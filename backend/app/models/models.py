from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, JSON, ForeignKey, Time, Date, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.database.database import Base

class Store(Base):
    __tablename__ = "stores"
    store_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    timezone = Column(String, nullable=False)

class Zone(Base):
    __tablename__ = "zones"
    zone_id = Column(String, primary_key=True, index=True)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False)
    zone_name = Column(String, nullable=False)
    zone_type = Column(String, nullable=False)
    is_billing_zone = Column(Boolean, default=False)
    polygon_coords = Column(JSON)

class Event(Base):
    __tablename__ = "events"
    event_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    camera_id = Column(String, nullable=False)
    visitor_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    zone_id = Column(String, ForeignKey("zones.zone_id"), nullable=True)
    dwell_ms = Column(Integer, default=0)
    is_staff = Column(Boolean, default=False)
    confidence = Column(Float, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_events_store_time", "store_id", "timestamp"),
        Index("ix_events_store_type_time", "store_id", "event_type", "timestamp"),
    )

class VisitorSession(Base):
    __tablename__ = "visitor_sessions"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False, index=True)
    visitor_id = Column(String, nullable=False, index=True)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    current_state = Column(String, nullable=False) # CREATED, ENTERED, ZONE_VISIT, BILLING_QUEUE, PURCHASED, EXITED
    converted = Column(Boolean, default=False)
    total_dwell_ms = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_sessions_store_state_entry", "store_id", "current_state", "entry_time"),
    )

class Transaction(Base):
    __tablename__ = "transactions"
    invoice_number = Column(String, primary_key=True, index=True)
    order_id = Column(String, nullable=False)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False)
    order_date = Column(Date, nullable=False)
    order_time = Column(Time, nullable=False)
    gmv = Column(Float, nullable=False)
    nmv = Column(Float, nullable=False)
    correlated_session_id = Column(UUID(as_uuid=True), ForeignKey("visitor_sessions.session_id"), nullable=True, index=True)

    __table_args__ = (
        Index("ix_transactions_store_time", "store_id", "order_time"),
    )

class MetricsSnapshot(Base):
    __tablename__ = "metrics_snapshots"
    snapshot_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False)
    snapshot_time = Column(DateTime(timezone=True), nullable=False, index=True)
    unique_visitors = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    avg_dwell_ms = Column(Float, default=0.0)
    queue_depth = Column(Float, default=0.0)
    abandonment_rate = Column(Float, default=0.0)

class Anomaly(Base):
    __tablename__ = "anomalies"
    anomaly_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id = Column(String, ForeignKey("stores.store_id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False) # INFO, WARN, CRITICAL
    description = Column(String, nullable=False)
    suggested_action = Column(String, nullable=False)
    triggered_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

    __table_args__ = (
        Index("ix_anomalies_store_resolved_time", "store_id", "resolved", "triggered_at"),
    )
