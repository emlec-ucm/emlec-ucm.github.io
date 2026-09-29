#!/usr/bin/env python3
"""
tcg_mail.py – correos de The Computational Garage.

Un único script con tres subcomandos (sustituye a los antiguos
send_session_notification.py y send_notification_standalone.py):

  announce   Avisa de las sesiones NUEVAS en sesiones.org comparando con un
             commit anterior (--base SHA). Con --force anuncia la próxima
             sesión aunque no haya cambios.
  remind     Recordatorio. Con --if-tomorrow solo envía si hay sesión mañana
             (uso del cron); sin él, recuerda la próxima sesión programada.
  message    Mensaje libre: asunto + cuerpo (Markdown). El cuerpo puede venir
             de un fichero (--body-file), de una variable de entorno
             (--body-env) o de un issue de GitHub (--from-issue, que lee
             ISSUE_TITLE e ISSUE_BODY). Si el issue indica como tipo de
             mensaje "recordatorio" o "aviso de nueva sesión", se envía esa
             plantilla para la próxima sesión programada, con el texto del
             issue (si lo hay) como párrafo adicional.

Opciones comunes:
  --test      Envía SOLO a la cuenta del grupo (EMAIL_USER), para revisar.
  --dry-run   No envía nada; imprime el correo que se enviaría.

Variables de entorno (GitHub Secrets):
  EMAIL_USER         Dirección de Gmail del grupo
  EMAIL_PASSWORD     Contraseña de aplicación de Gmail (16 caracteres)
  GENTE_PASSPHRASE   Frase de paso del fichero cifrado con la lista de
                     participantes (RECIPIENTS_FILE, por defecto
                     content/TheComputationalGarage/gente)
  EMAIL_RECIPIENTS   Solo para pruebas en local sin el fichero cifrado:
                     destinatarios separados por comas (sin grupos). Se usa
                     únicamente si no hay GENTE_PASSPHRASE.

Opcionales:
  GH_TOKEN / GITHUB_TOKEN   Para convertir Markdown a HTML con la API de GitHub.

Lista de participantes: el fichero es un org con una entrada cifrada por
org-crypt (cifrado simétrico). Dentro del bloque cifrado, cada subencabezado
org es un grupo (Jefes, Senior, Junior...) y debajo van las direcciones, una
por línea (se ignoran comas, nombres y las líneas que empiezan por '#').
Destinatarios posibles (--to): todos, senior (= Senior + Jefes), jefes, junior.

Los destinatarios van siempre en copia oculta (Bcc): nadie ve la lista.
El script termina con código 1 si algo falla (secrets ausentes, error SMTP),
para que el run de GitHub Actions aparezca en rojo.
"""

import argparse
import html
import json
import os
import re
import smtplib
import subprocess
import sys
from datetime import date, datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from urllib import request
from zoneinfo import ZoneInfo

SESIONES_PATH = "content/TheComputationalGarage/sesiones.org"
DEFAULT_RECIPIENTS_FILE = "content/TheComputationalGarage/gente"
# Destinatario -> grupos del fichero que incluye (None = todos los grupos)
AUDIENCES = {
    "todos": None,
    "senior": ["jefes", "senior"],
    "jefes": ["jefes"],
    "junior": ["junior"],
}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
WEB_URL = "https://emlec-ucm.github.io/TheComputationalGarage/sesiones.html"
TZ = ZoneInfo("Europe/Madrid")
FROM_NAME = "The Computational Garage"
MAX_RCPT_PER_MESSAGE = 80  # Gmail admite 100 destinatarios por mensaje
NULL_SHA = "0" * 40

SIGNATURE_LINES = [
    "The Computational Garage",
    "Econometría, Machine Learning y Economía Computacional (EMLEC)",
    "Universidad Complutense de Madrid",
]

SPANISH_WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
SPANISH_MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# ---------------------------------------------------------------------------
# Logging (con anotaciones de GitHub Actions cuando procede)
# ---------------------------------------------------------------------------

def info(msg):
    print(f"[INFO] {msg}")


