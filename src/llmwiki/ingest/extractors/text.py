from typing import Optional
from .base import BaseExtractor

class TextExtractor(BaseExtractor):
    def can_handle(self, source: str) -> bool:
        extensions = ['.txt', '.md', '.py', '.js', '.json', '.yaml', '.yml', '.toml']
        return any(source.lower().endswith(ext) for ext in extensions)

    def extract(self, source: str) -> Optional[str]:
        try:
            with open(source, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading text file {source}: {str(e)}"
