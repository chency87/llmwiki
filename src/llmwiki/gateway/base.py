from abc import ABC, abstractmethod
from typing import Any

class BaseChannel(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def start(self, manager: Any):
        """Starts the channel listener."""
        pass

    @abstractmethod
    async def send_message(self, chat_id: str, text: str):
        """Sends a message back to the platform."""
        pass