def warn(msg):
    print(f"::warning::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"[WARNING] {msg}")


def error(msg):
    print(f"::error::{msg}" if os.environ.get("GITHUB_ACTIONS") else f"[ERROR] {msg}")


# ---------------------------------------------------------------------------
# Parsing de sesiones.org
# ---------------------------------------------------------------------------

SESSION_HEADING_RE = re.compile(r"^\*{2}\s+(\d{4}-\d{2}-\d{2})\b")


def parse_sessions(org_text):
    """
    Devuelve la lista de todas las sesiones del fichero (cabeceras de nivel 2
    cuyo título empieza por YYYY-MM-DD), en el orden en que aparecen.

    Cada sesión es un dict con: date (str), date_obj (date), speakers,
    location, time (pueden faltar).
    """
    raw = []
    current = None
    for line in org_text.splitlines():
        m = SESSION_HEADING_RE.match(line)
        if m:
            current = {"date": m.group(1), "lines": []}
            raw.append(current)
            continue
        if re.match(r"^\*{1,2}\s", line):  # otra cabecera de nivel 1 o 2 cierra la sesión
            current = None
            continue
        if current is not None:
            current["lines"].append(line)

    sessions = []
    for item in raw:
        try:
            date_obj = datetime.strptime(item["date"], "%Y-%m-%d").date()
        except ValueError:
            warn(f"Fecha no válida en sesiones.org: {item['date']}")
            continue
        s = {"date": item["date"], "date_obj": date_obj}
        scheduled_time = None
        for line in item["lines"]:
            st = line.strip()
            m = re.match(r":SPEAKERS:\s+(.+)", st)
            if m:
                s["speakers"] = m.group(1).strip()
            m = re.match(r":LOCATION:\s+(.+)", st)
            if m:
                s["location"] = m.group(1).strip()
            m = re.match(r":SCHEDULED:\s+<[^>]*?(\d{1,2}:\d{2})", st)
            if m:
                scheduled_time = m.group(1)
            m = re.search(r"\*Hora:\*\s+(\d{1,2}:\d{2})", st)
            if m and "time" not in s:
                s["time"] = m.group(1)
        if "time" not in s and scheduled_time:
            s["time"] = scheduled_time
        sessions.append(s)
    return sessions


def read_sessions(path=SESIONES_PATH):
    try:
        with open(path, encoding="utf-8") as f:
            return parse_sessions(f.read())
    except FileNotFoundError:
        error(f"No existe el fichero {path}")
        return None


def git_show(ref, path=SESIONES_PATH):
    """Contenido de `path` en el commit `ref`, o None si no existe."""
    try:
        result = subprocess.run(["git", "show", f"{ref}:{path}"], capture_output=True, text=True)
    except OSError as exc:
        warn(f"No se pudo ejecutar git: {exc}")
        return None
    return result.stdout if result.returncode == 0 else None


def today_madrid():
    return datetime.now(TZ).date()


def next_session(sessions, today=None):
    """La sesión más próxima con fecha >= hoy, o None."""
    today = today or today_madrid()
    upcoming = [s for s in sessions if s["date_obj"] >= today]
    return min(upcoming, key=lambda s: s["date_obj"]) if upcoming else None


# ---------------------------------------------------------------------------
# Formato
# ---------------------------------------------------------------------------

def format_date_es(d):
    """date -> 'martes, 24 de marzo de 2026'."""
    return f"{SPANISH_WEEKDAYS[d.weekday()]}, {d.day} de {SPANISH_MONTHS[d.month - 1]} de {d.year}"


def format_date_short(d):
    return d.strftime("%d/%m/%Y")


def session_table_html(s):
    rows = [
        ("📅", "Fecha", format_date_es(s["date_obj"])),
        ("🕐", "Hora", s.get("time", "–")),
        ("👤", "Ponente(s)", s.get("speakers", "–")),
        ("📍", "Lugar", s.get("location", "–")),
    ]
    tr = "".join(
        f'<tr><td style="padding: 6px 12px;">{icon} <strong>{label}:</strong></td>'
        f'<td style="padding: 6px 12px;">{html.escape(value)}</td></tr>'
        for icon, label, value in rows
    )
    return f'<table style="border-collapse: collapse; margin: 16px 0;">{tr}</table>'


def session_table_text(s):
    return "\n".join([
        f"📅 Fecha: {format_date_es(s['date_obj'])}",
        f"🕐 Hora: {s.get('time', '–')}",
        f"👤 Ponente(s): {s.get('speakers', '–')}",
        f"📍 Lugar: {s.get('location', '–')}",
    ])


def wrap_html(inner_html):
    signature = "<br>".join(html.escape(line) for line in SIGNATURE_LINES)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #222; max-width: 600px; margin: 0 auto; padding: 20px;">
{inner_html}
  <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
  <p style="font-size: 0.9em; color: #555;">{signature}</p>
</body>
</html>"""


def wrap_text(inner_text):
    return inner_text.rstrip() + "\n\n--\n" + "\n".join(SIGNATURE_LINES) + "\n"


WEB_LINK_HTML = f'<p>Podéis consultar el histórico completo de sesiones en:<br><a href="{WEB_URL}">{WEB_URL}</a></p>'
WEB_LINK_TEXT = f"Podéis consultar el histórico completo de sesiones en:\n{WEB_URL}"


# ---------------------------------------------------------------------------
# Plantillas
# ---------------------------------------------------------------------------

def _note_parts(note):
    """Párrafo adicional opcional (Markdown) para anuncios y recordatorios."""
    if not note or not note.strip():
        return "", ""
    return markdown_to_html(note), note.strip() + "\n\n"


def build_announcement(s, note=None):
    note_html, note_text = _note_parts(note)
    subject = f"Nueva sesión de The Computational Garage - {format_date_short(s['date_obj'])}"
    html_body = wrap_html(
        "<p>Estimados/as compañeros/as,</p>"
        "<p>Os invitamos cordialmente a asistir a la próxima sesión de <strong>The Computational Garage</strong>:</p>"
        + session_table_html(s) + note_html + WEB_LINK_HTML + "<p>¡Os esperamos!</p>"
    )
    text_body = wrap_text(
        "Estimados/as compañeros/as,\n\n"
        "Os invitamos cordialmente a asistir a la próxima sesión de The Computational Garage:\n\n"
        + session_table_text(s) + "\n\n" + note_text + WEB_LINK_TEXT + "\n\n¡Os esperamos!"
    )
    return subject, html_body, text_body


def build_reminder(s, is_tomorrow, note=None):
    note_html, note_text = _note_parts(note)
    if is_tomorrow:
        subject = "Recordatorio - Sesión de The Computational Garage mañana"
        when_html = "<strong>MAÑANA</strong>"
        when_text = "MAÑANA"
    else:
        subject = f"Recordatorio - Próxima sesión de The Computational Garage ({format_date_short(s['date_obj'])})"
        when_html = f"el <strong>{format_date_es(s['date_obj'])}</strong>"
        when_text = f"el {format_date_es(s['date_obj'])}"
    html_body = wrap_html(
        "<p>Estimados/as compañeros/as,</p>"
        f"<p>Os recordamos que {when_html} tendremos sesión de <strong>The Computational Garage</strong>:</p>"
        + session_table_html(s) + note_html + "<p>¡No lo olvidéis!</p>" + WEB_LINK_HTML
    )
    text_body = wrap_text(
        "Estimados/as compañeros/as,\n\n"
        f"Os recordamos que {when_text} tendremos sesión de The Computational Garage:\n\n"
        + session_table_text(s) + "\n\n" + note_text + "¡No lo olvidéis!\n\n" + WEB_LINK_TEXT
    )
    return subject, html_body, text_body


def markdown_to_html(text):
    """Convierte Markdown a HTML con la API de GitHub; si falla, párrafos simples."""
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    payload = json.dumps({"text": text, "mode": "gfm"}).encode("utf-8")
    req = request.Request(
        "https://api.github.com/markdown",
        data=payload,
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "tcg-mail",
        },
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:  # noqa: BLE001
        warn(f"No se pudo convertir el Markdown con la API de GitHub ({exc}); se usa formato simple.")
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        return "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)


def build_message(subject, body_markdown, session=None):
    inner_html = markdown_to_html(body_markdown)
    inner_text = body_markdown.strip()
    if session:
        inner_html += "<p><strong>Próxima sesión programada:</strong></p>" + session_table_html(session) + WEB_LINK_HTML
        inner_text += "\n\nPróxima sesión programada:\n\n" + session_table_text(session) + "\n\n" + WEB_LINK_TEXT
    return subject, wrap_html(inner_html), wrap_text(inner_text)


# ---------------------------------------------------------------------------
# Issue de GitHub -> mensaje
# ---------------------------------------------------------------------------

ISSUE_TITLE_PREFIX_RE = re.compile(r"^\s*\[\s*mensaje\s*\]\s*:?\s*", re.IGNORECASE)


def parse_issue_sections(body):
    """Divide el cuerpo de un issue form en secciones por sus cabeceras '### '."""
    sections = {}
    current = None
    for line in (body or "").splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    out = {}
    for key, lines in sections.items():
        text = "\n".join(lines).strip()
        out[key] = "" if text == "_No response_" else text
    return out


def issue_kind(sections):
    """'general', 'reminder' o 'announcement' según el desplegable 'Tipo de mensaje'."""
    value = sections.get("tipo de mensaje", "").strip().lower()
    if value.startswith("recordatorio"):
        return "reminder"
    if value.startswith("aviso"):
        return "announcement"
    return "general"


def issue_audience(sections):
    """Clave de AUDIENCES según el desplegable 'Destinatarios' del issue."""
    value = sections.get("destinatarios", "").strip().lower()
    for key in ("senior", "jefes", "junior"):
        if value.startswith(key) or value.startswith("solo " + key):
            return key
    return "todos"


def message_from_issue():
    """
    Devuelve (kind, subject, text, include_session, audience) a partir de
    ISSUE_TITLE e ISSUE_BODY, o None si el issue no es válido.
    """
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")
    sections = parse_issue_sections(body)
    kind = issue_kind(sections)
    audience = issue_audience(sections)
    text = sections.get("mensaje")
    if text is None:
        text = body.strip()  # issue sin formulario: todo el cuerpo es el mensaje
    options = sections.get("opciones", "")
    include_session = bool(re.search(r"^\s*-\s*\[[xX]\]\s*Incluir", options, re.MULTILINE))

    subject = ISSUE_TITLE_PREFIX_RE.sub("", title).strip()
    if kind == "general":
        if not subject:
            error("El título del issue está vacío: escribe el asunto tras '[Mensaje]'.")
            return None
        if not text:
            error("El mensaje está vacío.")
            return None
    return kind, subject, text, include_session, audience


# ---------------------------------------------------------------------------
# Envío
# ---------------------------------------------------------------------------

def decrypt_pgp_block(path, passphrase):
    """Descifra el bloque PGP (org-crypt, simétrico) contenido en `path`."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        error(f"No existe el fichero de participantes {path}")
        return None
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "-----BEGIN PGP MESSAGE-----")
        end = next(i for i, l in enumerate(lines) if l.strip() == "-----END PGP MESSAGE-----")
    except StopIteration:
        error(f"{path} no contiene ningún bloque PGP cifrado.")
        return None
    block = "\n".join(lines[start:end + 1]) + "\n"

    import tempfile
    with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as pf:
        pf.write(passphrase)
        pass_path = pf.name
    try:
        os.chmod(pass_path, 0o600)
        result = subprocess.run(
            ["gpg", "--batch", "--quiet", "--yes", "--pinentry-mode", "loopback",
             "--passphrase-file", pass_path, "--decrypt"],
            input=block, capture_output=True, text=True,
        )
    finally:
        os.unlink(pass_path)
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "sin detalle"
        error(f"No se pudo descifrar la lista de participantes (¿frase de paso incorrecta?): {detail}")
        return None
    return result.stdout


