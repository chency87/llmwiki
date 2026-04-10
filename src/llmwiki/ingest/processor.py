import os
import shutil
import re
import hashlib
from typing import Tuple, Optional
from .manifest import Manifest
from .extractors.registry import registry
from llmwiki.utils.logger import get_logger
from llmwiki.utils.paths import safe_join, sanitize_filename

class Processor:
    def __init__(self, vault_path: str = "vault"):
        self.vault_path = os.path.abspath(vault_path)
        self.raw_path = safe_join(self.vault_path, "raw")
        os.makedirs(self.raw_path, exist_ok=True)
        self.manifest = Manifest(self.vault_path)
        self.logger = get_logger(self.vault_path)

    def process_file(self, source_path: str, skip_extraction: bool = False) -> Tuple[str, Optional[str], bool]:
        """
        Processes a local file or a URL.
        Acquires a state machine lock, moves to vault/raw and optionally extracts text.
        Returns (destination_path, extracted_text, was_processed)
        """
        # Handle URL special case
        if source_path.startswith(('http://', 'https://')):
            return self._process_url(source_path, skip_extraction)

        # Sanitize and resolve source path
        filename = sanitize_filename(os.path.basename(source_path))
        dest_path = safe_join(self.raw_path, filename)

        # Calculate hash from original source
        file_hash = self.manifest.get_file_hash(source_path)

        # Attempt to acquire lock (PENDING/ERROR -> PROCESSING)
        if not self.manifest.try_acquire_for_processing(filename, file_hash):
            self.logger.log("INGEST", "INFO", f"File already processing or processed: {filename}")
            return dest_path, None, False

        # Ensure file exists at the correct sanitized dest_path
        if os.path.abspath(source_path) != os.path.abspath(dest_path):
            self.logger.log("INGEST", "INFO", f"Copying/Renaming {source_path} to {dest_path}")
            shutil.copy2(source_path, dest_path)

        # Extract content using registry if not skipped
        text = None
        if not skip_extraction:
            text = registry.extract(dest_path)
        else:
            self.logger.log("INGEST", "INFO", f"Skipping text extraction for {filename}, model will handle it.")

        return dest_path, text, True

    def _process_url(self, url: str, skip_extraction: bool) -> Tuple[str, Optional[str], bool]:
        # Generate a clean filename from the URL
        clean_name = re.sub(r'[^a-z0-9]+', '-', url.lower()).strip('-')
        if len(clean_name) > 100:
            clean_name = clean_name[:100]
        filename = f"web-{clean_name}.txt"
        dest_path = safe_join(self.raw_path, filename)

        # Extract content using registry
        text = registry.extract(url)
        if not text:
            self.logger.log("INGEST", "ERROR", f"Failed to extract text from URL: {url}")
            return url, None, False

        file_hash = hashlib.sha256(text.encode()).hexdigest()

        # Attempt to acquire lock
        if not self.manifest.try_acquire_for_processing(filename, file_hash):
            self.logger.log("INGEST", "INFO", f"URL already processing or processed: {url}")
            return dest_path, None, False

        # Save extracted text to vault/raw as a source
        with open(dest_path, 'w', encoding='utf-8') as f:
            f.write(f"Source URL: {url}\n\n{text}")

        return dest_path, text, True

    def mark_as_done(self, dest_path: str):
        filename = os.path.basename(dest_path)
        file_hash = self.manifest.get_file_hash(dest_path)
        self.manifest.mark_processed(filename, file_hash)
        self.logger.log("INGEST", "INFO", f"Successfully marked as done: {filename}")

    def mark_as_failed(self, dest_path: str):
        filename = os.path.basename(dest_path)
        file_hash = self.manifest.get_file_hash(dest_path)
        self.manifest.mark_error(filename, file_hash)
        self.logger.log("INGEST", "WARNING", f"Marked as failed: {filename}")
