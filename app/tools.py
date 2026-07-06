import os
import requests
import logging

USE_MOCK_APIS = os.environ.get("USE_MOCK_APIS", "False").lower() == "true"
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logger
logger = logging.getLogger(__name__)

# Load .env file manually at import time
def load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

load_env_file()

from app.api_limits import increment_api_count
from app.app_utils.cache import with_cache

# Lazy/conditional import of mocks to isolate test code from production logic
try:
    from tests.mocks.tools_mocks import MOCK_SEARCH_RESULTS, MOCK_PAGES
except ImportError:
    logger.warning("Mock search/pages datasets not found. Defaulting to empty mocks.")
    MOCK_SEARCH_RESULTS = {}
    MOCK_PAGES = {}

STR_RELEVANCE_ANCHORS = [
    "short-term rental",
    "short term rental",
    "vacation rental",
    "transient occupancy",
    "transient lodging",
    "zoning",
    "permit",
    "minimum stay",
    "primary residence",
    "vacation dwelling",
    "yurt",
    "rv",
    "tiny home",
    "accessory dwelling",
    "temporary structure",
    "hotel tax",
    "occupancy tax",
]

def filter_str_relevant_text(text: str, window: int = 500, max_chars: int = 3000) -> str:
    """Extract STR-relevant windows around anchor terms to reduce LLM input tokens."""
    if not text:
        return text

    text_lower = text.lower()
    spans: list[tuple[int, int]] = []
    for anchor in STR_RELEVANCE_ANCHORS:
        start = 0
        anchor_lower = anchor.lower()
        while True:
            idx = text_lower.find(anchor_lower, start)
            if idx == -1:
                break
            spans.append((max(0, idx - window), min(len(text), idx + len(anchor) + window)))
            start = idx + len(anchor)

    if not spans:
        return text[:3000]

    spans.sort()
    merged: list[tuple[int, int]] = []
    for span_start, span_end in spans:
        if merged and span_start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], span_end))
        else:
            merged.append((span_start, span_end))

    chunks = [text[s:e].strip() for s, e in merged]
    filtered = " ... ".join(chunks)
    return filtered[:max_chars]

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _execute_serper_request(url: str, headers: dict, query: str) -> dict:
    """Executes the Serper request with retry logic."""
    logger.info(f"Executing Serper API post request for query: {query}")
    response = requests.post(url, headers=headers, json={"q": query}, timeout=15)
    response.raise_for_status()
    return response.json()

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def _execute_fetch_request(url: str, headers: dict) -> str:
    """Executes the Page Fetch request with retry logic."""
    logger.info(f"Executing fetch request for URL: {url}")
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    return response.text

@with_cache("search")
def serper_search(query: str) -> dict:
    """Performs a web search using the Serper API. Enforces limits and caches results.

    Args:
        query: The search query string.

    Returns:
        A dictionary containing the search results (snippets and links).
    """
    increment_api_count("serper_dev_search")

    serper_key = os.environ.get("SERPER_API_KEY") or os.environ.get("SERPER_API_KEY_DEV")

    if USE_MOCK_APIS:
        logger.info("Using mock search results.")
        query_lower = query.lower()
        results = None
        for key, val in MOCK_SEARCH_RESULTS.items():
            if key in query_lower:
                results = val
                break
        if results is None:
            results = MOCK_SEARCH_RESULTS.get("gatlinburg", {})

        return results

    if not serper_key or "your_" in serper_key or "placeholder" in serper_key:
        raise ValueError("Serper API key is missing or is a placeholder, but USE_MOCK_APIS is False.")

    # Real Search API Call with tenacity retry
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": serper_key, "Content-Type": "application/json"}
        return _execute_serper_request(url, headers, query)
    except Exception as e:
        logger.error(f"Serper API call failed after retries: {e}")
        if USE_MOCK_APIS:
            query_lower = query.lower()
            for key, val in MOCK_SEARCH_RESULTS.items():
                if key in query_lower:
                    return val
            return MOCK_SEARCH_RESULTS.get("gatlinburg", {})
        raise e

@with_cache("fetch")
def fetch_page(url: str) -> dict:
    """Downloads the full text of a zoning code or webpage. Enforces limits and caches.

    Args:
        url: The absolute URL of the page to scrape.

    Returns:
        A dictionary with 'url' and 'text' keys.
    """
    increment_api_count("web_scraper_fetch_page")

    if USE_MOCK_APIS:
        # Check mock pages first
        if url in MOCK_PAGES:
            return {"url": url, "text": MOCK_PAGES[url]}

        # Check if it is a mock domain or placeholder
        if any(p in url for p in ["localhost", "example.com", "municode-mock"]):
            # Return generic mock zoning
            return {"url": url, "text": "This zoning code permits short term rentals subject to local registration and safety rules."}

    # Real Scrape HTTP Call with tenacity retry
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RealEstateAssistant/1.0"}
        html_content = _execute_fetch_request(url, headers)

        soup = BeautifulSoup(html_content, "html.parser")
        # Remove script/style tags
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        text = soup.get_text(separator=" ").strip()
        # Clean up whitespace
        text = " ".join(text.split())
        text = filter_str_relevant_text(text)

        return {"url": url, "text": text}
    except Exception as e:
        logger.error(f"Web scraper call failed after retries for URL {url}: {e}.")
        fallback_text = "Error: Page could not be accessed. The site may block scrapers or is down. Please try a different search or source."

        if USE_MOCK_APIS:
            logger.error(f"Falling back to mock.")
            for m_url, m_text in MOCK_PAGES.items():
                if m_url in url or url in m_url:
                    fallback_text = m_text
                    break

        return {"url": url, "text": fallback_text}
