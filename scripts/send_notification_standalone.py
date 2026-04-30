#!/usr/bin/env python3
"""
send_notification_standalone.py

Standalone email notification script that does NOT require git history.
Supports manual (workflow_dispatch) and scheduled (cron) triggers.

Required environment variables (GitHub Secrets):
  EMAIL_USER         – Gmail address (thecomputationalgarage@gmail.com)
  EMAIL_PASSWORD     – Gmail app password (16 characters)
  EMAIL_RECIPIENTS   – Comma-separated list of recipient email addresses

Optional environment variables (set automatically by the workflow):
  TRIGGER_TYPE       – 'workflow_dispatch' or 'schedule'
  NOTIFICATION_TYPE  – 'announcement' or 'reminder' (only for workflow_dispatch)
"""

import os
import re
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SESIONES_PATH = "content/TheComputationalGarage/sesiones.org"
WEB_URL = "https://statespaceeconometrics-mlearning-rgroup.github.io/TheComputationalGarage/sesiones.html"

SPANISH_WEEKDAYS = {
    0: "lunes",
    1: "martes",
    2: "miércoles",
    3: "jueves",
    4: "viernes",
    5: "sábado",
    6: "domingo",
}

SPANISH_MONTHS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _get_first_subsection_lines(org_lines):
    """Return the lines that belong to the first level-2 heading (** ...)."""
    inside = False
    section_lines = []
    for line in org_lines:
        if re.match(r"^\*{2} ", line):
            if inside:
                break  # end of first subsection
            inside = True
            section_lines.append(line)
        elif inside:
            section_lines.append(line)
    return section_lines


def parse_first_session(org_text):
    """
    Parse the first subsection (level-2 heading) from org_text.

    Returns a dict with keys: date, speakers, time, location.
    Returns None if the subsection cannot be found.
    """
    lines = org_text.splitlines()
    section = _get_first_subsection_lines(lines)
    if not section:
        return None

    data = {}

    # Date from heading title: ** YYYY-MM-DD
    title_match = re.match(r"^\*{2}\s+(\d{4}-\d{2}-\d{2})", section[0])
    if not title_match:
        return None
    data["date"] = title_match.group(1)

    # Properties block
    in_props = False
    for line in section[1:]:
        stripped = line.strip()
        if stripped == ":PROPERTIES:":
            in_props = True
            continue
        if stripped == ":END:":
            in_props = False
            continue
        if in_props:
            m = re.match(r":SPEAKERS:\s+(.+)", stripped)
            if m:
                data["speakers"] = m.group(1).strip()
            m = re.match(r":LOCATION:\s+(.+)", stripped)
            if m:
                data["location"] = m.group(1).strip()

    # Time from content: *Hora:* HH:MM
    for line in section:
        m = re.search(r"\*Hora:\*\s+(\d{1,2}:\d{2})", line)
        if m:
            data["time"] = m.group(1)
            break

    return data if "date" in data else None


def parse_org_file(path):
    """Read and parse sesiones.org, returning the first session dict or None."""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[ERROR] File not found: {path}")
        return None
    return parse_first_session(content)


# ---------------------------------------------------------------------------
# Date/email helpers
# ---------------------------------------------------------------------------

def _format_date_spanish(date_str):
    """Convert 'YYYY-MM-DD' to 'lunes, 24 de marzo de 2026'."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = SPANISH_WEEKDAYS[dt.weekday()]
        month = SPANISH_MONTHS[dt.month]
        return f"{weekday}, {dt.day} de {month} de {dt.year}"
    except ValueError:
        return date_str


def _subject_date(date_str):
    """Convert 'YYYY-MM-DD' to 'DD/MM/YYYY' for use in email subject."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return date_str


# ---------------------------------------------------------------------------
# Email templates
# ---------------------------------------------------------------------------

