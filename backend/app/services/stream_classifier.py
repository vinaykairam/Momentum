from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.item import Item
from app.models.stream import Stream
from app.schemas.stream_suggestion import StreamSuggestionOption, StreamSuggestionResponse
from app.services.momentum_engine import stream_display_name
from app.services.url_metadata import enrich_content_with_url_context

CONFIDENT_THRESHOLD = 0.78
AMBIGUOUS_MARGIN = 0.12
MAX_OPTIONS = 4


@dataclass
class _StreamContext:
    stream_id: int
    label: str
    name: str
    description: str
    category: str
    type: str
    recent_items: list[str]


def _stream_label(stream: Stream, streams_by_id: dict[int, Stream]) -> str:
    name, parent = stream_display_name(stream, streams_by_id)
    return f"{parent} · {name}" if parent else name


def _build_stream_contexts(db: Session, streams: list[Stream]) -> list[_StreamContext]:
    streams_by_id = {stream.id: stream for stream in streams}
    contexts: list[_StreamContext] = []

    for stream in streams:
        recent = (
            db.query(Item.title)
            .filter(Item.stream_id == stream.id)
            .order_by(Item.created_at.desc())
            .limit(3)
            .all()
        )
        contexts.append(
            _StreamContext(
                stream_id=stream.id,
                label=_stream_label(stream, streams_by_id),
                name=stream.name,
                description=(stream.description or "").strip(),
                category=stream.category.value,
                type=stream.type.value,
                recent_items=[row[0] for row in recent],
            )
        )
    return contexts


def _format_streams_for_prompt(contexts: list[_StreamContext]) -> str:
    blocks: list[str] = []
    for ctx in contexts:
        lines = [
            f"id: {ctx.stream_id}",
            f"label: {ctx.label}",
            f"name: {ctx.name}",
            f"category: {ctx.category}",
            f"type: {ctx.type}",
        ]
        if ctx.description:
            lines.append(f"description: {ctx.description}")
        if ctx.recent_items:
            lines.append(f"recent_items: {', '.join(ctx.recent_items)}")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _heuristic_classify(content: str, contexts: list[_StreamContext]) -> list[StreamSuggestionOption]:
    text = content.lower()
    words = [w for w in re.findall(r"\w+", text) if len(w) > 2]
    scored: list[tuple[float, _StreamContext, str]] = []

    for ctx in contexts:
        haystack = " ".join(
            [ctx.name, ctx.label, ctx.description, *ctx.recent_items]
        ).lower()
        hay_words = set(re.findall(r"\w+", haystack))

        hits = len(set(words) & hay_words)
        hits += sum(1 for word in words if word in haystack)
        hits += sum(1 for word in hay_words if len(word) > 3 and word in text)

        if hits == 0:
            continue
        reason = f"Matched keywords related to {ctx.label}"
        scored.append((min(0.5 + hits * 0.1, 0.9), ctx, reason))

    if not scored:
        return []

    scored.sort(key=lambda row: row[0], reverse=True)
    return [
        StreamSuggestionOption(
            stream_id=ctx.stream_id,
            stream_name=ctx.label,
            confidence=round(score, 2),
            reason=reason,
        )
        for score, ctx, reason in scored[:MAX_OPTIONS]
    ]


