"""
scheduler.py
────────────
APScheduler background job manager.
Adds a ping job per active device on startup.
Exposes add_device_job / remove_device_job for dynamic updates.
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger(__name__)

PING_INTERVAL_SECONDS = 30

scheduler = BackgroundScheduler(
    jobstores={"default": MemoryJobStore()},
    job_defaults={"coalesce": True, "max_instances": 1},
)


def start_scheduler(devices: list):
    """Called at FastAPI startup. Loads all active devices."""
    for device in devices:
        add_device_job(device.id, device.ip_address, device.latency_threshold_ms)
    scheduler.start()
    logger.info(f"Scheduler started with {len(devices)} device(s).")


def add_device_job(device_id: int, ip: str, threshold_ms: float = 200.0):
    """Add a ping job for a newly registered device."""
    from ping_worker import ping_device
    job_id = f"ping_{device_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(
        ping_device,
        trigger="interval",
        seconds=PING_INTERVAL_SECONDS,
        args=[device_id, ip, threshold_ms],
        id=job_id,
        replace_existing=True,
    )
    logger.info(f"Scheduled ping job for device {device_id} ({ip}) every {PING_INTERVAL_SECONDS}s")


def remove_device_job(device_id: int):
    """Remove ping job when a device is deleted."""
    job_id = f"ping_{device_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        logger.info(f"Removed ping job for device {device_id}")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
def shutdown_scheduler():
    """Shutdown APScheduler cleanly."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")