def build_announcement_email(session):
    """Build announcement email (same style as send_session_notification.py)."""
    date_str = session.get("date", "")
    date_formatted = _format_date_spanish(date_str)
    time_str = session.get("time", "–")
    speakers = session.get("speakers", "–")
    location = session.get("location", "–")

    subject = f"Nueva sesión de The Computational Garage - {_subject_date(date_str)}"

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #222; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Estimados/as compañeros/as,</p>
  <p>Os invitamos cordialmente a asistir a la próxima sesión de <strong>The Computational Garage</strong>:</p>
  <table style="border-collapse: collapse; margin: 16px 0;">
    <tr><td style="padding: 6px 12px;">📅 <strong>Fecha:</strong></td><td style="padding: 6px 12px;">{date_formatted}</td></tr>
    <tr><td style="padding: 6px 12px;">🕐 <strong>Hora:</strong></td><td style="padding: 6px 12px;">{time_str}</td></tr>
    <tr><td style="padding: 6px 12px;">👤 <strong>Ponente(s):</strong></td><td style="padding: 6px 12px;">{speakers}</td></tr>
    <tr><td style="padding: 6px 12px;">📍 <strong>Lugar:</strong></td><td style="padding: 6px 12px;">{location}</td></tr>
  </table>
  <p>Podéis consultar el histórico completo de sesiones en:<br>
     <a href="{WEB_URL}">{WEB_URL}</a>
  </p>
  <p>¡Os esperamos!</p>
  <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
  <p style="font-size: 0.9em; color: #555;">
    The Computational Garage<br>
    State Space Econometrics &amp; Machine Learning Research Group<br>
    Universidad Complutense de Madrid
  </p>
</body>
</html>"""

    plain_text = f"""Estimados/as compañeros/as,

Os invitamos cordialmente a asistir a la próxima sesión de The Computational Garage:

📅 Fecha: {date_formatted}
🕐 Hora: {time_str}
👤 Ponente(s): {speakers}
📍 Lugar: {location}

Podéis consultar el histórico completo de sesiones en:
{WEB_URL}

¡Os esperamos!

--
The Computational Garage
State Space Econometrics & Machine Learning Research Group
Universidad Complutense de Madrid
"""

    return subject, html_body, plain_text


def build_reminder_email(session):
    """Build reminder email (for sessions happening tomorrow)."""
    date_str = session.get("date", "")
    date_formatted = _format_date_spanish(date_str)
    time_str = session.get("time", "–")
    speakers = session.get("speakers", "–")
    location = session.get("location", "–")

    subject = "Recordatorio - Sesión de The Computational Garage mañana"

    html_body = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="font-family: Arial, sans-serif; color: #222; max-width: 600px; margin: 0 auto; padding: 20px;">
  <p>Estimados/as compañeros/as,</p>
  <p>Os recordamos que <strong>MAÑANA</strong> tendremos sesión de <strong>The Computational Garage</strong>:</p>
  <table style="border-collapse: collapse; margin: 16px 0;">
    <tr><td style="padding: 6px 12px;">📅 <strong>Fecha:</strong></td><td style="padding: 6px 12px;">{date_formatted}</td></tr>
    <tr><td style="padding: 6px 12px;">🕐 <strong>Hora:</strong></td><td style="padding: 6px 12px;">{time_str}</td></tr>
    <tr><td style="padding: 6px 12px;">👤 <strong>Ponente(s):</strong></td><td style="padding: 6px 12px;">{speakers}</td></tr>
    <tr><td style="padding: 6px 12px;">📍 <strong>Lugar:</strong></td><td style="padding: 6px 12px;">{location}</td></tr>
  </table>
  <p>¡No lo olvidéis!</p>
  <p>Podéis consultar el histórico completo de sesiones en:<br>
     <a href="{WEB_URL}">{WEB_URL}</a>
  </p>
  <hr style="border: none; border-top: 1px solid #ccc; margin: 24px 0;">
  <p style="font-size: 0.9em; color: #555;">
    The Computational Garage<br>
    State Space Econometrics &amp; Machine Learning Research Group<br>
    Universidad Complutense de Madrid
  </p>
</body>
</html>"""

    plain_text = f"""Estimados/as compañeros/as,

Os recordamos que MAÑANA tendremos sesión de The Computational Garage:

📅 Fecha: {date_formatted}
🕐 Hora: {time_str}
👤 Ponente(s): {speakers}
📍 Lugar: {location}

¡No lo olvidéis!

Podéis consultar el histórico completo de sesiones en:
{WEB_URL}

--
The Computational Garage
State Space Econometrics & Machine Learning Research Group
Universidad Complutense de Madrid
"""

    return subject, html_body, plain_text


# ---------------------------------------------------------------------------
# Gmail SMTP sending
# ---------------------------------------------------------------------------

def send_email(subject, html_body, plain_text, recipients, from_email, password):
    """Send the notification email via Gmail SMTP."""
    to_list = [addr.strip() for addr in recipients if addr.strip()]
    if not to_list:
        print("[ERROR] No valid recipient addresses found.")
        return False

    message = MIMEMultipart("alternative")
    message["From"] = from_email
    message["To"] = ", ".join(to_list)
    message["Subject"] = subject

    part1 = MIMEText(plain_text, "plain", "utf-8")
    part2 = MIMEText(html_body, "html", "utf-8")
    message.attach(part1)
    message.attach(part2)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_list, message.as_string())
        print(f"[INFO] Email sent successfully to {len(to_list)} recipient(s).")
        return True
    except Exception as exc:
        print(f"[ERROR] SMTP error: {exc}")
        return False


