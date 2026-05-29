import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StreamCategory(str, enum.Enum):
    weekday = "weekday"
    weekend = "weekend"
    custom = "custom"


class StreamType(str, enum.Enum):
    short_term = "short_term"
    long_term = "long_term"


class MomentumState(str, enum.Enum):
    thriving = "thriving"
    healthy = "healthy"
    slowing = "slowing"
    neglected = "neglected"
    critical = "critical"


class Stream(Base):
    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[StreamCategory] = mapped_column(
        Enum(StreamCategory, name="stream_category"), nullable=False, default=StreamCategory.custom
    )
    type: Mapped[StreamType] = mapped_column(
        Enum(StreamType, name="stream_type"), nullable=False, default=StreamType.short_term
    )
    priority_weight: Mapped[float] = mapped_column(Float, default=1.0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    momentum_score: Mapped[float] = mapped_column(Float, default=50.0)
    momentum_state: Mapped[MomentumState] = mapped_column(
        Enum(MomentumState, name="momentum_state"), default=MomentumState.slowing
    )
    last_activity_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    items = relationship("Item", back_populates="stream", cascade="all, delete-orphan")
