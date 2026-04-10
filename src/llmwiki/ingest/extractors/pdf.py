from typing import Optional
from .base import BaseExtractor

class PDFExtractor(BaseExtractor):
    def can_handle(self, source: str) -> bool:
        return source.lower().endswith('.pdf')

    def extract(self, source: str) -> Optional[str]:
        # Lazy load heavy dependency
        try:
            from pdfminer.high_level import extract_text
            return extract_text(source)
        except ImportError:
            return "Error: pdfminer.six not installed. Please install it to process PDFs."
        except Exception as e:
            return f"Error extracting PDF {source}: {str(e)}"
