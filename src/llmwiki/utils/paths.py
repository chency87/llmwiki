import os
from pathlib import Path

def safe_join(base: str, *paths: str) -> str:
    """
    Safely joins paths and ensures the result is under the base directory.
    Prevents path traversal attacks.
    """
    base_path = Path(base).resolve()
    # Handle the case where the first path in *paths might be absolute
    joined = base_path.joinpath(*paths).resolve()
    
    if not str(joined).startswith(str(base_path)):
        raise ValueError(f"Security error: Path traversal attempt detected: {joined}")
    
    return str(joined)

def sanitize_filename(filename: str) -> str:
    """
    Removes potentially dangerous characters from a filename.
    """
    import re
    # Remove any path separators
    name = os.path.basename(filename)
    # Replace non-alphanumeric (except . - _) with underscore
    return re.sub(r'[^a-zA-Z0-9.\-_]', '_', name)
