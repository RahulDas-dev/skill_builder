"""Re-exports of dependencies/singletons needed by views.py. No logic here."""

from typing import Annotated

from fastapi import Depends

from ...services.item import ItemService, get_item_service

ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]
