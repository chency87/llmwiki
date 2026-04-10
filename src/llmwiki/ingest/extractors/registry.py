from typing import List, Optional
from .base import BaseExtractor
from .pdf import PDFExtractor
from .text import TextExtractor
from .web import WebExtractor
from .image import ImageExtractor

class ExtractorRegistry:
    def __init__(self):
        self.extractors: List[BaseExtractor] = []
        self._register_defaults()

    def register(self, extractor: BaseExtractor):
        self.extractors.append(extractor)

    def _register_defaults(self):
        # The order matters: specific check before generic ones
        self.register(WebExtractor())
        self.register(PDFExtractor())
        self.register(ImageExtractor())
        self.register(TextExtractor())

    def extract(self, source: str) -> Optional[str]:
        for extractor in self.extractors:
            if extractor.can_handle(source):
                return extractor.extract(source)
        return None

# Singleton for global use
registry = ExtractorRegistry()
