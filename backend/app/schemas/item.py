from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.item import ItemEffort, ItemImportance, ItemStatus, ItemType


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


class ItemProgressRequest(BaseModel):
    notes: str | None = None


class ItemSnoozeRequest(BaseModel):
    days: int = Field(default=1, ge=1, le=60)
    notes: str | None = None
