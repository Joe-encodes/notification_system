import time
from functools import wraps


class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = 'CLOSED'  # CLOSED, OPEN, or HALF-OPEN
        self.failure_count = 0
        self.last_failure_time = 0

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()

            # Check if circuit is open and timeout has passed
            if self.state == 'OPEN':
                if current_time - self.last_failure_time > self.recovery_timeout:
                    self.state = 'HALF-OPEN'
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = func(*args, **kwargs)

                # If we're in HALF-OPEN state and the call succeeded, reset the circuit
                if self.state == 'HALF-OPEN':
                    self.reset()
                return result

            except Exception:
                self.failure_count += 1
                self.last_failure_time = current_time

                # Check if we should trip the circuit
                if (self.failure_count >= self.failure_threshold and self.state != 'OPEN'):
                    self.state = 'OPEN'
                    self.last_failure_time = current_time

                # If in HALF-OPEN state and we got an error, trip the circuit
                elif self.state == 'HALF-OPEN':
                    self.state = 'OPEN'

                raise

        return wrapper

    def reset(self):
        """Reset the circuit breaker to its initial state"""
        self.state = 'CLOSED'
        self.failure_count = 0
        self.last_failure_time = 0


def circuit_breaker(failure_threshold=5, recovery_timeout=60):
    """Decorator that applies circuit breaker pattern to a function"""

    def decorator(func):
        cb = CircuitBreaker(failure_threshold, recovery_timeout)
        return cb(func)

    return decorator
