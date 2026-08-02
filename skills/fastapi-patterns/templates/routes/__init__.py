"""Aggregates all sub-routers into one api_router. No other logic here.

Rename `items` to your actual route domain(s) and add one
`api_router.include_router(...)` line per domain.
"""

from fastapi.routing import APIRouter

from . import items

api_router = APIRouter()
api_router.include_router(items.router)
