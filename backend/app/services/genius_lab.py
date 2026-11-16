"""Lab: a stream that teaches math and physics one lesson at a time.

Each subject follows a fixed roadmap. Lessons alternate between subjects: finish a
math lesson and the next one is physics, and vice versa. Each lesson is an Item in
the "Lab" stream, written by Gemini when it is reached.
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

STREAM_NAME = "Lab"
LEGACY_STREAM_NAMES = ("Genius Lab", "Math Me Genius")
# Lab lives inside Learn when that stream exists.
PARENT_STREAM_NAME = "Learn"
STREAM_DESCRIPTION = "Math and physics from the very basics to genius level, alternating one lesson at a time"

MATH_ROADMAP: list[str] = [
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

PHYSICS_ROADMAP: list[str] = [
    # Foundations and motion
    "What physics is: measurement, units and the scientific method",
    "Scientific notation and orders of magnitude",
    "Motion: distance, displacement and speed",
    "Velocity and acceleration",
    "Free fall and gravity",
    "Vectors: adding forces and velocities",
    "Projectile motion",
    # Forces
    "Newton's first law: inertia",
    "Newton's second law: F = ma",
    "Newton's third law: action and reaction",
    "Friction",
    "Circular motion",
    "Universal gravitation and orbits",
    # Energy and momentum
    "Work and energy",
    "Kinetic and potential energy",
    "Conservation of energy",
    "Power",
    "Momentum and collisions",
    "Torque and levers",
    "Simple machines",
    # Matter, heat and waves
    "Pressure and fluids",
    "Buoyancy",
    "Temperature and heat",
    "The laws of thermodynamics",
    "Entropy",
    "Oscillations and simple harmonic motion",
    "Waves",
    "Sound",
    "Light and reflection",
    "Refraction and lenses",
    # Electricity and magnetism
    "Electric charge and Coulomb's law",
    "Electric fields",
    "Voltage, current and resistance",
    "Electric circuits",
    "Magnetism",
    "Electromagnetic induction",
    "Maxwell's equations and electromagnetic waves",
    # Modern physics
    "Special relativity: time dilation and length contraction",
    "Mass-energy equivalence: E = mc^2",
    "Inside the atom",
    "Photons and the photoelectric effect",
    "Wave-particle duality",
    "The uncertainty principle",
    "Nuclear physics and radioactivity",
    "General relativity: gravity as curved spacetime",
    "Particle physics and the Standard Model",
    "Cosmology: the Big Bang and the expanding universe",
]

SUBJECTS: dict[str, list[str]] = {"Math": MATH_ROADMAP, "Physics": PHYSICS_ROADMAP}
_OTHER = {"Math": "Physics", "Physics": "Math"}

_STORY_EXAMPLES = {
    "Math": "Napier and logarithms, Pythagoras, Fibonacci, Pascal and Fermat on probability, "
    "Newton and Leibniz on calculus",
    "Physics": "Galileo and falling bodies, Newton and gravity, Faraday and induction, "
    "Einstein and relativity, Marie Curie and radioactivity",
}

# Titles look like "Math 4: Division and remainders". Old "Lesson N:" titles are math.
_TITLE_RE = re.compile(r"^(Lesson|Math|Physics) (\d+):")
_FALLBACK_PREFIX = "Today's topic:"
_lock = threading.Lock()


def _parse_title(title: str) -> tuple[str, int] | None:
    match = _TITLE_RE.match(title)
    if not match:
        return None
    subject = "Math" if match.group(1) == "Lesson" else match.group(1)
    return subject, int(match.group(2))


def get_or_create_stream(db: Session) -> Stream:
    stream = db.query(Stream).filter(Stream.name == STREAM_NAME).order_by(Stream.id).first()
    if stream:
        return stream
    stream = db.query(Stream).filter(Stream.name.in_(LEGACY_STREAM_NAMES)).order_by(Stream.id).first()
    if stream:
        stream.name = STREAM_NAME
        stream.description = STREAM_DESCRIPTION
        db.flush()
        return stream
    parent = (
        db.query(Stream).filter(Stream.name == PARENT_STREAM_NAME, Stream.parent_id.is_(None)).first()
    )
    stream = Stream(
        name=STREAM_NAME,
        parent_id=parent.id if parent else None,
        description=STREAM_DESCRIPTION,
        category=StreamCategory.everyday,
        type=StreamType.long_term,
        priority_weight=1.0,
    )
    db.add(stream)
    db.flush()
    return stream


def _generate_lesson_text(subject: str, number: int, math_done: int) -> str | None:
    if not settings.gemini_api_key:
        return None

    roadmap = SUBJECTS[subject]
    topic = roadmap[number - 1]
    previous = roadmap[max(0, number - 4) : number - 1]
    if subject == "Math":
        course = "basic arithmetic to advanced mathematics"
        math_note = ""
    else:
        course = "everyday intuition to modern physics"
        known = MATH_ROADMAP[:math_done]
        math_note = (
            "The learner is studying math alongside this course and has so far covered: "
            + (", ".join(known) if known else "nothing yet")
            + ". Only use math they have covered; if the topic needs more, explain it in "
            "words and intuition, or introduce the bit of math needed very gently.\n"
        )

    prompt = (
        f"Write {subject} lesson {number} of {len(roadmap)} in a course that takes an adult learner "
        f"from {course}. Today's topic: {topic}.\n"
        + (f"Recent {subject.lower()} lessons covered: {', '.join(previous)}.\n" if previous else "")
        + math_note
        + "\nStructure the lesson with these sections, in plain text (no markdown symbols like # or *), "
        "each starting with its name in capitals on its own line:\n"
        "THE STORY - include this section ONLY if the topic has a well-documented history involving "
        f"real, named people or specific historical events (for example {_STORY_EXAMPLES[subject]}). "
        "If it does, tell it in an engaging way: who, when and where, the real problem they were "
        "stuck on, why the old way was painful, and how this idea changed things. Every person, "
        "date and event must be historically factual. Never invent or imagine characters, names, "
        "scenes, quotes or dialogue, and don't write 'imagine' or 'picture' scenarios. If the topic "
        "has no such documented story, leave this section out entirely and start with THE IDEA.\n"
        "THE IDEA - explain the concept simply and intuitively (as the answer to the problem in "
        "the story, if there is one), building on earlier lessons.\n"
        "WORKED EXAMPLE - one example solved step by step.\n"
        "REAL WORLD - 2 or 3 concrete, practical situations where this is actually used "
        "(money, cooking, building, games, sports, cars, phones, space and so on), with numbers.\n"
        "PRACTICE - exactly 2 practice questions, at least one set in a real-world scenario.\n"
        "ANSWERS - the answers to the 2 practice questions with a one-line explanation each.\n"
        "\nKeep it focused: around 500 to 700 words with a story, or 300 to 450 without one."
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
        logger.warning("Genius Lab lesson generation failed: %s", exc)
        return None


def _fallback_text(topic: str) -> str:
    return (
        f"{_FALLBACK_PREFIX} {topic}.\n\n"
        "This lesson could not be written automatically (set GEMINI_API_KEY in backend/.env). "
        "Study this topic from any source, then mark it done to unlock the next one."
    )


def _next_subject(lessons: list[tuple[Item, str, int]], last_numbers: dict[str, int]) -> str | None:
    """Alternate subjects after each lesson; fall back to whichever subject still has topics."""
    latest = max(lessons, key=lambda row: row[0].id)[1] if lessons else "Physics"
    for subject in (_OTHER[latest], latest):
        if last_numbers[subject] < len(SUBJECTS[subject]):
            return subject
    return None


def queue_next_lesson() -> None:
    """Create the next lesson item if the stream has no unfinished lesson. Safe to call repeatedly."""
    with _lock:
        db = SessionLocal()
        try:
            stream = get_or_create_stream(db)
            items = db.query(Item).filter(Item.stream_id == stream.id).all()
            lessons = [(item, *parsed) for item in items if (parsed := _parse_title(item.title))]
            last_numbers = {subject: 0 for subject in SUBJECTS}
            for _, subject, number in lessons:
                last_numbers[subject] = max(last_numbers[subject], number)
            math_done = sum(
                1 for item, subject, _ in lessons if subject == "Math" and item.status == ItemStatus.completed
            )

            pending = [row for row in lessons if row[0].status in (ItemStatus.next, ItemStatus.active, ItemStatus.backlog)]
            if pending:
                # A lesson queued before GEMINI_API_KEY was set gets written properly now.
                for item, subject, number in pending:
                    if number <= len(SUBJECTS[subject]) and (item.description or "").startswith(_FALLBACK_PREFIX):
                        text = _generate_lesson_text(subject, number, math_done)
                        if text:
                            item.description = text
                db.commit()
                return

            subject = _next_subject(lessons, last_numbers)
            if subject is None:
                db.commit()
                return

            number = last_numbers[subject] + 1
            topic = SUBJECTS[subject][number - 1]
            text = _generate_lesson_text(subject, number, math_done) or _fallback_text(topic)
            db.add(
                Item(
                    stream_id=stream.id,
                    title=f"{subject} {number}: {topic}",
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


def is_genius_lab_stream(db: Session, stream_id: int) -> bool:
    stream = db.get(Stream, stream_id)
    return bool(stream and stream.name == STREAM_NAME)


def lesson_neighbors(db: Session, item: Item) -> dict[str, dict | None]:
    """Previous and next lesson in the same subject as `item`, for browsing back through a subject."""
    parsed = _parse_title(item.title)
    if not parsed or not is_genius_lab_stream(db, item.stream_id):
        return {"previous": None, "next": None}
    subject, number = parsed
    by_number: dict[int, Item] = {}
    for other in db.query(Item).filter(Item.stream_id == item.stream_id).all():
        other_parsed = _parse_title(other.title)
        if other_parsed and other_parsed[0] == subject:
            by_number[other_parsed[1]] = other

    def ref(n: int) -> dict | None:
        found = by_number.get(n)
        return {"id": found.id, "title": found.title} if found else None

    return {"previous": ref(number - 1), "next": ref(number + 1)}
