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

# Per-run limits (set via init_api_counts)
api_limits = contextvars.ContextVar("api_limits", default=None)

# Max API calls per resolved municipality.
CALLS_PER_MUNICIPALITY = {
    "google_maps_geocoding": 1,
    "overpass_api": 1,
    "mashvisor_api": 1,
    "llm_gemini_flash": 3,  # macro screen + extract + synthesis per municipality
    "llm_gemini_flash_loop": 6,  # executor + evaluator, up to 3 loop iterations
    "serper_dev_search": 5,  # macro screen + deep-research searches
    "web_scraper_fetch_page": 6,  # top 2-3 URLs per loop iteration
}

# Run-wide base calls not tied to a specific municipality (e.g. prompt parsing).
RUN_BASE_CALLS = {
    "google_maps_geocoding": 2,
    "overpass_api": 2,
    "llm_gemini_flash": 4,  # 1 parse call + buffer
}

_UNCONFIGURED_LIMIT = 999


def build_api_limits(num_municipalities: int) -> dict[str, int]:
    """Return per-run API limits scaled from the number of municipalities."""
    n = max(num_municipalities, 1)
    keys = set(CALLS_PER_MUNICIPALITY.keys()) | set(RUN_BASE_CALLS.keys())
    return {
        api: RUN_BASE_CALLS.get(api, 0) + CALLS_PER_MUNICIPALITY.get(api, 0) * n
        for api in keys
    }


def init_api_counts(
    limits: dict[str, int] | int | None = None,
    reset: bool = True,
):
    """Reset per-run counters and optionally set API limits.

    Pass an int (municipality count) to compute limits automatically, or a
    pre-built dict. Use ``reset=False`` to update limits mid-run without
    clearing counts already accumulated.
    """
    if reset:
        api_call_counts.set({})
    if isinstance(limits, int):
        api_limits.set(build_api_limits(limits))
    elif limits is not None:
        api_limits.set(limits)


def _get_limit(api_name: str) -> int:
    limits = api_limits.get()
    return limits.get(api_name, _UNCONFIGURED_LIMIT) if limits is not None else _UNCONFIGURED_LIMIT


def increment_api_count(api_name: str):
    counts = api_call_counts.get()
    if counts is None:
        # Fallback if not initialized at all (e.g. unit tests running directly)
        return

    counts[api_name] = counts.get(api_name, 0) + 1
    limit = _get_limit(api_name)

    logger.info(f"API Call tracked: {api_name} (Count: {counts[api_name]}/{limit})")

    if counts[api_name] > limit:
        raise ApiLimitExceededError(api_name, limit)


def get_current_counts() -> dict[str, int]:
    counts = api_call_counts.get()
    return dict(counts) if counts else {}
