from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ItemReorderRequest(BaseModel):
    direction: Literal["up", "down"]
