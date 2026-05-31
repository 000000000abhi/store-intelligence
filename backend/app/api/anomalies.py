from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.models.models import Anomaly
from app.schemas.schemas import AnomaliesResponse, AnomalyResponseItem

router = APIRouter()

@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(store_id: str, db: Session = Depends(get_db)):
    active_anomalies = db.query(Anomaly).filter(
        Anomaly.store_id == store_id,
        Anomaly.resolved == False
    ).order_by(Anomaly.triggered_at.desc()).all()
    
    items = []
    for a in active_anomalies:
        items.append(AnomalyResponseItem(
            type=a.type,
            severity=a.severity,
            description=a.description,
            suggested_action=a.suggested_action,
            triggered_at=a.triggered_at
        ))
        
    return AnomaliesResponse(
        store_id=store_id,
        anomalies=items
    )
