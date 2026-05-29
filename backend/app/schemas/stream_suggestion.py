from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StreamSuggestionOption(BaseModel):
    stream_id: int
    stream_name: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class StreamSuggestionRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=8000)


class StreamSuggestionResponse(BaseModel):
    status: Literal["confident", "ambiguous", "unavailable"]
    recommended: StreamSuggestionOption | None = None
    options: list[StreamSuggestionOption] = Field(default_factory=list)
    reasoning: str = ""
