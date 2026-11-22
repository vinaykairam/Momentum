from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.item import Item, ItemStatus
from app.models.stream import Stream
from app.schemas.item import ItemCreate, ItemProgressRequest, ItemResponse, ItemSnoozeRequest, ItemUpdate
from app.schemas.item_reorder import ItemReorderRequest
from app.services import genius_lab, item_coach
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
def create_item(
    payload: ItemCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> Item:
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


def _get_item_or_404(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def _touch_stream(db: Session, stream_id: int) -> None:
    stream = db.get(Stream, stream_id)
    if stream:
        stream.last_activity_date = date.today()
    refresh_all_stream_momentum(db)


@router.post("/{item_id}/first-step", response_model=ItemResponse)
def first_step(item_id: int, db: Session = Depends(get_db)) -> Item:
    """Write a tiny first step for the item if it has none yet."""
    item = _get_item_or_404(db, item_id)
    if not item.first_step and item_coach.wants_first_step(db, item):
        step = item_coach.generate_first_step(item)
        if step:
            item.first_step = step
            db.commit()
            db.refresh(item)
    return item


@router.post("/{item_id}/progress", response_model=ItemResponse)
def log_progress(
    item_id: int,
    payload: ItemProgressRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Item:
    """Worked on it but not finished: counts as activity, rests until tomorrow, gets a fresh first step."""
    item = _get_item_or_404(db, item_id)
    if payload.notes is not None:
        item.notes = payload.notes.strip() or None
    item.skip_count = 0
    item.snoozed_until = date.today() + timedelta(days=1)
    item.last_accessed = datetime.now(timezone.utc)
    _touch_stream(db, item.stream_id)
    db.commit()
    db.refresh(item)
    background_tasks.add_task(item_coach.fill_first_step, item.id, True)
    return item


@router.post("/{item_id}/snooze", response_model=ItemResponse)
def snooze_item(item_id: int, payload: ItemSnoozeRequest, db: Session = Depends(get_db)) -> Item:
    """Not today: hide from Today for `days` and count the skip."""
    item = _get_item_or_404(db, item_id)
    if payload.notes is not None:
        item.notes = payload.notes.strip() or None
    item.skip_count = (item.skip_count or 0) + 1
    item.snoozed_until = date.today() + timedelta(days=payload.days)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/split", response_model=list[ItemResponse])
def split_item(
    item_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> list[Item]:
    """Too big: Gemini breaks the item into 2-4 smaller steps that replace it in the queue."""
    item = _get_item_or_404(db, item_id)
    if item.status not in (ItemStatus.next, ItemStatus.active, ItemStatus.backlog):
        raise HTTPException(status_code=400, detail="Only queued items can be split")
    if genius_lab.is_genius_lab_stream(db, item.stream_id):
        raise HTTPException(status_code=400, detail="Lab lessons can't be split")
    created = item_coach.split_item(db, item)
    if created is None:
        raise HTTPException(status_code=503, detail="Couldn't split this right now. Try again, or edit it by hand.")
    item.queue_position = next_queue_position(db, item.stream_id, ItemStatus.archived)
    _touch_stream(db, item.stream_id)
    db.commit()
    for child in created:
        db.refresh(child)
    # Only the step that will show on Today needs a first step straight away.
    background_tasks.add_task(item_coach.fill_first_step, created[0].id)
    return created


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
