"""startops/setup_<name>.py — async setup step, called inside lifespan().

Naming: set_*.py = synchronous step, setup_*.py = async step.
Startup order is strict — each step may depend on the previous one.
"""

from services.item import ItemService, set_item_service


async def setup_item_service() -> None:
    set_item_service(ItemService())
