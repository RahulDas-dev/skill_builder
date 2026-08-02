"""Pydantic models this component produces/consumes."""

from pydantic import BaseModel


class TransactionPosterConfig(BaseModel):
    endpoint: str
    timeout_seconds: float = 10.0
