"""Builder pattern: always a @classmethod, never an instance method.

Usage — never instantiate the builder:
    poster = await TransactionPosterBuilder.build(config)
"""

from configs import AppConfig

from .component import TransactionPoster
from .schema import TransactionPosterConfig


class TransactionPosterBuilder:
    @classmethod
    async def build(cls, config: AppConfig) -> TransactionPoster:
        return TransactionPoster(TransactionPosterConfig(endpoint=config.transaction_endpoint))
