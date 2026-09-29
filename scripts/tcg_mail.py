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
  EMAIL_RECIPIENTS   Destinatarios separados por comas

Opcionales:
  GH_TOKEN / GITHUB_TOKEN   Para convertir Markdown a HTML con la API de GitHub.

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


def message_from_issue():
    """
    Devuelve (kind, subject, text, include_session) a partir de ISSUE_TITLE e
    ISSUE_BODY, o None si el issue no es válido.
    """
    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")
    sections = parse_issue_sections(body)
    kind = issue_kind(sections)
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
    return kind, subject, text, include_session


# ---------------------------------------------------------------------------
# Envío
# ---------------------------------------------------------------------------

def load_credentials():
    user = os.environ.get("EMAIL_USER", "").strip()
    password = os.environ.get("EMAIL_PASSWORD", "")
    recipients_raw = os.environ.get("EMAIL_RECIPIENTS", "")
    missing = [n for n, v in (("EMAIL_USER", user), ("EMAIL_PASSWORD", password), ("EMAIL_RECIPIENTS", recipients_raw)) if not v]
    if missing:
        error(f"Faltan variables de entorno: {', '.join(missing)}. Configura los GitHub Secrets.")
        return None
    recipients = [r.strip() for r in re.split(r"[,;\s]+", recipients_raw) if r.strip()]
    if not recipients:
        error("EMAIL_RECIPIENTS no contiene ninguna dirección.")
        return None
    return user, password, recipients


def send_email(subject, html_body, text_body, creds, test=False, dry_run=False):
    user, password, recipients = creds
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
        kind, subject, body, include_session_issue = parsed
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
            return 0 if send_email(*mail, creds, test=args.test, dry_run=args.dry_run) else 1
    else:
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

    ok = send_email(*build_message(subject, body, session), creds, test=args.test, dry_run=args.dry_run)
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
    p.set_defaults(func=cmd_message)

    args = parser.parse_args(argv)
    creds = load_credentials()
    if creds is None:
        return 1
    return args.func(args, creds)


if __name__ == "__main__":
    sys.exit(main())
