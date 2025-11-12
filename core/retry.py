import time
import random
import functools
from typing import Callable, Type, Tuple, Optional

def retry_with_backoff(
    retries: int = 3,
    backoff_in_seconds: int = 1,
    max_backoff: int = 60,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    logger: Optional[Callable] = None
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        retries: Number of times to retry before giving up
        backoff_in_seconds: Initial delay between retries in seconds
        max_backoff: Maximum backoff time in seconds
        exceptions: Tuple of exceptions to catch and retry on
        logger: Optional logger function (e.g., logging.getLogger(__name__).warning)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            delay = backoff_in_seconds
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retry_count += 1
                    
                    if retry_count > retries:
                        if logger:
                            logger(f"Max retries ({retries}) exceeded. Last error: {str(e)}")
                        raise
                    
                    # Calculate backoff with jitter
                    jitter = random.uniform(0, 0.1 * delay)
                    sleep_time = min(delay + jitter, max_backoff)
                    
                    if logger:
                        logger(
                            f"Retry {retry_count}/{retries} in {sleep_time:.2f}s "
                            f"after error: {str(e)}"
                        )
                    
                    time.sleep(sleep_time)
                    
                    # Exponential backoff
                    delay *= 2
        
        return wrapper
    return decorator
