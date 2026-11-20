"""Gemini helpers that make items easier to start: a tiny first step, or a split into smaller steps."""

from __future__ import annotations

import json
import logging
import re

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.item import Item, ItemEffort, ItemStatus, ItemType
from app.services import courses

logger = logging.getLogger(__name__)

FIRST_STEP_MINUTES = 10


def _item_context(item: Item) -> str:
    lines = [f"Item: {item.title}"]
    if item.description:
        lines.append(f"Details: {item.description[:1500]}")
    if item.url:
        lines.append(f"Link: {item.url}")
    if item.notes:
        lines.append(f"Progress notes so far: {item.notes[:1500]}")
    return "\n".join(lines)


def _gemini_json(system: str, user: str) -> dict | None:
    if not settings.gemini_api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                url,
                params={"key": settings.gemini_api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                    "generationConfig": {
                        "temperature": 0.4,
                        "responseMimeType": "application/json",
                        "thinkingConfig": {"thinkingBudget": 0},
                    },
                },
            )
            response.raise_for_status()
            payload = response.json()
        parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
        raw = "".join(part.get("text", "") for part in parts).strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        return json.loads(fence.group(1) if fence else raw)
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        logger.warning("Item coach Gemini call failed: %s", exc)
        return None


def generate_first_step(item: Item) -> str | None:
    system = (
        "You help a procrastinating person get started. Given a task from their to-do list, reply with "
        f"the single smallest concrete physical action that starts it and takes under {FIRST_STEP_MINUTES} "
        "minutes. Make it so easy it feels silly not to do it (open the file, put on shoes, watch the first "
        "5 minutes, write one sentence). Imperative, at most 15 words, no preamble. If progress notes "
        "exist, the step continues from where they left off. "
        'Return JSON only: {"first_step": "..."}'
    )
    parsed = _gemini_json(system, _item_context(item))
    step = str((parsed or {}).get("first_step", "")).strip()
    return step[:300] or None


def generate_split(item: Item) -> list[str]:
    system = (
        "You break a to-do item that feels too big into 2 to 4 smaller, concrete steps, in order. "
        "Each step must be doable in one sitting of 30 minutes or less and be a clear action "
        "(start with a verb), at most 12 words. Skip anything already done according to the "
        'progress notes. Return JSON only: {"steps": ["...", "..."]}'
    )
    parsed = _gemini_json(system, _item_context(item))
    steps = [str(step).strip()[:500] for step in (parsed or {}).get("steps", []) if str(step).strip()]
    return steps[:4]


def wants_first_step(db: Session, item: Item) -> bool:
    return (
        item.status in (ItemStatus.next, ItemStatus.active, ItemStatus.backlog)
        and not courses.is_course_stream(db, item.stream_id)
    )


def fill_first_step(item_id: int, force: bool = False) -> None:
    """Background task: write a first step for an item that has none (or replace it when forced)."""
    db = SessionLocal()
    try:
        item = db.get(Item, item_id)
        if not item or not wants_first_step(db, item) or (item.first_step and not force):
            return
        step = generate_first_step(item)
        if step:
            item.first_step = step
            db.commit()
    finally:
        db.close()


def split_item(db: Session, item: Item) -> list[Item] | None:
    """Replace `item` with smaller steps at the same place in its queue. None if Gemini is unavailable."""
    steps = generate_split(item)
    if len(steps) < 2:
        return None

    siblings = (
        db.query(Item)
        .filter(
            Item.stream_id == item.stream_id,
            Item.status == item.status,
            Item.queue_position > item.queue_position,
        )
        .all()
    )
    for sibling in siblings:
        sibling.queue_position += len(steps) - 1

    created: list[Item] = []
    for offset, step in enumerate(steps):
        child = Item(
            stream_id=item.stream_id,
            title=step,
            description=f"Step {offset + 1} of {len(steps)} from: {item.title}",
            url=item.url,
            item_type=ItemType.task,
            status=item.status,
            importance=item.importance,
            effort_estimate=ItemEffort.small,
            estimated_duration=30,
            queue_position=item.queue_position + offset,
        )
        db.add(child)
        created.append(child)

    item.status = ItemStatus.archived
    split_note = "Split into: " + "; ".join(steps)
    item.notes = f"{item.notes}\n\n{split_note}" if item.notes else split_note
    return created
