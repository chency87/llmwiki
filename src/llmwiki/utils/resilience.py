import functools
import time
import random
from typing import Callable

def retry_async(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """
    Decorator for retrying async functions with exponential backoff.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts >= max_attempts:
                        raise e
                    
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** (attempts - 1)) + random.uniform(0, 1), max_delay)
                    time.sleep(delay) # Use sleep for simplicity or asyncio.sleep
            return await func(*args, **kwargs)
        return wrapper
    return decorator
