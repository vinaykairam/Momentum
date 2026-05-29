from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.item import Item, ItemEffort, ItemStatus
from app.models.stream import MomentumState, Stream
from app.schemas.focus import FocusRecommendation, MomentumAlert


def score_to_state(score: float) -> MomentumState:
    if score >= 80:
        return MomentumState.thriving
    if score >= 60:
        return MomentumState.healthy
    if score >= 40:
        return MomentumState.slowing
    if score >= 20:
        return MomentumState.neglected
    return MomentumState.critical


def compute_momentum_score(stream: Stream, db: Session) -> float:
    """Compute momentum score from stream activity signals."""
    base = 50.0
    weight = stream.priority_weight

    if stream.last_activity_date:
        days_since = (date.today() - stream.last_activity_date).days
        decay = max(0, 100 - days_since * 4)
        base = decay * 0.6 + base * 0.4

    active_items = (
        db.query(Item)
        .filter(Item.stream_id == stream.id, Item.status.in_([ItemStatus.active, ItemStatus.next]))
        .count()
    )
    completed_recent = (
        db.query(Item)
        .filter(Item.stream_id == stream.id, Item.status == ItemStatus.completed)
        .count()
    )

    engagement_boost = min(20, active_items * 5 + completed_recent * 2)
    score = min(100.0, max(0.0, base * 0.7 + engagement_boost + weight * 3))
    return round(score, 1)


def update_stream_momentum(stream: Stream, db: Session) -> None:
    stream.momentum_score = compute_momentum_score(stream, db)
    stream.momentum_state = score_to_state(stream.momentum_score)


def _pick_action_item(stream: Stream, db: Session) -> Item | None:
    return (
        db.query(Item)
        .filter(
            Item.stream_id == stream.id,
            Item.status.in_([ItemStatus.next, ItemStatus.active, ItemStatus.backlog]),
        )
        .order_by(Item.status.desc(), Item.updated_at.desc())
        .first()
    )


def _recovery_action(stream: Stream, item: Item | None) -> tuple[str, int]:
    if item and item.effort_estimate == ItemEffort.tiny:
        return item.title, item.estimated_duration or 15

    name = stream.name
    if item:
        return f"Spend 15 minutes on {item.title}", 15
    return f"Spend 15 minutes on {name}", 15


def _normal_action(item: Item | None, stream: Stream) -> tuple[str, int]:
    if item:
        duration = item.estimated_duration or {"tiny": 15, "small": 30, "medium": 45, "large": 90}.get(
            item.effort_estimate.value, 45
        )
        return item.title, duration
    return f"Review {stream.name} progress", 30


def generate_daily_focus(db: Session, max_items: int = 5) -> list[FocusRecommendation]:
    streams = db.query(Stream).filter(Stream.active.is_(True)).all()

    for stream in streams:
        update_stream_momentum(stream, db)
    db.commit()

    # Prioritize neglected streams (lower score = higher priority)
    sorted_streams = sorted(streams, key=lambda s: (s.momentum_score, -s.priority_weight))

    recommendations: list[FocusRecommendation] = []
    for stream in sorted_streams:
        if len(recommendations) >= max_items:
            break

        item = _pick_action_item(stream, db)
        recovery = stream.momentum_score < 20

        if recovery:
            action, minutes = _recovery_action(stream, item)
        else:
            action, minutes = _normal_action(item, stream)

        recommendations.append(
            FocusRecommendation(
                stream_id=stream.id,
                stream_name=stream.name,
                item_id=item.id if item else None,
                action=action,
                estimated_minutes=minutes,
                momentum_score=stream.momentum_score,
                momentum_state=stream.momentum_state.value,
                recovery_mode=recovery,
            )
        )

    return recommendations


def generate_alerts(db: Session) -> list[MomentumAlert]:
    streams = db.query(Stream).filter(Stream.active.is_(True)).all()
    alerts: list[MomentumAlert] = []

    for stream in streams:
        if stream.momentum_score < 20:
            alerts.append(
                MomentumAlert(
                    stream_id=stream.id,
                    stream_name=stream.name,
                    message=f"{stream.name} is entering critical state — high abandonment risk",
                    severity="critical",
                    momentum_score=stream.momentum_score,
                )
            )
        elif stream.momentum_score < 40:
            days = (date.today() - stream.last_activity_date).days if stream.last_activity_date else None
            msg = f"{stream.name} momentum is declining"
            if days and days >= 7:
                msg = f"{stream.name} has not received attention in {days} days"
            alerts.append(
                MomentumAlert(
                    stream_id=stream.id,
                    stream_name=stream.name,
                    message=msg,
                    severity="warning",
                    momentum_score=stream.momentum_score,
                )
            )
        elif stream.momentum_score >= 80:
            alerts.append(
                MomentumAlert(
                    stream_id=stream.id,
                    stream_name=stream.name,
                    message=f"{stream.name} momentum is improving",
                    severity="positive",
                    momentum_score=stream.momentum_score,
                )
            )

    return sorted(alerts, key=lambda a: a.momentum_score)


def get_recent_progress(db: Session, limit: int = 8) -> list[dict]:
    items = (
        db.query(Item)
        .filter(Item.status == ItemStatus.completed)
        .order_by(Item.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "item_id": item.id,
            "title": item.title,
            "stream_id": item.stream_id,
            "completed_at": item.updated_at.isoformat() if item.updated_at else None,
        }
        for item in items
    ]