def _parse_llm_json(raw: str) -> dict:
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _call_gemini(content: str, contexts: list[_StreamContext]) -> list[StreamSuggestionOption]:
    if not settings.gemini_api_key:
        return []

    valid_ids = {ctx.stream_id for ctx in contexts}
    system = (
        "You classify captured tasks into life streams. "
        "Return JSON only with shape: "
        '{"rankings":[{"stream_id":number,"confidence":0-1,"reason":"short"}]}. '
        "Use only stream ids from the catalog. Prefer sub-streams over parents when both fit. "
        "Order rankings by confidence descending."
    )
    user = f"Streams catalog:\n\n{_format_streams_for_prompt(contexts)}\n\nCapture:\n{content.strip()}"
    model = settings.gemini_model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            url,
            params={"key": settings.gemini_api_key},
            headers={"Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "temperature": 0.2,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        payload = response.json()

    candidates = payload.get("candidates") or []
    if not candidates:
        return []
    parts = candidates[0].get("content", {}).get("parts") or []
    if not parts:
        return []
    message = parts[0].get("text", "")
    parsed = _parse_llm_json(message)
    rankings = parsed.get("rankings", [])
    options: list[StreamSuggestionOption] = []
    labels = {ctx.stream_id: ctx.label for ctx in contexts}

    for row in rankings:
        stream_id = int(row["stream_id"])
        if stream_id not in valid_ids:
            continue
        confidence = float(row.get("confidence", 0))
        reason = str(row.get("reason", "")).strip() or "Best match for this capture"
        options.append(
            StreamSuggestionOption(
                stream_id=stream_id,
                stream_name=labels[stream_id],
                confidence=round(max(0.0, min(confidence, 1.0)), 2),
                reason=reason,
            )
        )
        if len(options) >= MAX_OPTIONS:
            break
    return options


def _build_response(options: list[StreamSuggestionOption], reasoning: str) -> StreamSuggestionResponse:
    if not options:
        return StreamSuggestionResponse(
            status="unavailable",
            reasoning=reasoning or "Could not suggest a stream. Pick one manually.",
        )

    top = options[0]
    second_conf = options[1].confidence if len(options) > 1 else 0.0
    ambiguous = top.confidence < CONFIDENT_THRESHOLD or (second_conf and top.confidence - second_conf < AMBIGUOUS_MARGIN)

    if ambiguous:
        return StreamSuggestionResponse(
            status="ambiguous",
            recommended=top,
            options=options,
            reasoning=reasoning or top.reason,
        )

    return StreamSuggestionResponse(
        status="confident",
        recommended=top,
        options=[top],
        reasoning=reasoning or top.reason,
    )


def suggest_stream_for_capture(content: str, db: Session) -> StreamSuggestionResponse:
    streams = db.query(Stream).filter(Stream.active.is_(True)).order_by(Stream.name).all()
    if not streams:
        return StreamSuggestionResponse(
            status="unavailable",
            reasoning="Add a stream before capturing items.",
        )

    if len(streams) == 1:
        ctx = _build_stream_contexts(db, streams)[0]
        only = StreamSuggestionOption(
            stream_id=ctx.stream_id,
            stream_name=ctx.label,
            confidence=1.0,
            reason="Only active stream",
        )
        return StreamSuggestionResponse(
            status="confident",
            recommended=only,
            options=[only],
            reasoning=only.reason,
        )

    contexts = _build_stream_contexts(db, streams)
    classification_content, _, _ = enrich_content_with_url_context(content)
    options: list[StreamSuggestionOption] = []

    gemini_failure: str | None = None
    if settings.gemini_api_key:
        try:
            options = _call_gemini(classification_content, contexts)
        except httpx.HTTPStatusError as exc:
            gemini_failure = exc.response.text[:200] if exc.response is not None else str(exc)
            options = []
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            gemini_failure = str(exc)
            options = []

    if not options:
        options = _heuristic_classify(classification_content, contexts)
        if options:
            reasoning = ""
        elif not settings.gemini_api_key:
            reasoning = "Keyword match (set GEMINI_API_KEY for smarter suggestions)."
        elif gemini_failure and "no longer available" in gemini_failure.lower():
            reasoning = (
                f"Model {settings.gemini_model!r} is retired for your API key. "
                "Set GEMINI_MODEL=gemini-3.5-flash in backend/.env and restart."
            )
        else:
            reasoning = "AI suggestion failed; using keyword match."
        return _build_response(options, reasoning)

    return _build_response(options, options[0].reason if options else "")
