"""Courses: streams that teach a subject one AI-written lesson at a time.

Each course has two tracks that alternate: finish a lesson in one track and the next
lesson comes from the other. Each track follows a fixed roadmap. Lessons are Items in
the course's stream (inside Learn), written by Gemini when they are reached.

- Lab: Math and Physics (physics only uses math already covered).
- Finance: Finance and Trading (trading only builds on finance already covered).
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.item import Item, ItemEffort, ItemImportance, ItemStatus, ItemType
from app.models.stream import Stream, StreamCategory, StreamType
from app.services.item_queue import next_queue_position

logger = logging.getLogger(__name__)

# Courses live inside Learn when that stream exists.
PARENT_STREAM_NAME = "Learn"

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


FINANCE_ROADMAP: list[str] = [
    # Money basics
    "Money, inflation and purchasing power",
    "Simple and compound interest",
    "Time value of money: present and future value",
    "Budgeting, saving and the emergency fund",
    "Debt: credit cards, loans and amortization",
    "Credit scores and the cost of borrowing",
    "Taxes on income and investments",
    "Tax-advantaged retirement accounts",
    # Markets and instruments
    "What a stock is: owning part of a company",
    "How stock exchanges and brokers work",
    "Bonds: coupons, yields and prices",
    "Why bond prices fall when interest rates rise",
    "Mutual funds, index funds and ETFs",
    "Market indexes: S&P 500, Nasdaq, Dow and others",
    "Risk and return",
    "Diversification",
    "Asset allocation",
    "Dollar-cost averaging",
    "Bull and bear markets: a history of crashes and recoveries",
    # Analysing companies
    "Reading an income statement",
    "Reading a balance sheet",
    "Reading a cash flow statement",
    "Financial ratios: P/E, P/B, ROE and margins",
    "Earnings reports and guidance",
    "Dividends and share buybacks",
    "Discounted cash flow (DCF) valuation",
    "Competitive moats and business quality",
    "Value investing vs growth investing",
    # The economy
    "GDP, inflation and the business cycle",
    "Central banks and monetary policy",
    "The yield curve and what it signals",
    "Currencies and exchange rates",
    "Commodities: oil, gold and metals",
    # Portfolio theory
    "Expected return and variance of a portfolio",
    "Modern portfolio theory and the efficient frontier",
    "Beta and the capital asset pricing model (CAPM)",
    "Factor investing: value, size, momentum and quality",
    "The efficient market hypothesis",
    "Behavioral finance: the biases that cost money",
    "Rebalancing and tax-loss harvesting",
    # Advanced
    "Corporate finance: capital structure and WACC",
    "IPOs, mergers and acquisitions",
    "Credit risk and credit ratings",
    "Real estate and REITs",
    "Private equity and venture capital",
    "Hedge funds and their strategies",
    "Financial crises: 1929, 2000 and 2008",
    "Writing your own investment policy",
]

TRADING_ROADMAP: list[str] = [
    # Foundations
    "Trading vs investing, and why most traders lose money",
    "Brokers, accounts and trading costs",
    "Order types: market, limit and stop",
    "Bid, ask, spread and liquidity",
    "Reading a price chart: candlesticks",
    "Volume and what it tells you",
    "Trends, support and resistance",
    "Moving averages",
    "Momentum indicators: RSI and MACD",
    "Volatility and average true range (ATR)",
    "Chart patterns: what holds up and what doesn't",
    # Risk management
    "Position sizing",
    "Stop losses and risk per trade",
    "Risk/reward and expectancy",
    "Drawdowns and risk of ruin",
    "Keeping a trading journal",
    "Trading psychology: fear, greed and revenge trading",
    # Styles and mechanics
    "Day trading, swing trading and position trading",
    "Trading around earnings and news",
    "Short selling",
    "Margin and leverage",
    "Market microstructure: market makers and order flow",
    # Options
    "Options basics: calls and puts",
    "Option pricing: intrinsic value and time value",
    "Implied volatility",
    "The Greeks: delta, gamma, theta and vega",
    "Covered calls and cash-secured puts",
    "Vertical spreads",
    "Straddles, strangles and iron condors",
    "The Black-Scholes model",
    # Other markets
    "Futures contracts",
    "Forex trading basics",
    "Crypto markets and their risks",
    # Systematic trading
    "Statistical edge and the law of large numbers",
    "Backtesting a strategy",
    "Overfitting and data snooping",
    "The Kelly criterion",
    "Trend-following strategies",
    "Mean-reversion strategies",
    "Pairs trading and statistical arbitrage",
    "Algorithmic trading: building a simple bot",
    "Portfolio-level risk management",
    "Writing your own trading plan",
]


@dataclass(frozen=True)
class Track:
    name: str  # also the lesson title prefix, e.g. "Math 4: ..."
    roadmap: list[str]
    course: str  # "takes an adult learner from {course}"
    story_examples: str
    real_world: str


@dataclass(frozen=True)
class Course:
    stream_name: str
    description: str
    tracks: tuple[Track, Track]  # the second track builds on the first
    legacy_stream_names: tuple[str, ...] = ()
    legacy_title_prefixes: tuple[str, ...] = ()  # old prefixes that mean the first track
    extra_rules: str = ""

    def track(self, name: str) -> Track:
        return next(t for t in self.tracks if t.name == name)

    @property
    def title_re(self) -> re.Pattern[str]:
        names = [*self.legacy_title_prefixes, *(t.name for t in self.tracks)]
        return re.compile(r"^(" + "|".join(map(re.escape, names)) + r") (\d+):")


LAB = Course(
    stream_name="Lab",
    description="Math and physics from the very basics to genius level, alternating one lesson at a time",
    legacy_stream_names=("Genius Lab", "Math Me Genius"),
    legacy_title_prefixes=("Lesson",),
    tracks=(
        Track(
            name="Math",
            roadmap=MATH_ROADMAP,
            course="basic arithmetic to advanced mathematics",
            story_examples="Napier and logarithms, Pythagoras, Fibonacci, Pascal and Fermat on probability, "
            "Newton and Leibniz on calculus",
            real_world="(money, cooking, building, games, sports, cars, phones, space and so on), with numbers",
        ),
        Track(
            name="Physics",
            roadmap=PHYSICS_ROADMAP,
            course="everyday intuition to modern physics",
            story_examples="Galileo and falling bodies, Newton and gravity, Faraday and induction, "
            "Einstein and relativity, Marie Curie and radioactivity",
            real_world="(cars, sports, cooking, phones, buildings, space and so on), with numbers",
        ),
    ),
)

FINANCE = Course(
    stream_name="Finance",
    description="Finance, investing and trading from the very basics to expert level, alternating one lesson at a time",
    tracks=(
        Track(
            name="Finance",
            roadmap=FINANCE_ROADMAP,
            course="knowing nothing about money to expert-level finance and investing",
            story_examples="the Dutch East India Company and the first stock exchange, the South Sea Bubble, "
            "Benjamin Graham and Warren Buffett, John Bogle and the first index fund, Paul Volcker and inflation",
            real_world="(real companies, real market events, personal money decisions like a mortgage, "
            "a savings plan or a retirement account), with numbers",
        ),
        Track(
            name="Trading",
            roadmap=TRADING_ROADMAP,
            course="first trade to expert-level trading and risk management",
            story_examples="Jesse Livermore, Richard Dennis and the Turtle Traders, Black, Scholes and Merton, "
            "the 1987 crash, Long-Term Capital Management, the GameStop squeeze",
            real_world="(real stocks, real market events, specific trades worked through with prices, "
            "position sizes and fees), with numbers",
        ),
    ),
    extra_rules="Be honest about risk and about how often traders and stock pickers actually lose money. "
    "This is education: never tell the learner to buy or sell a specific security, and don't promise returns.\n",
)

COURSES: tuple[Course, ...] = (LAB, FINANCE)

_FALLBACK_PREFIX = "Today's topic:"
_lock = threading.Lock()


def _parse_title(course: Course, title: str) -> tuple[str, int] | None:
    match = course.title_re.match(title)
    if not match:
        return None
    track = course.tracks[0].name if match.group(1) in course.legacy_title_prefixes else match.group(1)
    return track, int(match.group(2))


def get_or_create_stream(db: Session, course: Course) -> Stream:
    stream = db.query(Stream).filter(Stream.name == course.stream_name).order_by(Stream.id).first()
    if stream:
        return stream
    if course.legacy_stream_names:
        stream = (
            db.query(Stream).filter(Stream.name.in_(course.legacy_stream_names)).order_by(Stream.id).first()
        )
        if stream:
            stream.name = course.stream_name
            stream.description = course.description
            db.flush()
            return stream
    parent = (
        db.query(Stream).filter(Stream.name == PARENT_STREAM_NAME, Stream.parent_id.is_(None)).first()
    )
    stream = Stream(
        name=course.stream_name,
        parent_id=parent.id if parent else None,
        description=course.description,
        category=StreamCategory.everyday,
        type=StreamType.long_term,
        priority_weight=1.0,
    )
    db.add(stream)
    db.flush()
    return stream


def _generate_lesson_text(course: Course, track_name: str, number: int, base_done: int) -> str | None:
    if not settings.gemini_api_key:
        return None

    track = course.track(track_name)
    roadmap = track.roadmap
    topic = roadmap[number - 1]
    previous = roadmap[max(0, number - 4) : number - 1]
    base = course.tracks[0]
    if track is base:
        base_note = ""
    else:
        known = base.roadmap[:base_done]
        base_note = (
            f"The learner is studying {base.name.lower()} alongside this course and has so far covered: "
            + (", ".join(known) if known else "nothing yet")
            + f". Only rely on {base.name.lower()} they have covered; if the topic needs more, explain "
            "it in words and intuition, or introduce the bit needed very gently.\n"
        )

    prompt = (
        f"Write {track.name} lesson {number} of {len(roadmap)} in a course that takes an adult learner "
        f"from {track.course}. Today's topic: {topic}.\n"
        + (f"Recent {track.name.lower()} lessons covered: {', '.join(previous)}.\n" if previous else "")
        + base_note
        + course.extra_rules
        + "\nStructure the lesson with these sections, in plain text (no markdown symbols like # or *), "
        "each starting with its name in capitals on its own line:\n"
        "THE STORY - include this section ONLY if the topic has a well-documented history involving "
        f"real, named people or specific historical events (for example {track.story_examples}). "
        "If it does, tell it in an engaging way: who, when and where, the real problem they were "
        "stuck on, why the old way was painful, and how this idea changed things. Every person, "
        "date and event must be historically factual. Never invent or imagine characters, names, "
        "scenes, quotes or dialogue, and don't write 'imagine' or 'picture' scenarios. If the topic "
        "has no such documented story, leave this section out entirely and start with THE IDEA.\n"
        "THE IDEA - explain the concept simply and intuitively (as the answer to the problem in "
        "the story, if there is one), building on earlier lessons.\n"
        "WORKED EXAMPLE - one example solved step by step.\n"
        "REAL WORLD - 2 or 3 concrete, practical situations where this is actually used "
        f"{track.real_world}.\n"
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
        logger.warning("%s lesson generation failed: %s", course.stream_name, exc)
        return None


def _fallback_text(topic: str) -> str:
    return (
        f"{_FALLBACK_PREFIX} {topic}.\n\n"
        "This lesson could not be written automatically (set GEMINI_API_KEY in backend/.env). "
        "Study this topic from any source, then mark it done to unlock the next one."
    )


def _next_track(course: Course, lessons: list[tuple[Item, str, int]], last_numbers: dict[str, int]) -> str | None:
    """Alternate tracks after each lesson; fall back to whichever track still has topics."""
    first, second = (t.name for t in course.tracks)
    latest = max(lessons, key=lambda row: row[0].id)[1] if lessons else second
    other = first if latest == second else second
    for name in (other, latest):
        if last_numbers[name] < len(course.track(name).roadmap):
            return name
    return None


def _queue_course(db: Session, course: Course) -> None:
    stream = get_or_create_stream(db, course)
    items = db.query(Item).filter(Item.stream_id == stream.id).all()
    lessons = [(item, *parsed) for item in items if (parsed := _parse_title(course, item.title))]
    last_numbers = {t.name: 0 for t in course.tracks}
    for _, name, number in lessons:
        last_numbers[name] = max(last_numbers[name], number)
    base_name = course.tracks[0].name
    base_done = sum(
        1 for item, name, _ in lessons if name == base_name and item.status == ItemStatus.completed
    )

    pending = [row for row in lessons if row[0].status in (ItemStatus.next, ItemStatus.active, ItemStatus.backlog)]
    if pending:
        # A lesson queued before GEMINI_API_KEY was set gets written properly now.
        for item, name, number in pending:
            if number <= len(course.track(name).roadmap) and (item.description or "").startswith(_FALLBACK_PREFIX):
                text = _generate_lesson_text(course, name, number, base_done)
                if text:
                    item.description = text
        db.commit()
        return

    name = _next_track(course, lessons, last_numbers)
    if name is None:
        db.commit()
        return

    number = last_numbers[name] + 1
    topic = course.track(name).roadmap[number - 1]
    text = _generate_lesson_text(course, name, number, base_done) or _fallback_text(topic)
    db.add(
        Item(
            stream_id=stream.id,
            title=f"{name} {number}: {topic}",
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


def queue_next_lesson() -> None:
    """Give every course a next lesson if it has no unfinished one. Safe to call repeatedly."""
    with _lock:
        for course in COURSES:
            db = SessionLocal()
            try:
                _queue_course(db, course)
            except Exception:
                logger.exception("Queueing the next %s lesson failed", course.stream_name)
                db.rollback()
            finally:
                db.close()


def course_for_stream(db: Session, stream_id: int) -> Course | None:
    stream = db.get(Stream, stream_id)
    if not stream:
        return None
    return next((c for c in COURSES if c.stream_name == stream.name), None)


def is_course_stream(db: Session, stream_id: int) -> bool:
    return course_for_stream(db, stream_id) is not None


def lesson_neighbors(db: Session, item: Item) -> dict[str, dict | None]:
    """Previous and next lesson in the same track as `item`, for browsing back through a track."""
    course = course_for_stream(db, item.stream_id)
    parsed = _parse_title(course, item.title) if course else None
    if not course or not parsed:
        return {"previous": None, "next": None}
    track, number = parsed
    by_number: dict[int, Item] = {}
    for other in db.query(Item).filter(Item.stream_id == item.stream_id).all():
        other_parsed = _parse_title(course, other.title)
        if other_parsed and other_parsed[0] == track:
            by_number[other_parsed[1]] = other

    def ref(n: int) -> dict | None:
        found = by_number.get(n)
        return {"id": found.id, "title": found.title} if found else None

    return {"previous": ref(number - 1), "next": ref(number + 1)}
