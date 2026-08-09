"""Common adapter interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AdapterError(RuntimeError):
    pass


class SwitchAdapter(ABC):
    @abstractmethod
    async def read_state(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def set_switch(self, on: bool) -> dict[str, Any]:
        raise NotImplementedError