def parse_groups(text):
    """
    Texto descifrado -> {grupo: [direcciones]}. Cada encabezado org abre un
    grupo (nombre en minúsculas, sin etiquetas). Las direcciones anteriores a
    cualquier encabezado van al grupo 'todos'. Se ignoran las líneas que
    empiezan por '#'.
    """
    groups = {}
    current = "todos"
    for line in text.splitlines():
        st = line.strip()
        if not st or st.startswith("#"):
            continue
        m = re.match(r"^\*+\s+(.*?)(?:\s+:[\w:@]+:)?\s*$", st)
        if m:
            current = m.group(1).strip().lower()
            groups.setdefault(current, [])
            continue
        for addr in EMAIL_RE.findall(st):
            groups.setdefault(current, [])
            if addr.lower() not in (a.lower() for a in groups[current]):
                groups[current].append(addr)
    return {g: addrs for g, addrs in groups.items() if addrs}


def load_credentials():
    user = os.environ.get("EMAIL_USER", "").strip()
    password = os.environ.get("EMAIL_PASSWORD", "")
    missing = [n for n, v in (("EMAIL_USER", user), ("EMAIL_PASSWORD", password)) if not v]
    if missing:
        error(f"Faltan variables de entorno: {', '.join(missing)}. Configura los GitHub Secrets.")
        return None

    passphrase = os.environ.get("GENTE_PASSPHRASE", "")
    if passphrase:
        path = os.environ.get("RECIPIENTS_FILE", DEFAULT_RECIPIENTS_FILE)
        text = decrypt_pgp_block(path, passphrase)
        if text is None:
            return None
        groups = parse_groups(text)
        source = path
    else:
        recipients_raw = os.environ.get("EMAIL_RECIPIENTS", "")
        if not recipients_raw:
            error("Faltan GENTE_PASSPHRASE (lista cifrada) o EMAIL_RECIPIENTS. Configura los GitHub Secrets.")
            return None
        groups = {"todos": [r for r in re.split(r"[,;\s]+", recipients_raw) if r.strip()]}
        source = "EMAIL_RECIPIENTS"
    if not groups:
        error(f"La lista de participantes ({source}) no contiene ninguna dirección.")
        return None
    info("Lista de participantes leída de " + source + ": "
         + ", ".join(f"{g} {len(a)}" for g, a in groups.items())
         + f" (total {sum(len(a) for a in groups.values())}).")
    return user, password, groups


