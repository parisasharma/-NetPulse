from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


class Device(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    ip_address = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    latency_threshold_ms = Column(Float, default=200.0)   # ms — above this = degraded
    created_at = Column(DateTime, default=datetime.utcnow)

    ping_results = relationship("PingResult", back_populates="device", cascade="all, delete")
    alerts = relationship("Alert", back_populates="device", cascade="all, delete")


class PingResult(Base):
    __tablename__ = "ping_results"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
    Integer,
    ForeignKey("devices.id"),
    nullable=False,
    index=True
)
    latency_ms = Column(Float, nullable=True)       # None means timed out
    packet_loss = Column(Float, default=0.0)        # 0.0 = no loss, 1.0 = 100% loss
    jitter_ms = Column(Float, nullable=True)        # variation in latency
    is_up = Column(Boolean, default=True)
    status = Column(String(20), default="up")       # "up", "degraded", "down"
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    device = relationship("Device", back_populates="ping_results")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(
    Integer,
    ForeignKey("devices.id"),
    nullable=False,
    index=True
)
    alert_type = Column(String(50), nullable=False)  # "down", "degraded", "recovered"
    message = Column(Text, nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    device = relationship("Device", back_populates="alerts")
