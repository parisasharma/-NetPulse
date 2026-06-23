"""
alerts.py
─────────
Email alert system using Gmail SMTP.
Set ALERT_EMAIL_FROM, ALERT_EMAIL_PASSWORD, ALERT_EMAIL_TO in .env
"""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime 
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(tags=["Alerts"])

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("ALERT_EMAIL_PASSWORD", "")
EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")

# Emoji + colour map per alert type
ALERT_META = {
    "down":      {"emoji": "🔴", "colour": "#E24B4A", "label": "DEVICE DOWN"},
    "degraded":  {"emoji": "🟡", "colour": "#BA7517", "label": "DEVICE DEGRADED"},
    "recovered": {"emoji": "🟢", "colour": "#1D9E75", "label": "DEVICE RECOVERED"},
}


def _build_html(alert_type: str, ip: str, message: str) -> str:
    meta = ALERT_META.get(alert_type, {"emoji": "⚪", "colour": "#666", "label": alert_type.upper()})
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px">
    <div style="max-width:500px;margin:auto;background:white;border-radius:8px;overflow:hidden;
                box-shadow:0 2px 8px rgba(0,0,0,0.1)">
        <div style="background:{meta['colour']};padding:20px;color:white">
            <h2 style="margin:0">{meta['emoji']} NetPulse Alert — {meta['label']}</h2>
        </div>
        <div style="padding:24px">
            <p style="font-size:16px;color:#333"><strong>Device:</strong> {ip}</p>
            <p style="font-size:14px;color:#555">{message}</p>
            <p style="font-size:12px;color:#999;margin-top:20px">
                Triggered at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </div>
        <div style="background:#f9f9f9;padding:12px 24px;font-size:11px;color:#aaa">
            NetPulse Network Monitor · Built by Parisa Sharma
        </div>
    </div>
    </body></html>
    """


def send_email_alert(alert_type: str, ip: str, message: str):
    """Send an HTML email alert. Silently skips if credentials not configured."""
    if not all([EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO]):
        logger.info("Email credentials not configured — skipping email alert.")
        return

    meta = ALERT_META.get(alert_type, {"emoji": "⚪", "label": alert_type.upper()})
    subject = f"{meta['emoji']} NetPulse: {meta['label']} — {ip}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(_build_html(alert_type, ip, message), "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        logger.info(f"Email alert sent for {ip} ({alert_type})")
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
@router.get("/alerts")
def get_alerts(db: Session = Depends(get_db)):
    alerts = (
        db.query(models.Alert)
        .order_by(models.Alert.created_at.desc())
        .limit(50)
        .all()
    )

    return [
        {
            "id": alert.id,
            "device_id": alert.device_id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "created_at": alert.created_at,
           "is_resolved": alert.is_resolved
        }
        for alert in alerts
    ]