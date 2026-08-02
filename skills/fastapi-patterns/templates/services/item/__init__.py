"""Item service: in-memory CRUD singleton, wired up in startops/setup_*.py."""

from .main import ItemService, get_item_service, set_item_service
from .schema import Item

__all__ = ("Item", "ItemService", "get_item_service", "set_item_service")
