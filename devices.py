"""
routers/devices.py
──────────────────
All /devices endpoints.

GET    /devices                     → list all devices
POST   /devices                     → add a new device
GET    /devices/{id}                → get one device
PUT    /devices/{id}                → update device
DELETE /devices/{id}                → delete device
GET    /devices/{id}/status         → latest ping result
GET    /devices/{id}/history        → last N ping results
GET    /devices/{id}/stats          → uptime %, avg latency, etc.
GET    /summary                     → overview of all devices
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db
import models
import schemas
from scheduler import add_device_job, remove_device_job

router = APIRouter(tags=["Devices"])


# ── List all devices ──────────────────────────────────────────────────────────

@router.get("/devices", response_model=List[schemas.DeviceResponse])
def list_devices(
    active_only: bool = Query(False, description="Return only active devices"),
    db: Session = Depends(get_db)
):
    query = db.query(models.Device)
    if active_only:
        query = query.filter(models.Device.is_active == True)
    return query.order_by(models.Device.created_at.desc()).all()


# ── Add a device ──────────────────────────────────────────────────────────────

@router.post("/devices", response_model=schemas.DeviceResponse, status_code=201)
def add_device(device: schemas.DeviceCreate, db: Session = Depends(get_db)):
    # Check for duplicate IP
    existing = db.query(models.Device).filter(
        models.Device.ip_address == device.ip_address
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Device with IP {device.ip_address} already exists.")

    db_device = models.Device(**device.model_dump())
    db.add(db_device)
    db.commit()
    db.refresh(db_device)

    # Schedule ping job immediately
    add_device_job(db_device.id, db_device.ip_address, db_device.latency_threshold_ms)
    return db_device


# ── Get one device ────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}", response_model=schemas.DeviceResponse)
def get_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")
    return device


# ── Update a device ───────────────────────────────────────────────────────────

@router.put("/devices/{device_id}", response_model=schemas.DeviceResponse)
def update_device(device_id: int, update: schemas.DeviceUpdate, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    for field, value in update.model_dump(exclude_none=True).items():
        setattr(device, field, value)

    db.commit()
    db.refresh(device)

    # Reschedule if threshold changed
    if update.latency_threshold_ms is not None:
        add_device_job(device.id, device.ip_address, device.latency_threshold_ms)

    return device


# ── Delete a device ───────────────────────────────────────────────────────────

@router.delete("/devices/{device_id}", status_code=204)
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")

    remove_device_job(device_id)
    db.delete(device)
    db.commit()


# ── Latest status ─────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}/status", response_model=Optional[schemas.PingResultResponse])
def get_device_status(device_id: int, db: Session = Depends(get_db)):
    _require_device(device_id, db)
    result = (
        db.query(models.PingResult)
        .filter(models.PingResult.device_id == device_id)
        .order_by(desc(models.PingResult.timestamp))
        .first()
    )
    return result


# ── Ping history ──────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}/history", response_model=List[schemas.PingResultResponse])
def get_device_history(
    device_id: int,
    limit: int = Query(100, ge=1, le=1000),
    hours: int = Query(1, ge=1, le=168, description="Look-back window in hours"),
    db: Session = Depends(get_db),
):
    _require_device(device_id, db)
    since = datetime.utcnow() - timedelta(hours=hours)
    results = (
        db.query(models.PingResult)
        .filter(
            models.PingResult.device_id == device_id,
            models.PingResult.timestamp >= since,
        )
        .order_by(desc(models.PingResult.timestamp))
        .limit(limit)
        .all()
    )
    return results


# ── Device stats ──────────────────────────────────────────────────────────────

@router.get("/devices/{device_id}/stats")
def get_device_stats(
    device_id: int,
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db),
):
    _require_device(device_id, db)
    since = datetime.utcnow() - timedelta(hours=hours)
    results = (
        db.query(models.PingResult)
        .filter(
            models.PingResult.device_id == device_id,
            models.PingResult.timestamp >= since,
        )
        .all()
    )

    if not results:
        return {"device_id": device_id, "message": "No data yet — pings run every 30 seconds."}

    total = len(results)
    up_count = sum(1 for r in results if r.status == "up")
    degraded_count = sum(1 for r in results if r.status == "degraded")
    down_count = sum(1 for r in results if r.status == "down")
    latencies = [r.latency_ms for r in results if r.latency_ms is not None]

    return {
        "device_id": device_id,
        "period_hours": hours,
        "total_pings": total,
        "uptime_percent": round((up_count / total) * 100, 2),
        "degraded_percent": round((degraded_count / total) * 100, 2),
        "down_percent": round((down_count / total) * 100, 2),
        "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "min_latency_ms": round(min(latencies), 2) if latencies else None,
        "max_latency_ms": round(max(latencies), 2) if latencies else None,
    }


# ── Overall summary ───────────────────────────────────────────────────────────

@router.get("/summary", response_model=schemas.OverallSummary)
def get_summary(db: Session = Depends(get_db)):
    devices = db.query(models.Device).filter(models.Device.is_active == True).all()
    statuses = {"up": 0, "degraded": 0, "down": 0}
    latencies = []

    for device in devices:
        latest = (
            db.query(models.PingResult)
            .filter(models.PingResult.device_id == device.id)
            .order_by(desc(models.PingResult.timestamp))
            .first()
        )
        if latest:
            statuses[latest.status] = statuses.get(latest.status, 0) + 1
            if latest.latency_ms:
                latencies.append(latest.latency_ms)
        else:
            statuses["down"] += 1  # no data yet = treat as unknown/down

    active_alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).count()

    return schemas.OverallSummary(
        total_devices=len(devices),
        devices_up=statuses["up"],
        devices_degraded=statuses["degraded"],
        devices_down=statuses["down"],
        average_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else None,
        active_alerts=active_alerts,
    )


# ── Helper ────────────────────────────────────────────────────────────────────

def _require_device(device_id: int, db: Session):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found.")
    return device
