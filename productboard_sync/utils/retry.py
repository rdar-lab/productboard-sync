import functools
import logging
import time

logger = logging.getLogger(__name__)


def retry_on_rate_limit(max_retries: int = 5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                response = func(*args, **kwargs)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        raw = response.headers.get("Retry-After")
                        try:
                            wait = int(raw) if raw is not None else 2 ** attempt
                        except (ValueError, TypeError):
                            wait = 2 ** attempt
                        logger.debug(
                            "Rate limited (429). Attempt %d/%d. Sleeping %ds.",
                            attempt + 1,
                            max_retries,
                            wait,
                        )
                        time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            raise RuntimeError(f"Rate limit retries exhausted after {max_retries} attempts")

        return wrapper

    return decorator