def select_recipients(groups, audience):
    """Direcciones (sin duplicados) para un destinatario de AUDIENCES."""
    if audience not in AUDIENCES:
        error(f"Destinatario desconocido: {audience}. Opciones: {', '.join(AUDIENCES)}.")
        return None
    wanted = AUDIENCES[audience]
    if wanted is None:
        chosen = list(groups)
    else:
        chosen = [g for g in wanted if g in groups]
        missing = [g for g in wanted if g not in groups]
        if missing:
            warn(f"Grupos no encontrados en la lista: {', '.join(missing)}.")
    seen, recipients = set(), []
    for g in chosen:
        for addr in groups[g]:
            if addr.lower() not in seen:
                seen.add(addr.lower())
                recipients.append(addr)
    if not recipients:
        error(f"No hay ninguna dirección para el destinatario '{audience}'.")
        return None
    info(f"Destinatario '{audience}': grupos {', '.join(chosen) or '-'} ({len(recipients)} direcciones).")
    return recipients


def send_email(subject, html_body, text_body, creds, audience="todos", test=False, dry_run=False):
    user, password, groups = creds
    recipients = select_recipients(groups, audience)
    if recipients is None:
        return False
    envelope = [user] if test else recipients

    msg = MIMEMultipart("alternative")
    msg["From"] = formataddr((FROM_NAME, user))
    msg["To"] = formataddr((FROM_NAME, user))  # destinatarios reales en Bcc
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    info(f"Asunto: {subject}")
    info(f"Destinatarios (Bcc): {len(envelope)}" + (" [MODO PRUEBA: solo la cuenta del grupo]" if test else ""))
    if dry_run:
        info("Dry run: no se envía nada. Texto plano del correo:\n" + "-" * 60 + "\n" + text_body + "-" * 60)
        return True

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as server:
            server.login(user, password)
            for i in range(0, len(envelope), MAX_RCPT_PER_MESSAGE):
                chunk = envelope[i:i + MAX_RCPT_PER_MESSAGE]
                server.sendmail(user, chunk, msg.as_string())
        info(f"Correo enviado a {len(envelope)} destinatario(s).")
        return True
    except Exception as exc:  # noqa: BLE001
        error(f"Error SMTP al enviar '{subject}': {exc}")
        return False


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

