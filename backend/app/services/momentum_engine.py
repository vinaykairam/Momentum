from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.models.item import Item, ItemEffort, ItemStatus
from app.services.item_queue import QUEUED_STATUSES, item_queue_order
from app.models.stream import MomentumState, Stream, StreamCategory
from app.schemas.focus import FocusRecommendation

def _is_weekend(day: date | None = None) -> bool:
    check = day or date.today()
    return check.weekday() >= 5


def _stream_map(streams: list[Stream]) -> dict[int, Stream]:
    return {stream.id: stream for stream in streams}


def effective_category(stream: Stream, streams_by_id: dict[int, Stream]) -> StreamCategory:
    if stream.parent_id and stream.parent_id in streams_by_id:
        return streams_by_id[stream.parent_id].category
    return stream.category


def streams_relevant_today(streams: list[Stream], day: date | None = None) -> list[Stream]:
    """Weekday streams Mon–Fri; weekend streams Sat–Sun; everyday streams always."""
    streams_by_id = _stream_map(streams)
    weekend = _is_weekend(day)

    def is_relevant(category: StreamCategory) -> bool:
        if category in (StreamCategory.everyday, StreamCategory.custom):
            return True
        if weekend:
            return category == StreamCategory.weekend
        return category == StreamCategory.weekday

    return [
        stream
        for stream in streams
        if is_relevant(effective_category(stream, streams_by_id))
    ]


def has_children(stream_id: int, streams: list[Stream]) -> bool:
    return any(stream.parent_id == stream_id for stream in streams)


def focusable_streams(streams: list[Stream]) -> list[Stream]:
    """Leaf streams only — parent containers are excluded from focus."""
    return [stream for stream in streams if not has_children(stream.id, streams)]


def stream_display_name(stream: Stream, streams_by_id: dict[int, Stream]) -> tuple[str, str | None]:
    if stream.parent_id and stream.parent_id in streams_by_id:
        return stream.name, streams_by_id[stream.parent_id].name
    return stream.name, None


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


def _update_leaf_momentum(stream: Stream, db: Session) -> None:
    stream.momentum_score = compute_momentum_score(stream, db)
    stream.momentum_state = score_to_state(stream.momentum_score)


def refresh_all_stream_momentum(db: Session) -> None:
    streams = db.query(Stream).filter(Stream.active.is_(True)).all()
    children_by_parent: dict[int, list[Stream]] = defaultdict(list)
    for stream in streams:
        if stream.parent_id:
            children_by_parent[stream.parent_id].append(stream)

    def update_node(stream: Stream) -> None:
        children = children_by_parent.get(stream.id, [])
        if children:
            for child in children:
                update_node(child)
            stream.momentum_score = round(sum(child.momentum_score for child in children) / len(children), 1)
            stream.momentum_state = score_to_state(stream.momentum_score)
            child_dates = [child.last_activity_date for child in children if child.last_activity_date]
            if child_dates:
                stream.last_activity_date = max(child_dates)
        else:
            _update_leaf_momentum(stream, db)

    for stream in streams:
        if stream.parent_id is None:
            update_node(stream)


def update_stream_momentum(stream: Stream, db: Session) -> None:
    refresh_all_stream_momentum(db)


def _pick_action_item(stream: Stream, db: Session) -> Item | None:
    """Top queued item for this stream, matching the Items page order."""
    return (
        db.query(Item)
        .filter(Item.stream_id == stream.id, Item.status.in_(QUEUED_STATUSES))
        .order_by(*item_queue_order())
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
    """Up to one queued item per stream (oldest per stream), across today's focusable streams."""
    streams = db.query(Stream).filter(Stream.active.is_(True)).all()
    refresh_all_stream_momentum(db)
    db.commit()

    streams_by_id = _stream_map(streams)
    today_streams = focusable_streams(streams_relevant_today(streams))
    sorted_streams = sorted(today_streams, key=lambda stream: (stream.momentum_score, -stream.priority_weight))

    recommendations: list[FocusRecommendation] = []
    for stream in sorted_streams:
        if len(recommendations) >= max_items:
            break

        item = _pick_action_item(stream, db)
        if not item:
            continue

        recovery = stream.momentum_score < 20
        stream_name, parent_name = stream_display_name(stream, streams_by_id)

        if recovery:
            action, minutes = _recovery_action(stream, item)
        else:
            action, minutes = _normal_action(item, stream)

        recommendations.append(
            FocusRecommendation(
                stream_id=stream.id,
                stream_name=stream_name,
                parent_stream_name=parent_name,
                item_id=item.id,
                action=action,
                estimated_minutes=minutes,
                momentum_score=stream.momentum_score,
                momentum_state=stream.momentum_state.value,
                recovery_mode=recovery,
            )
        )

    return recommendations
