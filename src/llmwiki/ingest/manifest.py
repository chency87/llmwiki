import hashlib
from llmwiki.db.store import Store

class Manifest:
    def __init__(self, vault_path: str = "vault"):
        self.store = Store(vault_path)

    def get_file_hash(self, file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def try_acquire_for_processing(self, filename: str, file_hash: str) -> bool:
        """
        Attempts to lock the file for processing.
        Returns True if the lock is acquired, False otherwise.
        """
        return self.store.try_acquire_lock(filename, file_hash)

    def mark_processed(self, filename: str, file_hash: str):
        self.store.mark_processed(filename, file_hash)

    def mark_error(self, filename: str, file_hash: str):
        self.store.mark_error(filename, file_hash)

    def is_processed(self, filename: str, file_hash: str) -> bool:
        return self.store.is_processed(filename, file_hash)