def cmd_announce(args, creds):
    sessions = read_sessions()
    if sessions is None:
        return 1
    today = today_madrid()

    if args.force:
        s = next_session(sessions, today)
        if not s:
            warn("No hay ninguna sesión futura en sesiones.org; no se envía nada.")
            return 0
        targets = [s]
    else:
        base = args.base or "HEAD^"
        if base == NULL_SHA:
            info("Primer push de la rama: no hay commit anterior con el que comparar.")
            return 0
        prev_text = git_show(base)
        if prev_text is None:
            warn(f"No se pudo leer sesiones.org en {base}; no se envía nada.")
            return 0
        prev_dates = {s["date"] for s in parse_sessions(prev_text)}
        targets = sorted(
            (s for s in sessions if s["date"] not in prev_dates and s["date_obj"] >= today),
            key=lambda s: s["date_obj"],
        )
        if not targets:
            info("No hay sesiones nuevas con fecha futura. No se envía nada.")
            return 0

    ok = True
    for s in targets:
        info(f"Anunciando sesión del {s['date']}.")
        ok &= send_email(*build_announcement(s), creds, test=args.test, dry_run=args.dry_run)
    return 0 if ok else 1


def cmd_remind(args, creds):
    sessions = read_sessions()
    if sessions is None:
        return 1
    today = today_madrid()
    tomorrow = today + timedelta(days=1)

    if args.if_tomorrow:
        targets = [s for s in sessions if s["date_obj"] == tomorrow]
        if not targets:
            nxt = next_session(sessions, today)
            info("No hay sesión mañana. " + (f"Próxima sesión: {nxt['date']}." if nxt else "No hay sesiones futuras."))
            return 0
    else:
        s = next_session(sessions, today)
        if not s:
            warn("No hay ninguna sesión futura en sesiones.org; no se envía nada.")
            return 0
        targets = [s]

    ok = True
    for s in targets:
        ok &= send_email(*build_reminder(s, s["date_obj"] == tomorrow), creds, test=args.test, dry_run=args.dry_run)
    return 0 if ok else 1


