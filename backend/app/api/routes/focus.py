from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.focus import CaptureRequest, CaptureResponse, DailyFocusResponse, DashboardResponse
from app.services.capture import capture_item
from app.services.momentum_engine import (
    generate_daily_focus,
    refresh_all_stream_momentum,
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
    refresh_all_stream_momentum(db)
    db.commit()
    return DashboardResponse(todays_focus=generate_daily_focus(db))


@router.post("/capture", response_model=CaptureResponse, status_code=201)
def capture(payload: CaptureRequest, db: Session = Depends(get_db)) -> CaptureResponse:
    try:
        return capture_item(payload.content, db, stream_id=payload.stream_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
