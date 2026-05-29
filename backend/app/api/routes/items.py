from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.item import Item, ItemStatus
from app.models.stream import Stream
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.schemas.item_reorder import ItemReorderRequest
from app.services.item_queue import item_queue_order, next_queue_position, reorder_item
from app.services.momentum_engine import refresh_all_stream_momentum

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemResponse])
def list_items(
    stream_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Item]:
    query = db.query(Item)
    if stream_id is not None:
        query = query.filter(Item.stream_id == stream_id)
    return query.order_by(*item_queue_order()).all()


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    stream = db.get(Stream, payload.stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    data = payload.model_dump()
    item = Item(**data)
    item.queue_position = next_queue_position(db, item.stream_id, item.status)
    db.add(item)
    stream.last_activity_date = datetime.now(timezone.utc).date()
    refresh_all_stream_momentum(db)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    item.last_accessed = datetime.now(timezone.utc)
    db.commit()
    return item


@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    if payload.stream_id is not None:
        stream = db.get(Stream, payload.stream_id)
        if not stream:
            raise HTTPException(status_code=404, detail="Stream not found")

    updates = payload.model_dump(exclude_unset=True)
    previous_status = item.status
    for key, value in updates.items():
        setattr(item, key, value)

    if "status" in updates and updates["status"] != previous_status:
        item.queue_position = next_queue_position(db, item.stream_id, item.status)
    if "stream_id" in updates:
        item.queue_position = next_queue_position(db, item.stream_id, item.status)

    stream = db.get(Stream, item.stream_id)
    if stream:
        stream.last_activity_date = datetime.now(timezone.utc).date()
        refresh_all_stream_momentum(db)

    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/reorder", response_model=ItemResponse)
def reorder_item_endpoint(
    item_id: int, payload: ItemReorderRequest, db: Session = Depends(get_db)
) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.status not in (ItemStatus.next, ItemStatus.active, ItemStatus.backlog):
        raise HTTPException(status_code=400, detail="Only queued items can be reordered")

    reorder_item(db, item, payload.direction)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> None:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    db.delete(item)
    db.commit()
