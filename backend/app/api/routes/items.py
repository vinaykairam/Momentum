from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from sqlalchemy import case

from app.core.database import get_db
from app.models.item import Item, ItemStatus
from app.models.stream import Stream
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.services.momentum_engine import refresh_all_stream_momentum

router = APIRouter(prefix="/items", tags=["items"])

STATUS_SORT = case(
    (Item.status == ItemStatus.next, 0),
    (Item.status == ItemStatus.active, 1),
    (Item.status == ItemStatus.backlog, 2),
    (Item.status == ItemStatus.completed, 3),
    (Item.status == ItemStatus.archived, 4),
    else_=5,
)


@router.get("", response_model=list[ItemResponse])
def list_items(
    stream_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Item]:
    query = db.query(Item)
    if stream_id is not None:
        query = query.filter(Item.stream_id == stream_id)
    return query.order_by(STATUS_SORT, Item.created_at.asc(), Item.id.asc()).all()


@router.post("", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> Item:
    stream = db.get(Stream, payload.stream_id)
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")

    item = Item(**payload.model_dump())
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

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, key, value)

    stream = db.get(Stream, item.stream_id)
    if stream:
        stream.last_activity_date = datetime.now(timezone.utc).date()
        refresh_all_stream_momentum(db)

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
