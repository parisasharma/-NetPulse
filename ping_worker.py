"""
ping_worker.py
──────────────
Handles ICMP pinging of devices and stores results in the database.
Falls back to subprocess ping if icmplib needs root privileges.
"""

import subprocess
import platform
import re
import logging
from datetime import datetime
from database import SessionLocal
import models

logger = logging.getLogger(__name__)

# Track consecutive failures per device {device_id: count}
_consecutive_failures: dict[int, int] = {}
# Track previous status per device to detect recovery
_previous_status: dict[int, str] = {}

DOWN_THRESHOLD = 3   # consecutive failures before flagging "down"


# ─── Ping logic ───────────────────────────────────────────────────────────────

def _ping_subprocess(ip: str, count: int = 4) -> dict:
    """
    Cross-platform ICMP ping using subprocess.
    Returns dict with: is_up, latency_ms, packet_loss, jitter_ms
    """
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", str(count), ip]
    else:
        cmd = ["ping", "-c", str(count), "-W", "2", ip]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = result.stdout

        if system == "windows":
            # Parse Windows ping output
            times = re.findall(r"time[=<](\d+)ms", output)
            loss_match = re.search(r"(\d+)% loss", output)
        else:
            # Parse Linux/Mac ping output
            times = re.findall(r"time=([\d.]+)", output)
            loss_match = re.search(r"(\d+)% packet loss", output)

        packet_loss = float(loss_match.group(1)) / 100 if loss_match else 1.0
        is_up = len(times) > 0

        if is_up:
            latencies = [float(t) for t in times]
            latency_ms = sum(latencies) / len(latencies)
            jitter_ms = max(latencies) - min(latencies) if len(latencies) > 1 else 0.0
        else:
            latency_ms = None
            jitter_ms = None

        return {
            "is_up": is_up,
            "latency_ms": latency_ms,
            "packet_loss": packet_loss,
            "jitter_ms": jitter_ms,
        }

    except subprocess.TimeoutExpired:
        logger.warning(f"Ping timeout for {ip}")
        return {"is_up": False, "latency_ms": None, "packet_loss": 1.0, "jitter_ms": None}
    except Exception as e:
        logger.error(f"Ping error for {ip}: {e}")
        return {"is_up": False, "latency_ms": None, "packet_loss": 1.0, "jitter_ms": None}


def _determine_status(is_up: bool, latency_ms: float | None, threshold: float) -> str:
    """Determine device status based on ping result."""
    if not is_up:
        return "down"
    if latency_ms and latency_ms > threshold:
        return "degraded"
    return "up"


# ─── Main ping job ────────────────────────────────────────────────────────────

def ping_device(device_id: int, ip: str, threshold_ms: float = 200.0):
    """
    Main ping job called by APScheduler every 30 seconds.
    1. Pings the device
    2. Determines status
    3. Saves result to DB
    4. Handles consecutive failure tracking
    5. Creates alerts on status change
    """
    logger.info(f"Pinging device {device_id} ({ip})")

    ping_data = _ping_subprocess(ip)
    status = _determine_status(ping_data["is_up"], ping_data["latency_ms"], threshold_ms)
    print(
    f"DEBUG -> latency={ping_data['latency_ms']}, "
    f"threshold={threshold_ms}, "
    f"status={status}"
)

    # Update consecutive failure tracker
    if not ping_data["is_up"]:
        _consecutive_failures[device_id] = _consecutive_failures.get(device_id, 0) + 1
    else:
        _consecutive_failures[device_id] = 0

    # Only mark "down" after DOWN_THRESHOLD consecutive failures
    if status == "down" and _consecutive_failures.get(device_id, 0) < DOWN_THRESHOLD:
        status = "degraded"

    db = SessionLocal()
    try:
        # Save ping result
        result = models.PingResult(
            device_id=device_id,
            latency_ms=ping_data["latency_ms"],
            packet_loss=ping_data["packet_loss"],
            jitter_ms=ping_data["jitter_ms"],
            is_up=ping_data["is_up"],
            status=status,
            timestamp=datetime.utcnow(),
        )
        db.add(result)

        # Handle alerts on status change
        prev_status = _previous_status.get(device_id, "unknown")

        if status == "down" and prev_status != "down":
            _create_alert(db, device_id, ip, "down",
                          f"Device {ip} is DOWN — {DOWN_THRESHOLD} consecutive ping failures.")

        elif status == "degraded" and prev_status != "degraded":
            _create_alert(db, device_id, ip, "degraded",
                          f"Device {ip} is DEGRADED — latency {ping_data['latency_ms']:.1f}ms exceeds {threshold_ms}ms threshold.")

        elif status == "up" and prev_status in ("down", "degraded"):
            _create_alert(db, device_id, ip, "recovered",
                          f"Device {ip} has RECOVERED — latency {ping_data['latency_ms']:.1f}ms, packet loss {ping_data['packet_loss']*100:.0f}%.")
            _resolve_alerts(db, device_id)

        _previous_status[device_id] = status
        db.commit()

    except Exception as e:
        logger.error(f"DB error saving ping result for device {device_id}: {e}")
        db.rollback()
    finally:
        db.close()


def _create_alert(db, device_id: int, ip: str, alert_type: str, message: str):
    alert = models.Alert(
        device_id=device_id,
        alert_type=alert_type,
        message=message,
        is_resolved=False,
        created_at=datetime.utcnow(),
    )
    db.add(alert)
    logger.warning(f"ALERT [{alert_type.upper()}]: {message}")

    # Send email alert in background (non-blocking)
    try:
        from alerts import send_email_alert
        send_email_alert(alert_type, ip, message)
    except Exception as e:
        logger.error(f"Email alert failed: {e}")


def _resolve_alerts(db, device_id: int):
    """Mark all open alerts for this device as resolved."""
    open_alerts = db.query(models.Alert).filter(
        models.Alert.device_id == device_id,
        models.Alert.is_resolved == False
    ).all()
    for alert in open_alerts:
        alert.is_resolved = True
        alert.resolved_at = datetime.utcnow()
