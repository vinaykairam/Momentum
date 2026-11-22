from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.item import ItemEffort, ItemImportance, ItemStatus, ItemType


class WorkoutSet(BaseModel):
    reps: float | None = Field(default=None, ge=0)  # reps, or seconds for holds
    weight: float | None = Field(default=None, ge=0)  # lb; empty for bodyweight


class WorkoutLogEntry(BaseModel):
    exercise: str = Field(..., min_length=1, max_length=200)
    sets: list[WorkoutSet] = Field(default_factory=list, max_length=20)


class ItemBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    notes: str | None = None
    url: str | None = None
    item_type: ItemType = ItemType.task
    status: ItemStatus = ItemStatus.backlog
    importance: ItemImportance = ItemImportance.medium
    effort_estimate: ItemEffort = ItemEffort.medium
    estimated_duration: int | None = Field(default=None, ge=1)


class ItemCreate(ItemBase):
    stream_id: int


class ItemUpdate(BaseModel):
    stream_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = None
    notes: str | None = None
    url: str | None = None
    item_type: ItemType | None = None
    status: ItemStatus | None = None
    importance: ItemImportance | None = None
    effort_estimate: ItemEffort | None = None
    estimated_duration: int | None = Field(default=None, ge=1)
    workout_log: list[WorkoutLogEntry] | None = Field(default=None, max_length=30)


class ItemResponse(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stream_id: int
    queue_position: int
    created_at: datetime
    updated_at: datetime
    last_accessed: datetime | None
    first_step: str | None = None
    skip_count: int = 0
    snoozed_until: date | None = None
    workout_plan: list[dict] | None = None
    workout_log: list[dict] | None = None


class ItemProgressRequest(BaseModel):
    notes: str | None = None


class ItemSnoozeRequest(BaseModel):
    days: int = Field(default=1, ge=1, le=60)
    notes: str | None = None
