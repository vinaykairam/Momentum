from __future__ import annotations

from pydantic import BaseModel, Field


class FocusRecommendation(BaseModel):
    stream_id: int
    stream_name: str
    item_id: int | None = None
    action: str
    estimated_minutes: int | None = None
    momentum_score: float
    momentum_state: str
    recovery_mode: bool = False


class DailyFocusResponse(BaseModel):
    recommendations: list[FocusRecommendation] = Field(..., max_length=5)
    generated_at: str


class MomentumAlert(BaseModel):
    stream_id: int
    stream_name: str
    message: str
    severity: str
    momentum_score: float


class DashboardResponse(BaseModel):
    todays_focus: list[FocusRecommendation]
    streams: list[dict]
    alerts: list[MomentumAlert]
    recent_progress: list[dict]


class CaptureRequest(BaseModel):
    content: str = Field(..., min_length=1)


class CaptureResponse(BaseModel):
    item_id: int
    title: str
    item_type: str
    suggested_stream_id: int | None
    suggested_stream_name: str | None
    confidence: float
    summary: str | None = None
