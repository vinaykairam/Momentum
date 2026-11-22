import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ItemType(str, enum.Enum):
    task = "task"
    project = "project"
    youtube = "youtube"
    article = "article"
    course = "course"
    note = "note"
    bookmark = "bookmark"
    idea = "idea"
    pdf = "pdf"
    resource = "resource"
    link = "link"
    video = "video"
    document = "document"


class ItemStatus(str, enum.Enum):
    backlog = "backlog"
    next = "next"
    active = "active"
    completed = "completed"
    archived = "archived"


class ItemImportance(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ItemEffort(str, enum.Enum):
    tiny = "tiny"
    small = "small"
    medium = "medium"
    large = "large"


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    stream_id: Mapped[int] = mapped_column(ForeignKey("streams.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    item_type: Mapped[ItemType] = mapped_column(Enum(ItemType, name="item_type"), nullable=False, default=ItemType.task)
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, name="item_status"), nullable=False, default=ItemStatus.backlog
    )
    importance: Mapped[ItemImportance] = mapped_column(
        Enum(ItemImportance, name="item_importance"), default=ItemImportance.medium
    )
    effort_estimate: Mapped[ItemEffort] = mapped_column(
        Enum(ItemEffort, name="item_effort"), default=ItemEffort.medium
    )
    estimated_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    queue_position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    last_accessed: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Smallest concrete action to get started (written by Gemini).
    first_step: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Times this item was put off ("not today"); reset when you make progress.
    skip_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    # Hidden from Today until this date.
    snoozed_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Workouts only. Plan: [{name, sets, reps, weight_lb}] written by Gemini.
    # Log: [{exercise, sets: [{reps, weight}]}] entered after the workout (weight in lb).
    workout_plan: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    workout_log: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    stream = relationship("Stream", back_populates="items")
