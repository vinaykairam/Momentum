from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.stream import Stream
from app.schemas.focus import CaptureRequest, CaptureResponse, DailyFocusResponse, DashboardResponse
from app.services.capture import classify_and_capture
from app.services.momentum_engine import (
    generate_alerts,
    generate_daily_focus,
    get_recent_progress,
    update_stream_momentum,
)

router = APIRouter(tags=["focus"])


@router.get("/focus/today", response_model=DailyFocusResponse)
def get_todays_focus(db: Session = Depends(get_db)) -> DailyFocusResponse:
    recommendations = generate_daily_focus(db)
    return DailyFocusResponse(
        recommendations=recommendations,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardResponse:
    streams = db.query(Stream).filter(Stream.active.is_(True)).all()
    for stream in streams:
        update_stream_momentum(stream, db)
    db.commit()

    stream_data = [
        {
            "id": s.id,
            "name": s.name,
            "momentum_score": s.momentum_score,
            "momentum_state": s.momentum_state.value,
            "category": s.category.value,
        }
        for s in sorted(streams, key=lambda x: x.momentum_score)
    ]

    return DashboardResponse(
        todays_focus=generate_daily_focus(db),
        streams=stream_data,
        alerts=generate_alerts(db),
        recent_progress=get_recent_progress(db),
    )


@router.post("/capture", response_model=CaptureResponse, status_code=201)
def capture(payload: CaptureRequest, db: Session = Depends(get_db)) -> CaptureResponse:
    return classify_and_capture(payload.content, db)
