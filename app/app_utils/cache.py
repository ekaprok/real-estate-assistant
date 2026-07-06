import os
import sqlite3
import hashlib
import json
import logging
import functools

# Configure local logger
logger = logging.getLogger(__name__)

CACHE_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cache.db")

def init_cache_db():
    try:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error initializing SQLite cache DB: {e}")

def get_cached_response(cache_key: str) -> dict | None:
    try:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            # Delete entries older than 90 days (7776000 seconds)
            cursor.execute(
                "DELETE FROM api_cache WHERE strftime('%s', 'now') - strftime('%s', timestamp) > 7776000"
            )
            conn.commit()

            cursor.execute("SELECT response_json FROM api_cache WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
    except sqlite3.Error as e:
        logger.error(f"SQLite error retrieving cache for key {cache_key}: {e}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error parsing cache for key {cache_key}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving cache for key {cache_key}: {e}")
    return None

def set_cached_response(cache_key: str, response: dict):
    try:
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO api_cache (cache_key, response_json, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (cache_key, json.dumps(response))
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.error(f"SQLite error saving cache for key {cache_key}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving cache for key {cache_key}: {e}")

def with_cache(prefix: str):
    """Decorator to automatically check and set cache for a function.
    Generates cache keys that are 100% backward compatible with the legacy formats.

    Args:
        prefix: A string prefix to differentiate cache entries (e.g. 'geocode', 'mashvisor', 'search', 'fetch')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Compute cache key from arguments to match legacy format
            if prefix in ("geocode", "search", "fetch") and args:
                val = args[0].lower()
            elif prefix == "mashvisor" and len(args) >= 2:
                val = f"{args[0]}_{args[1]}".lower()
            else:
                args_repr = f"{args}_{sorted(kwargs.items())}"
                val = args_repr.lower()

            args_hash = hashlib.md5(val.encode("utf-8")).hexdigest()
            cache_key = f"{prefix}_{args_hash}"

            cached = get_cached_response(cache_key)
            if cached is not None:
                logger.info(f"Cache hit for key {cache_key} (func: {func.__name__})")
                return cached

            logger.info(f"Cache miss for key {cache_key} (func: {func.__name__})")
            result = func(*args, **kwargs)

            # Save to cache if result is valid and not empty/None
            if result is not None:
                set_cached_response(cache_key, result)
            return result
        return wrapper
    return decorator
