from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    name: str

    @abstractmethod
    async def health(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def sync(self) -> dict[str, Any]:
        raise NotImplementedError
