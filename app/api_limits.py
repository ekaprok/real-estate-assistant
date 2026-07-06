import contextvars
import yaml
import os
import logging

logger = logging.getLogger(__name__)

# Custom exception for API limit violations
class ApiLimitExceededError(Exception):
    def __init__(self, api_name: str, limit: int):
        super().__init__(f"API call limit exceeded for {api_name} (max {limit} allowed). The rate has been met.")
        self.api_name = api_name
        self.limit = limit

# Contextvar to store the request-scoped call counts
api_call_counts = contextvars.ContextVar("api_call_counts", default=None)

# Cache for limit configuration
_limits_cache = None

def load_limits():
    global _limits_cache
    if _limits_cache is not None:
        return _limits_cache

    # Locate api_limits_config.yaml
    # Try specs/ first, fallback to root or parent directories
    config_paths = [
        "specs/api_limits_config.yaml",
        "../specs/api_limits_config.yaml",
        "/Users/ekaterinaprokopeva/Documents/real-estate-assistant/specs/api_limits_config.yaml"
    ]

    config = {}
    for path in config_paths:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
                    config = data.get("api_limits_per_request", {})
                    break
            except Exception:
                pass

    # Defaults in case the file isn't found/readable
    _limits_cache = {
        "google_maps_geocoding": config.get("google_maps_geocoding", {}).get("max_calls", 20),
        "overpass_api": config.get("overpass_api", {}).get("max_calls", 20),
        "serper_dev_search": config.get("serper_dev_search", {}).get("max_calls", 50),
        "mashvisor_api": config.get("mashvisor_api", {}).get("max_calls", 2),
        "llm_gemini_flash": config.get("llm_gemini_flash", {}).get("max_calls", 50),
        "llm_gemini_pro": config.get("llm_gemini_pro", {}).get("max_calls", 20),
        "web_scraper_fetch_page": config.get("web_scraper_fetch_page", {}).get("max_calls", 30)
    }
    return _limits_cache

def init_api_counts():
    api_call_counts.set({
        "google_maps_geocoding": 0,
        "overpass_api": 0,
        "serper_dev_search": 0,
        "mashvisor_api": 0,
        "llm_gemini_flash": 0,
        "llm_gemini_pro": 0,
        "web_scraper_fetch_page": 0,
    })

def increment_api_count(api_name: str):
    counts = api_call_counts.get()
    if counts is None:
        # Fallback if context is not initialized (e.g. unit tests running directly)
        return

    limits = load_limits()
    limit = limits.get(api_name, 999)

    counts[api_name] = counts.get(api_name, 0) + 1
    logger.info(f"API Call tracked: {api_name} (Count: {counts[api_name]}/{limit})")
    if counts[api_name] > limit:
        raise ApiLimitExceededError(api_name, limit)

def get_current_counts() -> dict:
    counts = api_call_counts.get()
    return dict(counts) if counts else {}
