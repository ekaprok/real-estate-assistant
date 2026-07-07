import os
import logging
import requests
from app.api_limits import increment_api_count
from app.app_utils.cache import with_cache, get_cached_response, set_cached_response, init_cache_db

# Configure logger
logger = logging.getLogger(__name__)

# Run DB initialization at import time
init_cache_db()

from app.mock_handlers import _use_mock_apis

# Lazy/conditional import of mocks to isolate test code from production logic
try:
    from tests.mocks.integrations_mocks import MOCK_GEOMAP, MOCK_MASHVISOR_DB
except ImportError:
    logger.warning("Mock datasets not found. Defaulting to empty mocks.")
    MOCK_GEOMAP = {}
    MOCK_MASHVISOR_DB = {}

# Check if an API key is a placeholder or missing
def is_placeholder_or_missing(key: str | None) -> bool:
    if not key:
        return True
    key_lower = key.lower()
    return any(p in key_lower for p in ["your_", "placeholder", "key_here", "prod_mashvisor"])


def _to_float(value) -> float:
    """Coerce a Mashvisor field to float, defaulting to 0.0 on missing/bad data."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_int(value) -> int:
    return int(_to_float(value))


def _empty_mashvisor_result() -> dict:
    """Zeroed metrics for municipalities Mashvisor has no city coverage for."""
    return {
        "sample_size": 0,
        "median_property_price": 0,
        "annual_occupancy_rate_percentage": 0,
        "average_cap_rate_percentage": 0.0,
        "monthly_rental_income": 0,
        "airbnb_properties_count": 0,
    }

@with_cache("geocode")
def geocode_location(location_query: str) -> list[dict]:
    """Resolves target geography to coordinates/bounding box. Encapsulates count & caching."""
    increment_api_count("google_maps_geocoding")

    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY_DEV")

    if _use_mock_apis():
        logger.info(f"Using mock geocoding for {location_query}.")
        query_lower = location_query.lower()
        results = None
        for key, val in MOCK_GEOMAP.items():
            if key in query_lower:
                results = val
                break

        if results is None:
            results = [{"municipality": "Gatlinburg", "state": "TN", "county": "Sevier"}]

        return results

    if not maps_key or is_placeholder_or_missing(maps_key):
        raise ValueError("Google Maps API key is missing or is a placeholder, but USE_MOCK_APIS is False.")

    # Real Google Maps Geocoding API call
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": location_query, "key": maps_key}
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("results", []):
            municipality = ""
            state = ""
            county = ""
            for comp in result.get("address_components", []):
                types = comp.get("types", [])
                if "locality" in types:
                    municipality = comp["long_name"]
                elif "administrative_area_level_1" in types:
                    state = comp["short_name"]
                elif "administrative_area_level_2" in types:
                    county = comp["long_name"]

            if municipality and state:
                results.append({
                    "municipality": municipality,
                    "state": state,
                    "county": county
                })

        if not results:
            raise ValueError(f"No valid municipality/state found for location query: '{location_query}'")

        return results
    except Exception as e:
        logger.error(f"Geocoding failed for {location_query}: {e}")
        raise e

def resolve_municipalities_overpass(lat: float, lng: float) -> list[dict]:
    """Queries Overpass API or returns mock results based on mock coordinates."""
    increment_api_count("overpass_api")

    if _use_mock_apis():
        return []

    headers = {"User-Agent": "RealEstateAssistant/1.0 (local-dev)"}
    overpass_url = "https://overpass-api.de/api/interpreter"
    # Search for admin_level=8 (municipalities) around the coordinates
    overpass_query = f"""
    [out:json][timeout:15];
    is_in({lat},{lng})->.a;
    area.a[admin_level=8];
    out body;
    """
    try:
        response = requests.post(overpass_url, data={"data": overpass_query}, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()

        municipalities = []
        for element in data.get("elements", []):
            tags = element.get("tags", {})
            name = tags.get("name")
            if name:
                municipalities.append({"municipality": name})
        return municipalities
    except Exception as e:
        logger.error(f"Overpass API request failed: {e}")
        return []

@with_cache("mashvisor")
def query_mashvisor_api(municipality: str, state: str) -> dict:
    """Queries Mashvisor data for a resolved municipality/state. Tracks limit & mocks."""
    increment_api_count("mashvisor_api")

    mashvisor_key = os.environ.get("MASHVISOR_API_KEY_DEV")

    if _use_mock_apis():
        logger.info(f"Using mock Mashvisor data for {municipality}, {state}.")
        result = MOCK_MASHVISOR_DB.get(municipality)
        if result is None:
            # Check by state or substring
            for name, data in MOCK_MASHVISOR_DB.items():
                if name.lower() in municipality.lower():
                    result = data
                    break

        if result is None:
            result = MOCK_MASHVISOR_DB.get("Gatlinburg", {}) # Default fallback

        return result

    if not mashvisor_key or is_placeholder_or_missing(mashvisor_key):
        raise ValueError("Mashvisor API key is missing or is a placeholder, but USE_MOCK_APIS is False.")

    # Real Mashvisor API request.
    #
    # We use the city-level investment endpoint, which returns aggregate median
    # performance for the whole municipality in a single call:
    #   GET /v1.1/client/city/investment/{state}/{city}
    # This is both simpler and more accurate than pulling the raw property list
    # and computing medians client-side. We only surface the fields this endpoint
    # actually returns (median_price, occupancy, airbnb_cap_rate, airbnb_rental,
    # and the comp counts); no synthetic ADR/opex/seasonality/growth values.
    try:
        import urllib.parse

        state_enc = urllib.parse.quote(state)
        city_enc = urllib.parse.quote(municipality)

        # RapidAPI-hosted keys ("msh" identifier) use a different host/header.
        if "msh" in mashvisor_key:
            url = f"https://mashvisor-api.p.rapidapi.com/city/investment/{state_enc}/{city_enc}"
            headers = {
                "X-RapidAPI-Key": mashvisor_key,
                "X-RapidAPI-Host": "mashvisor-api.p.rapidapi.com",
            }
        else:
            url = f"https://api.mashvisor.com/v1.1/client/city/investment/{state_enc}/{city_enc}"
            headers = {"x-api-key": mashvisor_key}

        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched live Mashvisor data for {municipality}, {state}.")

        # Errors can arrive embedded in a 200 response (e.g. {'message': '...'}).
        if "message" in data and len(data) == 1:
            raise ValueError(f"Mashvisor API returned an error message: {data['message']}")

        content = data.get("content")
        if not isinstance(content, dict):
            logger.warning(
                f"No city investment data for {municipality}, {state}. "
                "Returning empty metrics."
            )
            return _empty_mashvisor_result()

        return {
            # investment_properties = comp pool backing the medians; drives data quality.
            "sample_size": _to_int(content.get("investment_properties")),
            "median_property_price": _to_int(content.get("median_price")),
            "annual_occupancy_rate_percentage": _to_int(content.get("occupancy")),
            "average_cap_rate_percentage": round(_to_float(content.get("airbnb_cap_rate")), 1),
            # airbnb_rental is Mashvisor's median monthly Airbnb income.
            "monthly_rental_income": _to_int(content.get("airbnb_rental")),
            "airbnb_properties_count": _to_int(content.get("airbnb_properties")),
        }
    except Exception as e:
        logger.error(f"Mashvisor API request failed for {municipality}, {state}: {e}")
        raise e
