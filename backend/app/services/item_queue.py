from __future__ import annotations

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.item import Item, ItemStatus

STATUS_SORT = case(
    (Item.status == ItemStatus.next, 0),
    (Item.status == ItemStatus.active, 1),
    (Item.status == ItemStatus.backlog, 2),
    (Item.status == ItemStatus.completed, 3),
    (Item.status == ItemStatus.archived, 4),
    else_=5,
)

QUEUED_STATUSES = (ItemStatus.next, ItemStatus.active, ItemStatus.backlog)


def item_queue_order():
    return (STATUS_SORT, Item.queue_position.asc(), Item.created_at.asc(), Item.id.asc())


def next_queue_position(db: Session, stream_id: int, status: ItemStatus) -> int:
    max_pos = (
        db.query(func.max(Item.queue_position))
        .filter(Item.stream_id == stream_id, Item.status == status)
        .scalar()
    )
    return (max_pos if max_pos is not None else -1) + 1


def reorder_item(db: Session, item: Item, direction: str) -> None:
    siblings = (
        db.query(Item)
        .filter(
            Item.stream_id == item.stream_id,
            Item.status == item.status,
            Item.status.in_(QUEUED_STATUSES),
        )
        .order_by(Item.queue_position.asc(), Item.created_at.asc(), Item.id.asc())
        .all()
    )

    index = next((i for i, row in enumerate(siblings) if row.id == item.id), None)
    if index is None:
        return

    if direction == "up":
        if index == 0:
            return
        neighbor = siblings[index - 1]
    elif direction == "down":
        if index >= len(siblings) - 1:
            return
        neighbor = siblings[index + 1]
    else:
        return

    item.queue_position, neighbor.queue_position = neighbor.queue_position, item.queue_position
