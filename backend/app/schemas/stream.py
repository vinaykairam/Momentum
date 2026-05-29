from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.stream import MomentumState, StreamCategory, StreamType


class StreamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    category: StreamCategory = StreamCategory.custom
    type: StreamType = StreamType.short_term
    priority_weight: float = Field(default=1.0, ge=0.1, le=10.0)
    active: bool = True


class StreamCreate(StreamBase):
    pass


class StreamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category: StreamCategory | None = None
    type: StreamType | None = None
    priority_weight: float | None = Field(default=None, ge=0.1, le=10.0)
    active: bool | None = None


class StreamResponse(StreamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    momentum_score: float
    momentum_state: MomentumState
    last_activity_date: date | None
    created_at: datetime
    updated_at: datetime
