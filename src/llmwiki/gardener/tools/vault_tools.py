import os
from typing import List
from datetime import datetime
from functools import lru_cache
from llmwiki.utils.paths import safe_join

# Global cache for page content to reduce disk I/O
@lru_cache(maxsize=128)
def _cached_read(path: str, mtime: float) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

class VaultTools:
    def __init__(self, vault_path: str = "vault"):
        self.vault_path = os.path.abspath(vault_path)
        self.pages_path = safe_join(self.vault_path, "pages")
        self.raw_path = safe_join(self.vault_path, "raw")
        os.makedirs(self.pages_path, exist_ok=True)
        os.makedirs(self.raw_path, exist_ok=True)

    def read_page(self, page_name: str) -> str:
        """Reads a Markdown file from vault/pages. Uses an LRU cache."""
        if not page_name.endswith(".md"):
            page_name += ".md"
        try:
            path = safe_join(self.pages_path, page_name)
            if os.path.exists(path):
                # Use mtime to invalidate cache if file changes on disk
                mtime = os.path.getmtime(path)
                return _cached_read(path, mtime)
            return f"Page {page_name} not found."
        except ValueError as e:
            return str(e)

    def write_page(self, page_name: str, content: str) -> str:
        """Writes/updates a Markdown file in vault/pages."""
        if not page_name.endswith(".md"):
            page_name += ".md"
        try:
            path = safe_join(self.pages_path, page_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote to {page_name}"
        except ValueError as e:
            return str(e)

    def list_pages(self) -> List[str]:
        """Lists all pages in the wiki."""
        pages = []
        for root, _, files in os.walk(self.pages_path):
            for file in files:
                if file.endswith(".md"):
                    rel_dir = os.path.relpath(root, self.pages_path)
                    if rel_dir == ".":
                        pages.append(file)
                    else:
                        pages.append(os.path.join(rel_dir, file))
        return pages

    def search_vault(self, query: str) -> str:
        """Basic search over vault/pages."""
        results = []
        pages = self.list_pages()
        for page in pages:
            content = self.read_page(page)
            if query.lower() in content.lower():
                results.append(page)
        
        if not results:
            return "No matches found."
        return "Matches found in: " + ", ".join(results)

    def read_pages_batch(self, page_names: List[str]) -> dict:
        """Reads multiple pages at once to reduce turn counts."""
        results = {}
        for name in page_names:
            results[name] = self.read_page(name)
        return results

    def append_log(self, message: str):
        """Appends a timestamped message to vault/pages/log.md."""
        try:
            log_path = safe_join(self.pages_path, "log.md")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(f"- [{now}] {message}\n")
            return "Log updated."
        except ValueError as e:
            return str(e)
