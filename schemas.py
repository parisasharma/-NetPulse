from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
import ipaddress


# ── Device schemas ────────────────────────────────────────────────────────────

class DeviceCreate(BaseModel):
    name: str
    ip_address: str
    description: Optional[str] = None
    latency_threshold_ms: Optional[float] = 200.0

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v):
        try:
            ipaddress.ip_address(v)
        except ValueError:
            raise ValueError(f"'{v}' is not a valid IP address")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Device name cannot be empty")
        return v.strip()


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    latency_threshold_ms: Optional[float] = None


class DeviceResponse(BaseModel):
    id: int
    name: str
    ip_address: str
    description: Optional[str]
    is_active: bool
    latency_threshold_ms: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── PingResult schemas ────────────────────────────────────────────────────────

class PingResultResponse(BaseModel):
    id: int
    device_id: int
    latency_ms: Optional[float]
    packet_loss: float
    jitter_ms: Optional[float]
    is_up: bool
    status: str
    timestamp: datetime

    model_config = {"from_attributes": True}


# ── Alert schemas ─────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id: int
    device_id: int
    alert_type: str
    message: str
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


# ── Summary schemas ───────────────────────────────────────────────────────────

class DeviceStatusSummary(BaseModel):
    device_id: int
    device_name: str
    ip_address: str
    status: str                        # "up", "degraded", "down", "unknown"
    last_latency_ms: Optional[float]
    uptime_percent: float              # last 100 pings
    last_seen: Optional[datetime]


class OverallSummary(BaseModel):
    total_devices: int
    devices_up: int
    devices_degraded: int
    devices_down: int
    average_latency_ms: Optional[float]
    active_alerts: int
