"""Workout: a stream with one AI-written workout per day, so there's nothing to plan.

Every day the app writes that day's workout (30-40 minutes, strength and mobility, no
cardio) as an Item in the "Workout" stream. Yesterday's workout, if it wasn't done, is
archived and counted as skipped. Gemini sees recent workouts, the reps and weights
logged for each set, and the notes written on them (e.g. "lower back felt tight"), so it
rotates muscle groups, progresses from real numbers and backs off when something hurts. It progresses from calisthenics to dumbbells to the barbell as
workouts get completed.

The stream description holds the trainee profile (injuries, equipment) and is passed
to Gemini as-is, so editing it on the Streams page changes future workouts.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.item import Item, ItemEffort, ItemImportance, ItemStatus, ItemType
from app.models.stream import Stream, StreamCategory, StreamType
from app.services.item_queue import next_queue_position

logger = logging.getLogger(__name__)

STREAM_NAME = "Workout"
DEFAULT_PROFILE = (
    "Daily 30-40 minute strength workout. Back injury and several other injuries, so every "
    "exercise has to be mindful and joint-friendly (list specific injuries here to tailor it). "
    "No cardio: gets that from walking the dogs. Equipment: 300 lb barbell plate set, squat rack, "
    "and 2 dumbbell handles that share the plates with the barbell. Started with calisthenics."
)

_TITLE_RE = re.compile(r"^Workout (\d+):")
_FALLBACK_PREFIX = "Today's workout could not be written"
_CHECK_EVERY_SECONDS = 15 * 60
_lock = threading.Lock()

_PHASES = (
    (20, "Phase 1, calisthenics: bodyweight exercises only, with easier and harder versions. Priorities "
     "are learning to brace and keep a neutral spine, core stability (the McGill big 3: curl-up, side "
     "plank, bird dog), glute and hip strength, and mobility."),
    (50, "Phase 2, adding dumbbells: keep the bodyweight base and add light dumbbell work (rows, presses, "
     "goblet squats, split squats, carries). Choose loads that leave 3 or more reps in reserve."),
    (None, "Phase 3, adding the barbell: keep dumbbell and bodyweight work, and add barbell lifts in the "
     "rack with the safety pins set, using back-friendly versions (e.g. box squat to the pins, floor "
     "press, rack pulls from the pins, light Romanian deadlifts, rows). Progress load slowly and "
     "conservatively; technique over weight, always 2 or more reps in reserve."),
)


def _phase(completed: int) -> str:
    for limit, text in _PHASES:
        if limit is None or completed < limit:
            return text
    return _PHASES[-1][1]


def _local_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    if value.tzinfo is None:  # SQLite stores UTC without an offset
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone().date()


def get_or_create_stream(db: Session) -> Stream:
    stream = db.query(Stream).filter(Stream.name == STREAM_NAME).order_by(Stream.id).first()
    if stream:
        return stream
    stream = Stream(
        name=STREAM_NAME,
        description=DEFAULT_PROFILE,
        category=StreamCategory.everyday,
        type=StreamType.long_term,
        priority_weight=1.0,
    )
    db.add(stream)
    db.flush()
    return stream


def is_workout_stream(db: Session, stream_id: int) -> bool:
    stream = db.get(Stream, stream_id)
    return bool(stream and stream.name == STREAM_NAME)


def _num(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _format_log(log: list[dict]) -> str:
    """e.g. "Goblet squat: 10, 10, 8 @ 25 lb; Side plank: 30, 30 (bodyweight)"."""
    parts = []
    for entry in log:
        sets = [s for s in entry.get("sets") or [] if s.get("reps") is not None or s.get("weight") is not None]
        if not sets:
            continue
        reps = ", ".join(_num(s["reps"]) if s.get("reps") is not None else "?" for s in sets)
        weights = {_num(s["weight"]) for s in sets if s.get("weight")}
        load = f" @ {'/'.join(sorted(weights))} lb" if weights else " (bodyweight)"
        parts.append(f"{entry.get('exercise', '?')}: {reps}{load}")
    return "; ".join(parts)


def _format_plan(plan: list[dict]) -> str:
    parts = []
    for ex in plan:
        load = f" @ {_num(ex['weight_lb'])} lb" if ex.get("weight_lb") else ""
        parts.append(f"{ex.get('name', '?')} {_num(ex.get('sets', '?'))}x{ex.get('reps', '?')}{load}")
    return "; ".join(parts)


def _history_lines(workouts: list[Item]) -> list[str]:
    lines = []
    recent = sorted(workouts, key=lambda i: i.id)[-10:]
    for index, item in enumerate(recent):
        day = _local_date(item.created_at)
        state = "done" if item.status == ItemStatus.completed else "skipped"
        line = f"- {day:%a %b %d}: {item.title} ({state})" if day else f"- {item.title} ({state})"
        detailed = index >= len(recent) - 6  # full numbers for the last 6 only
        logged = _format_log(item.workout_log or []) if detailed else ""
        if logged:
            line += f". Logged sets (reps or seconds per set): {logged}"
        elif detailed and state == "done" and item.workout_plan:
            line += f". Planned (no log entered): {_format_plan(item.workout_plan)}"
        if item.notes:
            line += f". Their notes: {item.notes.strip()[:400]}"
        lines.append(line)
    return lines


def _clean_plan(raw: object) -> list[dict]:
    plan = []
    for ex in raw if isinstance(raw, list) else []:
        if not isinstance(ex, dict) or not str(ex.get("name", "")).strip():
            continue
        try:
            sets = max(1, min(10, int(ex.get("sets") or 3)))
        except (TypeError, ValueError):
            sets = 3
        weight = ex.get("weight_lb")
        plan.append(
            {
                "name": str(ex["name"]).strip()[:120],
                "sets": sets,
                "reps": str(ex.get("reps") or "").strip()[:30],
                "weight_lb": weight if isinstance(weight, (int, float)) and weight > 0 else None,
            }
        )
    return plan[:12]


def _generate(number: int, profile: str, completed: int, history: list[str], today: date) -> dict | None:
    if not settings.gemini_api_key:
        return None
    system = (
        "You are a careful strength coach and physical therapist writing today's workout for one "
        "trainee who has injuries. Safety comes first: a workout that's a bit too easy is fine, one "
        "that flares up an injury is not."
    )
    prompt = (
        f"Write workout {number} for {today:%A, %B %d}.\n\n"
        f"Trainee profile (their own words): {profile}\n\n"
        f"They have completed {completed} workouts so far. Current stage: {_phase(completed)}\n\n"
        "Recent workouts, oldest first:\n"
        + ("\n".join(history) if history else "- none yet: this is the first one, keep it gentle")
        + "\n\nRules:\n"
        "- 30 to 40 minutes total, including a 5 minute warm-up and a short cool-down.\n"
        "- They train every day, so rotate the emphasis (for example upper-body push, upper-body pull, "
        "legs and hips, core and mobility) and don't hit the same muscles hard on back-to-back days.\n"
        "- No cardio or conditioning, no jumping, no running: they get cardio from walking their dogs.\n"
        "- Back-friendly: neutral spine, brace before every rep, no loaded spinal flexion (no sit-ups, "
        "crunches, good mornings or toe-touches under load), no ballistic or jerky movements, controlled "
        "tempo. Prefer exercises that train the core to resist movement.\n"
        "- If their notes mention pain, soreness or a flare-up, make today gentler and avoid that area.\n"
        "- For every exercise give sets, reps (or seconds), rest, one short form cue, and an easier "
        "option for a bad day.\n"
        "- If weights are used: the barbell and the 2 dumbbell handles share one plate set, so pick "
        "loads that don't need constant plate swapping, say the total weight per dumbbell or bar, and "
        "say to start lighter than they think.\n"
        "- Stop any exercise that causes sharp, pinching or radiating pain (normal muscle effort is ok).\n"
        "- Progress from the logged numbers: keep a core set of exercises coming back each week so "
        "progress is measurable. When they hit every target rep at a load and their notes are fine, add "
        "1-2 reps, a harder variation, or the smallest weight jump; if they fell short or noted pain, "
        "repeat or reduce. Without logs, progress cautiously.\n\n"
        'Reply with JSON: {"focus": "<2-6 word emphasis, e.g. Pull + core stability>", '
        '"workout": "<the workout as plain text>", '
        '"exercises": [{"name": "<exercise>", "sets": <number>, "reps": "<target, e.g. 8-10 or 30 s>", '
        '"weight_lb": <number per dumbbell or total bar weight, or null for bodyweight>}]} '
        "where exercises lists only the main WORKOUT section exercises (not warm-up or cool-down), "
        "in order, matching the text exactly: weight_lb is the weight written in that exercise's line, "
        "or null when the line names no weight.\n\n"
        "Format of the workout text: short and scannable, like a gym whiteboard. No paragraphs, no intro, "
        "no motivation, no explanations, no markdown symbols like # or *. Sections WARM-UP, WORKOUT, "
        "COOL-DOWN, each name in capitals on its own line, then one line per exercise, for example:\n"
        "WORKOUT\n"
        "1. Goblet squat - 3 x 8-10 @ 25 lb, rest 90 s. Chest up, sit back. Easier: box squat\n"
        "2. Side plank - 3 x 20-30 s per side, rest 45 s. Straight line. Easier: from knees\n"
        "Warm-up and cool-down lines are just the move and the time or reps. End with one line: "
        "Stop if sharp or radiating pain."
    )
    data = _gemini_json(system, prompt)
    if not isinstance(data, dict):
        return None
    focus = str(data.get("focus", "")).strip()[:80]
    text = str(data.get("workout", "")).strip()
    plan = _clean_plan(data.get("exercises"))
    return {"focus": focus or "Full body", "workout": text, "plan": plan or None} if text else None


def _extract_plan(text: str) -> list[dict] | None:
    """Exercise list for a workout written before plans existed."""
    data = _gemini_json(
        "You extract structured data from workout descriptions.",
        "List the main WORKOUT section exercises (not warm-up or cool-down) in this workout, in order. "
        'Reply with JSON: {"exercises": [{"name": "<exercise>", "sets": <number>, '
        '"reps": "<target, e.g. 8-10 or 30 s>", "weight_lb": <number or null>}]}\n\n' + text,
    )
    plan = _clean_plan(data.get("exercises")) if isinstance(data, dict) else []
    return plan or None


def _gemini_json(system: str, prompt: str) -> object | None:
    if not settings.gemini_api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                url,
                params={"key": settings.gemini_api_key},
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.6, "responseMimeType": "application/json"},
                },
            )
            response.raise_for_status()
            payload = response.json()
        parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
        raw = "".join(part.get("text", "") for part in parts).strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        return json.loads(fence.group(1) if fence else raw)
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        logger.warning("Workout Gemini call failed: %s", exc)
        return None


def ensure_todays_workout() -> None:
    """Make sure today's workout exists. Archives an undone earlier one. Safe to call repeatedly."""
    with _lock:
        db = SessionLocal()
        try:
            stream = get_or_create_stream(db)
            today = date.today()
            workouts = [
                item
                for item in db.query(Item).filter(Item.stream_id == stream.id).all()
                if _TITLE_RE.match(item.title)
            ]
            done_statuses = (ItemStatus.completed, ItemStatus.archived)
            todays = [w for w in workouts if _local_date(w.created_at) == today]
            completed = sum(1 for w in workouts if w.status == ItemStatus.completed)
            history = _history_lines([w for w in workouts if w.status in done_statuses])

            if todays:
                # Written while Gemini was unavailable: try again.
                for item in todays:
                    if item.status not in done_statuses and (item.description or "").startswith(_FALLBACK_PREFIX):
                        number = int(_TITLE_RE.match(item.title).group(1))
                        result = _generate(number, stream.description or DEFAULT_PROFILE, completed, history, today)
                        if result:
                            item.title = f"Workout {number}: {result['focus']}"
                            item.description = result["workout"]
                            item.workout_plan = result["plan"]
                    elif item.status not in done_statuses and not item.workout_plan and item.description:
                        item.workout_plan = _extract_plan(item.description)
                db.commit()
                return

            for item in workouts:
                if item.status not in done_statuses:
                    item.status = ItemStatus.archived
                    item.queue_position = next_queue_position(db, stream.id, ItemStatus.archived)
            db.flush()
            history = _history_lines([w for w in workouts if w.status in done_statuses])

            number = max((int(_TITLE_RE.match(w.title).group(1)) for w in workouts), default=0) + 1
            result = _generate(number, stream.description or DEFAULT_PROFILE, completed, history, today)
            plan = None
            if result:
                title, text, plan = f"Workout {number}: {result['focus']}", result["workout"], result["plan"]
            else:
                title = f"Workout {number}: Bodyweight basics"
                text = (
                    f"{_FALLBACK_PREFIX} automatically (Gemini unavailable); the app will retry.\n\n"
                    "Until then, a gentle routine: 5 minutes of easy mobility, then 3 rounds of "
                    "10 bird dogs per side, 20-30 second side planks per side, 10 glute bridges, "
                    "8-10 incline push-ups against a bench or the rack, and 10 bodyweight box squats. "
                    "Stop anything that causes sharp or radiating pain."
                )
            db.add(
                Item(
                    stream_id=stream.id,
                    title=title,
                    description=text,
                    workout_plan=plan,
                    item_type=ItemType.task,
                    status=ItemStatus.next,
                    importance=ItemImportance.high,
                    effort_estimate=ItemEffort.medium,
                    estimated_duration=35,
                    queue_position=next_queue_position(db, stream.id, ItemStatus.next),
                )
            )
            db.commit()
        except Exception:
            logger.exception("Creating today's workout failed")
            db.rollback()
        finally:
            db.close()


def run_daily_loop() -> None:
    """Background thread: check for a new day every 15 minutes."""
    while True:
        ensure_todays_workout()
        time.sleep(_CHECK_EVERY_SECONDS)