def cmd_message(args, creds):
    include_session = args.include_session
    if args.from_issue:
        parsed = message_from_issue()
        if parsed is None:
            return 1
        kind, subject, body, include_session_issue, audience = parsed
        include_session = include_session or include_session_issue
        if kind != "general":
            s = next_session(read_sessions() or [])
            if not s:
                error("No hay ninguna sesión futura en sesiones.org: no se puede enviar un "
                      f"{'recordatorio' if kind == 'reminder' else 'aviso de nueva sesión'}.")
                return 1
            info(f"Tipo de mensaje: {kind}; próxima sesión: {s['date']}.")
            if kind == "reminder":
                mail = build_reminder(s, s["date_obj"] == today_madrid() + timedelta(days=1), note=body)
            else:
                mail = build_announcement(s, note=body)
            return 0 if send_email(*mail, creds, audience=audience, test=args.test, dry_run=args.dry_run) else 1
    else:
        audience = args.to
        subject = args.subject
        if args.body_file:
            with open(args.body_file, encoding="utf-8") as f:
                body = f.read()
        else:
            body = os.environ.get(args.body_env, "")
        if not subject or not body.strip():
            error("Hace falta un asunto (--subject) y un cuerpo no vacío.")
            return 1

    session = None
    if include_session:
        sessions = read_sessions() or []
        session = next_session(sessions)
        if not session:
            warn("Se pidió incluir la próxima sesión pero no hay ninguna programada.")

    ok = send_email(*build_message(subject, body, session), creds, audience=audience, test=args.test, dry_run=args.dry_run)
    return 0 if ok else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description="Correos de The Computational Garage")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--test", action="store_true", help="enviar solo a la cuenta del grupo (EMAIL_USER)")
    common.add_argument("--dry-run", action="store_true", help="no enviar; solo mostrar el correo")

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("announce", parents=[common], help="avisar de sesiones nuevas")
    p.add_argument("--base", help="commit con el que comparar sesiones.org (por defecto HEAD^)")
    p.add_argument("--force", action="store_true", help="anunciar la próxima sesión aunque no haya cambios")
    p.set_defaults(func=cmd_announce)

    p = sub.add_parser("remind", parents=[common], help="recordatorio de sesión")
    p.add_argument("--if-tomorrow", action="store_true", help="solo si hay sesión mañana (cron)")
    p.set_defaults(func=cmd_remind)

    p = sub.add_parser("message", parents=[common], help="mensaje libre a los participantes")
    p.add_argument("--subject", help="asunto del correo")
    src = p.add_mutually_exclusive_group()
    src.add_argument("--body-file", help="fichero con el cuerpo (Markdown)")
    src.add_argument("--body-env", default="MESSAGE_BODY", help="variable de entorno con el cuerpo (por defecto MESSAGE_BODY)")
    src.add_argument("--from-issue", action="store_true", help="leer asunto y cuerpo de ISSUE_TITLE / ISSUE_BODY")
    p.add_argument("--include-session", action="store_true", help="añadir los datos de la próxima sesión")
    p.add_argument("--to", default="todos", choices=list(AUDIENCES),
                   help="destinatarios (por defecto todos; con --from-issue se lee del issue)")
    p.set_defaults(func=cmd_message)

    args = parser.parse_args(argv)
    creds = load_credentials()
    if creds is None:
        return 1
    return args.func(args, creds)


if __name__ == "__main__":
    sys.exit(main())
