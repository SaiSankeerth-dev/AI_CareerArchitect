from abc import ABC, abstractmethod
from typing import TypedDict


class CollectedData(TypedDict):
    platform: str
    url: str
    text: str
    metadata: dict
    items: list[dict]


class CollectorError(Exception):
    pass


class BaseCollector(ABC):
    platform: str = "generic"

    @abstractmethod
    async def collect(self, url_or_path: str) -> CollectedData:
        """Collect public professional data. Read-only; never mutates accounts."""
