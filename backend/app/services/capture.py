from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.item import Item, ItemStatus, ItemType
from app.services.item_queue import next_queue_position
from app.models.stream import Stream
from app.schemas.focus import CaptureResponse
from app.services.momentum_engine import stream_display_name
from app.services.url_metadata import fetch_url_context

YOUTUBE_PATTERN = re.compile(r"(youtube\.com|youtu\.be)", re.I)
URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)


def _detect_item_type(content: str, url: str | None = None) -> ItemType:
    target = url or content
    if YOUTUBE_PATTERN.search(target):
        return ItemType.youtube
    if URL_PATTERN.search(target):
        return ItemType.link
    if len(content) > 200:
        return ItemType.note
    if content.strip().endswith("?"):
        return ItemType.idea
    return ItemType.task


def _extract_title(content: str, item_type: ItemType, url_context: str | None = None) -> str:
    if url_context:
        return url_context[:500]

    content = content.strip()
    url_match = URL_PATTERN.search(content)
    if url_match and item_type in (ItemType.youtube, ItemType.link):
        return url_match.group(0)[:120]

    first_line = content.split("\n")[0].strip()
    return first_line[:500] if first_line else "Untitled capture"


def capture_item(content: str, db: Session, stream_id: int) -> CaptureResponse:
    streams = db.query(Stream).filter(Stream.active.is_(True)).all()
    if not streams:
        raise ValueError("Add a stream before capturing items")

    streams_by_id = {stream.id: stream for stream in streams}
    target_stream = streams_by_id.get(stream_id)
    if not target_stream:
        raise ValueError("Selected stream not found")

    url_match = URL_PATTERN.search(content)
    url = url_match.group(0) if url_match else None
    url_context = fetch_url_context(url) if url else None

    item_type = _detect_item_type(content, url)
    title = _extract_title(content, item_type, url_context)

    item = Item(
        stream_id=target_stream.id,
        title=title,
        description=content if item_type == ItemType.note else None,
        url=url,
        item_type=item_type,
    )
    item.queue_position = next_queue_position(db, item.stream_id, ItemStatus.backlog)
    db.add(item)
    db.commit()
    db.refresh(item)

    stream_name, parent_name = stream_display_name(target_stream, streams_by_id)
    display_name = f"{parent_name} · {stream_name}" if parent_name else stream_name

    return CaptureResponse(
        item_id=item.id,
        title=title,
        item_type=item_type.value,
        stream_id=target_stream.id,
        stream_name=display_name,
    )
