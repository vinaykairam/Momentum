from __future__ import annotations

from pydantic import BaseModel, Field


class FocusRecommendation(BaseModel):
    stream_id: int
    stream_name: str
    parent_stream_name: str | None = None
    item_id: int | None = None
    action: str
    estimated_minutes: int | None = None
    momentum_score: float
    momentum_state: str
    recovery_mode: bool = False


class DailyFocusResponse(BaseModel):
    recommendations: list[FocusRecommendation] = Field(..., max_length=5)
    generated_at: str


class DashboardResponse(BaseModel):
    todays_focus: list[FocusRecommendation]


class CaptureRequest(BaseModel):
    content: str = Field(..., min_length=1)
    stream_id: int


class CaptureResponse(BaseModel):
    item_id: int
    title: str
    item_type: str
    stream_id: int
    stream_name: str
