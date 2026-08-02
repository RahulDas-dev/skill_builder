"""APIRouter + route handler functions for the `items` domain.

One HTTP operation per function. Router-level prefix/tags/dependencies
go on the APIRouter itself, not on include_router() calls.
"""


from fastapi import APIRouter

from .models import ItemCreateRequest, ItemResponse
from .runner import ItemServiceDep

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
async def list_items(service: ItemServiceDep) -> list[ItemResponse]:
    return await service.list_items()


@router.get("/{item_id}")
async def get_item(item_id: int, service: ItemServiceDep) -> ItemResponse:
    return await service.get_item(item_id)


@router.post("/")
async def create_item(item: ItemCreateRequest, service: ItemServiceDep) -> ItemResponse:
    return await service.create_item(item)
