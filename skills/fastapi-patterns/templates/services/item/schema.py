"""Pydantic/dataclass domain models this service owns (not HTTP models)."""

from pydantic import BaseModel


class Item(BaseModel):
    id: int
    name: str
    description: str | None = None
