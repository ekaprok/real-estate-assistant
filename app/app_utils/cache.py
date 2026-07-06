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
            # Only return entries younger than 90 days (7776000 seconds)
            # Avoid DELETE on read to prevent SQLite write locks
            cursor.execute("""
                SELECT response_json
                FROM api_cache
                WHERE cache_key = ?
                  AND strftime('%s', 'now') - strftime('%s', timestamp) <= 7776000
            """, (cache_key,))

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

def set_cached_response(cache_key: str, response):
    try:
        from pydantic import BaseModel
        if isinstance(response, BaseModel):
            if hasattr(response, "model_dump"):
                response_data = response.model_dump()
            else:
                response_data = response.dict()
        else:
            response_data = response

        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO api_cache (cache_key, response_json, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (cache_key, json.dumps(response_data))
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
    import inspect
    def decorator(func):
        def get_cache_key_and_hit(*args, **kwargs):
            # Compute cache key from arguments to match legacy format
            if prefix in ("geocode", "search", "fetch", "parse") and args:
                val = args[0].lower()
            elif prefix in ("mashvisor", "macro") and len(args) >= 2:
                val = f"{args[0]}_{args[1]}".lower()
            elif prefix == "agent_run" and len(args) >= 2:
                val = args[1].lower()
            else:
                args_repr = f"{args}_{sorted(kwargs.items())}"
                val = args_repr.lower()

            args_hash = hashlib.md5(val.encode("utf-8")).hexdigest()

            # Check if mock mode is active to prevent cache pollution
            use_mock = False
            if os.environ.get("USE_MOCK_APIS", "False").lower() == "true":
                use_mock = True
            else:
                import sys
                module = sys.modules.get(func.__module__)
                if module and getattr(module, "USE_MOCK_APIS", False):
                    use_mock = True

            if use_mock:
                return None, None, False

            cache_key = f"{prefix}_{args_hash}"

            cached = get_cached_response(cache_key)
            if cached is not None:
                logger.info(f"Cache hit for key {cache_key} (func: {func.__name__})")

                # Check if return type is Pydantic model
                import typing
                from pydantic import BaseModel
                try:
                    hints = typing.get_type_hints(func)
                    return_type = hints.get('return')
                except Exception:
                    return_type = func.__annotations__.get('return')

                if return_type and inspect.isclass(return_type) and issubclass(return_type, BaseModel):
                    if hasattr(return_type, "model_validate"):
                        return cache_key, return_type.model_validate(cached), True
                    else:
                        return cache_key, return_type.parse_obj(cached), True
                return cache_key, cached, True
            return cache_key, None, False

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                cache_key, cached_val, is_hit = get_cache_key_and_hit(*args, **kwargs)
                if is_hit:
                    return cached_val

                logger.info(f"Cache miss for key {cache_key} (func: {func.__name__})")
                result = await func(*args, **kwargs)

                # Save to cache if result is valid and not empty/None and not in mock mode
                if result is not None and cache_key is not None:
                    set_cached_response(cache_key, result)
                return result
        else:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                cache_key, cached_val, is_hit = get_cache_key_and_hit(*args, **kwargs)
                if is_hit:
                    return cached_val

                logger.info(f"Cache miss for key {cache_key} (func: {func.__name__})")
                result = func(*args, **kwargs)

                # Save to cache if result is valid and not empty/None and not in mock mode
                if result is not None and cache_key is not None:
                    set_cached_response(cache_key, result)
                return result
        return wrapper
    return decorator
