import httpx
from typing import Optional
from .base import BaseExtractor
from llmwiki.utils.resilience import retry_async

class WebExtractor(BaseExtractor):
    def can_handle(self, source: str) -> bool:
        return source.lower().startswith(('http://', 'https://'))

    @retry_async(max_attempts=3)
    async def extract_async(self, source: str) -> Optional[str]:
        # Lazy load heavy dependency
        try:
            import trafilatura
        except ImportError:
            return "Error: trafilatura not installed. Please install it to process URLs."

        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            response = await client.get(source)
            response.raise_for_status()
            result = trafilatura.extract(response.text)
            return result

    def extract(self, source: str) -> Optional[str]:
        try:
            import asyncio
            return asyncio.run(self.extract_async(source))
        except Exception as e:
            return f"Error fetching URL {source}: {str(e)}"
