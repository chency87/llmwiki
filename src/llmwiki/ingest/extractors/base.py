from abc import ABC, abstractmethod
from typing import Optional

class BaseExtractor(ABC):
    @abstractmethod
    def can_handle(self, source: str) -> bool:
        """Returns True if this plugin can handle the source (file path or URL)."""
        pass

    @abstractmethod
    def extract(self, source: str) -> Optional[str]:
        """Extracts text content from the source."""
        pass
