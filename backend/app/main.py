from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import focus, items, streams
from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import Item, Stream
from app.models.item import ItemEffort, ItemImportance, ItemStatus, ItemType
from app.models.stream import StreamCategory, StreamType
from app.services.momentum_engine import update_stream_momentum


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(Stream).count() > 0:
            return

        today = date.today()
        demo_streams = [
            Stream(
                name="Work",
                category=StreamCategory.weekday,
                type=StreamType.short_term,
                priority_weight=1.2,
                last_activity_date=today,
            ),
            Stream(
                name="Workout",
                category=StreamCategory.weekday,
                type=StreamType.short_term,
                priority_weight=1.0,
                last_activity_date=today - timedelta(days=1),
            ),
            Stream(
                name="Study",
                category=StreamCategory.weekday,
                type=StreamType.long_term,
                priority_weight=1.1,
                last_activity_date=today - timedelta(days=5),
            ),
            Stream(
                name="Garage Projects",
                category=StreamCategory.weekend,
                type=StreamType.long_term,
                priority_weight=0.9,
                last_activity_date=today - timedelta(days=24),
            ),
            Stream(
                name="Long-Term Projects",
                category=StreamCategory.custom,
                type=StreamType.long_term,
                priority_weight=1.0,
                last_activity_date=today - timedelta(days=30),
            ),
        ]
        for s in demo_streams:
            db.add(s)
        db.flush()

        demo_items = [
            (demo_streams[0], "Finish Architecture Review", ItemType.task, ItemStatus.next, 45),
            (demo_streams[1], "Upper Body Session", ItemType.task, ItemStatus.next, 60),
            (demo_streams[2], "Watch Kubernetes Lesson", ItemType.youtube, ItemStatus.next, 30),
            (demo_streams[3], "Welding Cart — Install Wheels", ItemType.project, ItemStatus.active, 45),
            (demo_streams[4], "Side Business MVP Planning", ItemType.project, ItemStatus.backlog, 90),
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

        for stream in demo_streams:
            update_stream_momentum(stream, db)

        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_demo_data()
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
