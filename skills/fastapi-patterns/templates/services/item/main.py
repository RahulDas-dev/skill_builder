"""Service class + get_*/set_* singleton functions.

set_item_service() is called only from startops/setup_*.py, never from
route handlers. get_item_service() is used everywhere else.
"""

from .schema import Item


class ItemService:
    def __init__(self) -> None:
        self._items: dict[int, Item] = {}

    async def list_items(self) -> list[Item]:
        return list(self._items.values())

    async def get_item(self, item_id: int) -> Item:
        return self._items[item_id]

    async def create_item(self, item: Item) -> Item:
        self._items[item.id] = item
        return item


_item_service: ItemService | None = None


def get_item_service() -> ItemService:
    if _item_service is None:
        raise RuntimeError("ItemService not initialized")
    return _item_service


def set_item_service(service: ItemService) -> None:
    global _item_service  # noqa: PLW0603
    _item_service = service
