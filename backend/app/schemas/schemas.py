from pydantic import BaseModel, Field, UUID4, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any

class EventMetadata(BaseModel):
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: Optional[int] = None
    # Flexible field to capture any other schema additions gracefully
    extra: Dict[str, Any] = Field(default_factory=dict)

class EventIngest(BaseModel):
    event_id: UUID4
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: datetime
    zone_id: Optional[str] = None
    dwell_ms: int = Field(default=0, ge=0)
    is_staff: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Optional[EventMetadata] = None

class EventBatchIngest(BaseModel):
    events: List[EventIngest] = Field(max_length=500)

class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    errors: List[str]

class MetricsResponse(BaseModel):
    store_id: str
    date: str
    unique_visitors: int
    conversion_rate: float
    avg_dwell_by_zone: Dict[str, float]
    avg_dwell_ms: float = 0.0          # Overall average dwell ms across all sessions
    queue_depth: float
    abandonment_rate: float
    computed_at: str

class FunnelStage(BaseModel):
    stage: str
    count: int
    drop_off_percentage: float         # Renamed from drop_off_pct to match frontend

class HeatmapZone(BaseModel):
    zone_id: str
    zone_name: str
    avg_dwell_ms: float
    normalized_score: float # 0 to 100
    data_confidence: float # percentage

class HeatmapResponse(BaseModel):
    store_id: str
    zones: List[HeatmapZone]
    data_confidence: str

class AnomalyResponseItem(BaseModel):
    type: str
    severity: str
    description: str
    suggested_action: str
    triggered_at: datetime

class AnomaliesResponse(BaseModel):
    store_id: str
    anomalies: List[AnomalyResponseItem]

class HealthResponse(BaseModel):
    status: str
    database: str
    stores: List[str]
    stale_feed_warnings: List[str] = Field(default_factory=list)
    last_event_timestamps: Dict[str, str] = Field(default_factory=dict)