# ---------------------------------------------------------------------------
# Notification dispatch
# ---------------------------------------------------------------------------

def send_reminder_if_tomorrow(session_data, email_user, email_password, recipients):
    """Send reminder only if the first session is tomorrow (for cron trigger)."""
    session_date_str = session_data.get("date")
    if not session_date_str:
        print("[INFO] No date found for session.")
        return

    try:
        session_date = datetime.strptime(session_date_str, "%Y-%m-%d").date()
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()

        if session_date == tomorrow:
            print(f"[INFO] Session tomorrow ({session_date}). Sending reminder.")
            subject, html_body, plain_text = build_reminder_email(session_data)
            print(f"[INFO] Subject: {subject}")
            print(f"[INFO] Sending to {len(recipients)} recipient(s)...")
            success = send_email(subject, html_body, plain_text, recipients, email_user, email_password)
            if not success:
                print("[WARNING] Email could not be sent. Continuing without failing.")
            else:
                print("[INFO] Reminder sent successfully.")
        else:
            print(f"[INFO] No session tomorrow. Next session: {session_date}. No email sent.")
    except ValueError as e:
        print(f"[ERROR] Invalid date format: {e}")


def send_reminder_for_upcoming(session_data, email_user, email_password, recipients):
    """Send reminder for the next upcoming session (manual trigger)."""
    print("[INFO] Sending reminder for upcoming session.")
    subject, html_body, plain_text = build_reminder_email(session_data)
    print(f"[INFO] Subject: {subject}")
    print(f"[INFO] Sending to {len(recipients)} recipient(s)...")
    success = send_email(subject, html_body, plain_text, recipients, email_user, email_password)
    if not success:
        print("[WARNING] Email could not be sent. Continuing without failing.")
    else:
        print("[INFO] Reminder sent successfully.")


def send_announcement(session_data, email_user, email_password, recipients):
    """Send announcement for the first session (manual trigger)."""
    print("[INFO] Sending announcement for current session.")
    subject, html_body, plain_text = build_announcement_email(session_data)
    print(f"[INFO] Subject: {subject}")
    print(f"[INFO] Sending to {len(recipients)} recipient(s)...")
    success = send_email(subject, html_body, plain_text, recipients, email_user, email_password)
    if not success:
        print("[WARNING] Email could not be sent. Continuing without failing.")
    else:
        print("[INFO] Announcement sent successfully.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Get environment variables
    email_user = os.environ.get("EMAIL_USER")
    email_password = os.environ.get("EMAIL_PASSWORD")
    recipients_raw = os.environ.get("EMAIL_RECIPIENTS")
    trigger_type = os.environ.get("TRIGGER_TYPE", "workflow_dispatch")
    notification_type = os.environ.get("NOTIFICATION_TYPE", "announcement")

    # Validate required variables
    missing = [name for name, val in [
        ("EMAIL_USER", email_user),
        ("EMAIL_PASSWORD", email_password),
        ("EMAIL_RECIPIENTS", recipients_raw),
    ] if not val]

    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}")
        print("[INFO] Skipping notification. Please configure the GitHub Secrets.")
        sys.exit(0)

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    # Parse sesiones.org
    print(f"[INFO] Trigger type: {trigger_type}, Notification type: {notification_type}")
    session_data = parse_org_file(SESIONES_PATH)

    if not session_data:
        print("[INFO] No session data found in sesiones.org.")
        sys.exit(0)

    print(f"[INFO] First session date: {session_data.get('date')}")

    # Determine what to do based on trigger
    if trigger_type == "schedule":
        # Cron trigger: send reminder only if session is tomorrow
        send_reminder_if_tomorrow(session_data, email_user, email_password, recipients)
    elif trigger_type == "workflow_dispatch":
        if notification_type == "reminder":
            # Manual reminder for next upcoming session
            send_reminder_for_upcoming(session_data, email_user, email_password, recipients)
        else:
            # Manual announcement for first session (default)
            send_announcement(session_data, email_user, email_password, recipients)
    else:
        print(f"[WARNING] Unknown trigger type '{trigger_type}'. Defaulting to announcement.")
        send_announcement(session_data, email_user, email_password, recipients)


if __name__ == "__main__":
    main()
