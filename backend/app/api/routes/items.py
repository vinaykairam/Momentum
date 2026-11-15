from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.item import Item, ItemStatus
from app.models.stream import Stream
from app.schemas.item import ItemCreate, ItemResponse, ItemUpdate
from app.schemas.item_reorder import ItemReorderRequest
from app.services import genius_lab
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


CSV_COLUMNS = [
    "id",
    "title",
    "stream",
    "status",
    "item_type",
    "importance",
    "effort_estimate",
    "estimated_duration",
    "queue_position",
    "url",
    "description",
    "notes",
    "created_at",
    "updated_at",
    "last_accessed",
]


def _csv_value(value: object) -> object:
    if value is None:
        return ""
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


@router.get("/export.csv")
def export_items_csv(db: Session = Depends(get_db)) -> Response:
    streams = {stream.id: stream for stream in db.query(Stream).all()}

    def stream_path(stream_id: int) -> str:
        names: list[str] = []
        seen: set[int] = set()
        current = streams.get(stream_id)
        while current is not None and current.id not in seen:
            seen.add(current.id)
            names.append(current.name)
            current = streams.get(current.parent_id) if current.parent_id else None
        return " / ".join(reversed(names))

    items = db.query(Item).order_by(Item.stream_id, *item_queue_order()).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for item in items:
        row = []
        for column in CSV_COLUMNS:
            if column == "stream":
                row.append(stream_path(item.stream_id))
            else:
                row.append(_csv_value(getattr(item, column)))
        writer.writerow(row)

    filename = f"momentum-items-{datetime.now(timezone.utc).date().isoformat()}.csv"
    # BOM so Excel opens UTF-8 correctly
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


@router.get("/{item_id}/lab-neighbors")
def get_lab_neighbors(item_id: int, db: Session = Depends(get_db)) -> dict:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return genius_lab.lesson_neighbors(db, item)


@router.patch("/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Item:
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

    if item.status == ItemStatus.completed and previous_status != ItemStatus.completed:
        if genius_lab.is_genius_lab_stream(db, item.stream_id):
            background_tasks.add_task(genius_lab.queue_next_lesson)
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
