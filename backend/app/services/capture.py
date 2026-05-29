from __future__ import annotations

import re
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.item import Item, ItemType
from app.models.stream import Stream
from app.schemas.focus import CaptureResponse


YOUTUBE_PATTERN = re.compile(r"(youtube\.com|youtu\.be)", re.I)
URL_PATTERN = re.compile(r"https?://[^\s]+", re.I)


def _detect_item_type(content: str) -> ItemType:
    if YOUTUBE_PATTERN.search(content):
        return ItemType.youtube
    if URL_PATTERN.search(content):
        return ItemType.link
    if len(content) > 200:
        return ItemType.note
    if content.strip().endswith("?"):
        return ItemType.idea
    return ItemType.task


def _extract_title(content: str, item_type: ItemType) -> str:
    content = content.strip()
    url_match = URL_PATTERN.search(content)
    if url_match and item_type in (ItemType.youtube, ItemType.link):
        return url_match.group(0)[:120]
    first_line = content.split("\n")[0].strip()
    return first_line[:500] if first_line else "Untitled capture"


def _suggest_stream(content: str, streams: list[Stream]) -> tuple[Stream | None, float]:
    if not streams:
        return None, 0.0

    content_lower = content.lower()
    best: Stream | None = None
    best_score = 0.0

    for stream in streams:
        score = 0.0
        name_parts = stream.name.lower().split()
        for part in name_parts:
            if len(part) > 2 and part in content_lower:
                score += 0.35
        if stream.description and any(w in content_lower for w in stream.description.lower().split()[:10]):
            score += 0.2
        score += stream.priority_weight * 0.05
        if score > best_score:
            best_score = score
            best = stream

    if best is None:
        best = streams[0]
        best_score = 0.5

    confidence = min(0.96, max(0.4, best_score + 0.4))
    return best, round(confidence, 2)


def classify_and_capture(content: str, db: Session) -> CaptureResponse:
    item_type = _detect_item_type(content)
    title = _extract_title(content, item_type)
    url = None
    url_match = URL_PATTERN.search(content)
    if url_match:
        url = url_match.group(0)

    streams = db.query(Stream).filter(Stream.active.is_(True)).all()
    suggested_stream, confidence = _suggest_stream(content, streams)

    item = Item(
        stream_id=suggested_stream.id if suggested_stream else streams[0].id,
        title=title,
        description=content if item_type == ItemType.note else None,
        url=url,
        item_type=item_type,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    return CaptureResponse(
        item_id=item.id,
        title=title,
        item_type=item_type.value,
        suggested_stream_id=suggested_stream.id if suggested_stream else None,
        suggested_stream_name=suggested_stream.name if suggested_stream else None,
        confidence=confidence,
        summary=content[:200] if len(content) > 200 else None,
    )
