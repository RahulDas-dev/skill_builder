"""Request & Response Pydantic models scoped to this route module only.

Cross-cutting types belong in the top-level `_types.py`, not here.
"""

from pydantic import BaseModel


class ItemCreateRequest(BaseModel):
    name: str
    description: str | None = None


class ItemResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
