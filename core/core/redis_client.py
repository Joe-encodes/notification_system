import redis

# ... (Redis client initialization code)

def check_and_set_idempotency_key(key: str, expiry_seconds: int = 3600) -> bool:
    """
    Checks if the key exists and sets it if it doesn't.
    Returns True if the request is NEW, False if it's a DUPLICATE.
    """
    if redis_client is None:
        return True  # Assume new if Redis is not available
    
    is_new = redis_client.setnx(f"idempotency:{key}", "processed")

    if is_new:
        redis_client.expire(f"idempotency:{key}", expiry_seconds)
        return True
    else:
        return False
    
