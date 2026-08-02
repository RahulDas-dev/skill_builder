"""Component business logic. Extends BaseComponent, implements run_async()."""

from apps.component.base import BaseComponent

from .schema import TransactionPosterConfig


class TransactionPoster(BaseComponent):
    def __init__(self, config: TransactionPosterConfig) -> None:
        self._config = config

    async def run_async(self, payload: dict) -> dict:
        raise NotImplementedError
