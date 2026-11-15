"""Math Me Genius: a stream that teaches math one lesson at a time.

Lessons follow a fixed roadmap. Each lesson is an Item in the "Math Me Genius"
stream, written by Gemini when it is reached. Completing a lesson queues the next.
"""

from __future__ import annotations

import logging
import re
import threading

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.item import Item, ItemEffort, ItemImportance, ItemStatus, ItemType
from app.models.stream import Stream, StreamCategory, StreamType
from app.services.item_queue import next_queue_position

logger = logging.getLogger(__name__)

STREAM_NAME = "Math Me Genius"
STREAM_DESCRIPTION = "Math from the very basics to genius level, one lesson at a time"

ROADMAP: list[str] = [
    # Foundations
    "Counting and place value",
    "Addition and subtraction",
    "Multiplication",
    "Division and remainders",
    "Order of operations",
    "Negative numbers",
    "Factors, multiples and primes",
    "Fractions",
    "Adding and subtracting fractions",
    "Multiplying and dividing fractions",
    "Decimals",
    "Percentages",
    "Ratios and proportions",
    "Exponents and powers",
    "Square roots",
    "Mental math tricks and estimation",
    # Pre-algebra and algebra
    "Variables and expressions",
    "Solving one-step equations",
    "Solving multi-step equations",
    "Inequalities",
    "The coordinate plane",
    "Linear functions and slope",
    "Graphing lines",
    "Systems of linear equations",
    "Polynomials",
    "Factoring polynomials",
    "Quadratic equations",
    "The quadratic formula",
    "Functions and function notation",
    "Exponential growth and decay",
    "Logarithms",
    # Geometry and trigonometry
    "Angles and lines",
    "Triangles",
    "The Pythagorean theorem",
    "Area and perimeter",
    "Circles",
    "Volume and surface area",
    "Similarity and congruence",
    "Right-triangle trigonometry: sine, cosine, tangent",
    "The unit circle",
    "Trigonometric identities",
    # Data and probability
    "Mean, median and mode",
    "Spread: range, variance and standard deviation",
    "Basic probability",
    "Counting: permutations and combinations",
    "Conditional probability and Bayes' rule",
    "Normal distribution",
    # Pre-calculus and calculus
    "Sequences and series",
    "Limits",
    "Derivatives: the idea of instantaneous change",
    "Derivative rules",
    "Applications of derivatives: optimization",
    "Integrals: area under a curve",
    "The fundamental theorem of calculus",
    "Integration techniques",
    "Differential equations",
    # Higher math
    "Vectors",
    "Matrices",
    "Linear transformations",
    "Eigenvalues and eigenvectors",
    "Complex numbers",
    "Logic and proof techniques",
    "Mathematical induction",
    "Sets and functions (rigorous)",
    "Number theory: modular arithmetic",
    "Graph theory",
    "Multivariable calculus: partial derivatives",
    "Real analysis: the epsilon-delta definition of a limit",
    "Abstract algebra: groups",
]

_TITLE_RE = re.compile(r"^Lesson (\d+):")
_lock = threading.Lock()


def _lesson_number(title: str) -> int | None:
    match = _TITLE_RE.match(title)
    return int(match.group(1)) if match else None


def get_or_create_stream(db: Session) -> Stream:
    stream = db.query(Stream).filter(Stream.name == STREAM_NAME, Stream.parent_id.is_(None)).first()
    if stream:
        return stream
    stream = Stream(
        name=STREAM_NAME,
        description=STREAM_DESCRIPTION,
        category=StreamCategory.everyday,
        type=StreamType.long_term,
        priority_weight=1.0,
    )
    db.add(stream)
    db.flush()
    return stream


def _generate_lesson_text(number: int, topic: str) -> str | None:
    if not settings.gemini_api_key:
        return None

    previous = ROADMAP[max(0, number - 4) : number - 1]
    prompt = (
        f"Write lesson {number} of {len(ROADMAP)} in a course that takes an adult learner from "
        f"basic arithmetic to advanced mathematics. Today's topic: {topic}.\n"
        + (f"Recent lessons covered: {', '.join(previous)}.\n" if previous else "")
        + "\nStructure the lesson with these sections, in plain text (no markdown symbols like # or *), "
        "each starting with its name in capitals on its own line:\n"
        "THE STORY - open with the human story behind this idea, told like a gripping short story: "
        "who discovered or developed it, when and where, what real problem they were stuck on "
        "(trade, astronomy, navigation, war, taxes, gambling and so on), why the old way was painful, "
        "and how this idea changed things. For ideas with no single inventor (like counting), tell "
        "the story of the civilizations that shaped it. Stick to well-documented history: no invented "
        "quotes or dialogue, and say 'legend has it' for anything uncertain.\n"
        "THE IDEA - explain the concept simply and intuitively as the answer to the problem in the "
        "story, building on earlier lessons.\n"
        "WORKED EXAMPLE - one example solved step by step.\n"
        "REAL WORLD - 2 or 3 concrete, practical situations where this is actually used "
        "(money, cooking, building, games, science, tech, sports and so on), with numbers.\n"
        "PRACTICE - exactly 2 practice questions, at least one set in a real-world scenario.\n"
        "ANSWERS - the answers to the 2 practice questions with a one-line explanation each.\n"
        "\nKeep it focused: around 500 to 700 words, with the story taking about a third."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                url,
                params={"key": settings.gemini_api_key},
                json={
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.7},
                },
            )
            response.raise_for_status()
            payload = response.json()
        parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        return text or None
    except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
        logger.warning("Math Me Genius lesson generation failed: %s", exc)
        return None


def _fallback_text(topic: str) -> str:
    return (
        f"Today's topic: {topic}.\n\n"
        "This lesson could not be written automatically (set GEMINI_API_KEY in backend/.env). "
        "Study this topic from any source, then mark it done to unlock the next one."
    )


def queue_next_lesson() -> None:
    """Create the next lesson item if the stream has no unfinished lesson. Safe to call repeatedly."""
    with _lock:
        db = SessionLocal()
        try:
            stream = get_or_create_stream(db)
            items = db.query(Item).filter(Item.stream_id == stream.id).all()
            pending = [i for i in items if i.status in (ItemStatus.next, ItemStatus.active, ItemStatus.backlog)]
            if pending:
                # A lesson queued before GEMINI_API_KEY was set gets written properly now.
                for item in pending:
                    number = _lesson_number(item.title)
                    if number and 1 <= number <= len(ROADMAP) and (item.description or "").startswith(
                        "Today's topic:"
                    ):
                        text = _generate_lesson_text(number, ROADMAP[number - 1])
                        if text:
                            item.description = text
                db.commit()
                return

            numbers = [n for n in (_lesson_number(item.title) for item in items) if n is not None]
            number = max(numbers, default=0) + 1
            if number > len(ROADMAP):
                db.commit()
                return

            topic = ROADMAP[number - 1]
            text = _generate_lesson_text(number, topic) or _fallback_text(topic)
            db.add(
                Item(
                    stream_id=stream.id,
                    title=f"Lesson {number}: {topic}",
                    description=text,
                    item_type=ItemType.course,
                    status=ItemStatus.next,
                    importance=ItemImportance.high,
                    effort_estimate=ItemEffort.small,
                    estimated_duration=20,
                    queue_position=next_queue_position(db, stream.id, ItemStatus.next),
                )
            )
            db.commit()
        finally:
            db.close()


def is_math_stream(db: Session, stream_id: int) -> bool:
    stream = db.get(Stream, stream_id)
    return bool(stream and stream.name == STREAM_NAME and stream.parent_id is None)
