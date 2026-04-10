from typing import Optional
from .base import BaseExtractor

class ImageExtractor(BaseExtractor):
    def can_handle(self, source: str) -> bool:
        extensions = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif']
        return any(source.lower().endswith(ext) for ext in extensions)

    def extract(self, source: str) -> Optional[str]:
        # Lazy load heavy dependency
        try:
            from PIL import Image
            with Image.open(source) as img:
                return f"Image file: {source}, Size: {img.size}, Format: {img.format}, Mode: {img.mode}"
        except ImportError:
            return "Error: Pillow not installed. Please install it to process images."
        except Exception as e:
            return f"Error reading image {source}: {str(e)}"
