from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from sqlalchemy import text

from app.api.routes import focus, items, streams
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine, get_db
from app.models import Item, Stream
from app.models.item import ItemEffort, ItemImportance, ItemStatus, ItemType
from app.models.stream import StreamCategory, StreamType
from app.services import math_genius
from app.services.momentum_engine import generate_daily_focus, refresh_all_stream_momentum
from app.services.static_home import render_today_page
from app.services.stream_constants import DEFAULT_STREAM_DESCRIPTIONS, WORKOUT_SUB_STREAMS


def _create_workout_sub_streams(db, workout: Stream, today: date) -> list[Stream]:
    sub_streams = []
    for index, name in enumerate(WORKOUT_SUB_STREAMS):
        sub_stream = Stream(
            name=name,
            parent_id=workout.id,
            category=workout.category,
            type=workout.type,
            priority_weight=workout.priority_weight,
            description=DEFAULT_STREAM_DESCRIPTIONS.get(name),
            last_activity_date=today - timedelta(days=index + 1),
        )
        db.add(sub_stream)
        sub_streams.append(sub_stream)
    return sub_streams


def ensure_stream_descriptions() -> None:
    db = SessionLocal()
    try:
        for stream in db.query(Stream).all():
            if not stream.description and stream.name in DEFAULT_STREAM_DESCRIPTIONS:
                stream.description = DEFAULT_STREAM_DESCRIPTIONS[stream.name]
        db.commit()
    finally:
        db.close()


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(Stream).count() > 0:
            return

        today = date.today()
        workout = Stream(
            name="Workout",
            description=DEFAULT_STREAM_DESCRIPTIONS["Workout"],
            category=StreamCategory.weekday,
            type=StreamType.short_term,
            priority_weight=1.0,
        )
        study = Stream(
            name="Study",
            description=DEFAULT_STREAM_DESCRIPTIONS["Study"],
            category=StreamCategory.weekday,
            type=StreamType.long_term,
            priority_weight=1.1,
            last_activity_date=today - timedelta(days=5),
        )
        garage = Stream(
            name="Garage Projects",
            description=DEFAULT_STREAM_DESCRIPTIONS["Garage Projects"],
            category=StreamCategory.weekend,
            type=StreamType.long_term,
            priority_weight=0.9,
            last_activity_date=today - timedelta(days=24),
        )
        db.add(workout)
        db.add(study)
        db.add(garage)
        db.flush()

        cardio, strong_lifts = _create_workout_sub_streams(db, workout, today)
        db.flush()

        demo_items = [
            (cardio, "30 Minute Run", ItemType.task, ItemStatus.next, 30),
            (strong_lifts, "Squat / Bench / Rows", ItemType.task, ItemStatus.next, 60),
            (study, "Watch Kubernetes Lesson", ItemType.youtube, ItemStatus.next, 30),
            (garage, "Welding Cart — Install Wheels", ItemType.project, ItemStatus.active, 45),
        ]
        for stream, title, itype, status, duration in demo_items:
            db.add(
                Item(
                    stream_id=stream.id,
                    title=title,
                    item_type=itype,
                    status=status,
                    importance=ItemImportance.high,
                    effort_estimate=ItemEffort.medium,
                    estimated_duration=duration,
                )
            )

        refresh_all_stream_momentum(db)

        db.commit()
    finally:
        db.close()


def ensure_item_notes_column() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        columns = conn.execute(text("PRAGMA table_info(items)")).fetchall()
        if not any(column[1] == "notes" for column in columns):
            conn.execute(text("ALTER TABLE items ADD COLUMN notes TEXT"))
            conn.commit()


def ensure_item_queue_position_column() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        columns = conn.execute(text("PRAGMA table_info(items)")).fetchall()
        if not any(column[1] == "queue_position" for column in columns):
            conn.execute(text("ALTER TABLE items ADD COLUMN queue_position INTEGER NOT NULL DEFAULT 0"))
            conn.commit()

    db = SessionLocal()
    try:
        rows = (
            db.query(Item)
            .order_by(Item.stream_id, Item.status, Item.created_at.asc(), Item.id.asc())
            .all()
        )
        counters: dict[tuple[int, ItemStatus], int] = {}
        changed = False
        for row in rows:
            key = (row.stream_id, row.status)
            expected = counters.get(key, 0)
            if row.queue_position != expected:
                row.queue_position = expected
                changed = True
            counters[key] = expected + 1
        if changed:
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_item_notes_column()
    ensure_item_queue_position_column()
    if settings.seed_demo_data:
        seed_demo_data()
    ensure_stream_descriptions()
    # Create the Math Me Genius stream and first lesson without blocking startup.
    threading.Thread(target=math_genius.queue_next_lesson, daemon=True).start()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(streams.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(focus.router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


@app.get("/eink", response_class=HTMLResponse)
def eink_home(db: Session = Depends(get_db)) -> HTMLResponse:
    refresh_all_stream_momentum(db)
    db.commit()
    focus = generate_daily_focus(db)
    return HTMLResponse(content=render_today_page(focus))
