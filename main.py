"""
main.py
───────
NetPulse — Real-Time Network Health Monitor
FastAPI entry point.

Run locally:
    uvicorn app.main:app --reload

API docs auto-generated at:
    http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, SessionLocal
import models
import devices
import alerts
from scheduler import start_scheduler, shutdown_scheduler

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("netpulse")


# ── DB init + scheduler startup ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables
    models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready.")

    # Load active devices and start pinging
    db = SessionLocal()
    try:
        active_devices = db.query(models.Device).filter(models.Device.is_active == True).all()
        start_scheduler(active_devices)
        logger.info(f"NetPulse started. Monitoring {len(active_devices)} device(s).")
    finally:
        db.close()

    yield  # App runs here

    # Cleanup on shutdown
    shutdown_scheduler()
    logger.info("NetPulse shut down cleanly.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="NetPulse",
    description=(
        "Real-time network health monitoring system. "
        "Monitors device latency and packet loss via ICMP, "
        "detects anomalies, and sends email alerts on status changes."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow Streamlit dashboard to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(devices.router)
app.include_router(alerts.router)


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "app": "NetPulse",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}
