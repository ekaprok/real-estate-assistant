import contextvars
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

# API limits maintained directly in this file
API_LIMITS = {
    "google_maps_geocoding": 5,
    "overpass_api": 5,
    "serper_dev_search": 20,
    "mashvisor_api": 2,
    "llm_gemini_flash": 15,
    "llm_gemini_flash_loop": 10,
    "web_scraper_fetch_page": 10,
}

def init_api_counts():
    api_call_counts.set({
        "google_maps_geocoding": 0,
        "overpass_api": 0,
        "serper_dev_search": 0,
        "mashvisor_api": 0,
        "llm_gemini_flash": 0,
        "llm_gemini_flash_loop": 0,
        "web_scraper_fetch_page": 0,
    })

def increment_api_count(api_name: str):
    counts = api_call_counts.get()
    if counts is None:
        # Fallback if not initialized at all (e.g. unit tests running directly)
        return

    limit = API_LIMITS.get(api_name, 999)

    counts[api_name] = counts.get(api_name, 0) + 1
    logger.info(f"API Call tracked: {api_name} (Count: {counts[api_name]}/{limit})")
    if counts[api_name] > limit:
        raise ApiLimitExceededError(api_name, limit)

def get_current_counts() -> dict:
    counts = api_call_counts.get()
    return dict(counts) if counts else {}
