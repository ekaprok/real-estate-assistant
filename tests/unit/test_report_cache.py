import os
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

import app.integrations
import app.tools
from app.api_limits import ApiLimitExceededError
from app.app_utils.cache import CACHE_DB_PATH, get_cached_response
from app.pipeline import run_pipeline

# Ensure mock mode is active for testing to avoid hitting live APIs
app.integrations.USE_MOCK_APIS = True
app.tools.USE_MOCK_APIS = True
os.environ["USE_MOCK_APIS"] = "True"

def clear_test_cache():
    """Helper to clear report cache entries from SQLite."""
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_cache WHERE cache_key LIKE 'mock_report_%' OR cache_key LIKE 'report_%'")
        conn.commit()

@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_test_cache()
    yield
    clear_test_cache()

def test_pipeline_caching_bypasses_downstream():
    """Verify that a second run with the same prompt returns cached report and bypasses downstream pipeline steps."""
    # First run: populates cache
    res1 = run_pipeline("Jersey City rentals")
    assert "Jersey City" in res1
    assert "error" not in res1

    # Second run: must hit cache and bypass query_mashvisor_api
    with patch("app.pipeline.query_mashvisor_api") as mock_mashvisor:
        res2 = run_pipeline("Jersey City rentals")
        mock_mashvisor.assert_not_called()
        assert res1 == res2

def test_pipeline_caching_equivalent_phrasings():
    """Verify that different phrasings that parse to the same parameters hit the same cache key."""
    # Run first phrasing: populates cache
    res1 = run_pipeline("Are there rentals in Jersey City?")
    assert "Jersey City" in res1

    # Run second phrasing (equivalent target geography/parameters): should hit the cache
    with patch("app.pipeline.query_mashvisor_api") as mock_mashvisor:
        res2 = run_pipeline("jersey city rentals")
        mock_mashvisor.assert_not_called()
        assert res1 == res2

def test_pipeline_does_not_cache_api_limit_exceeded_error():
    """Verify that if an ApiLimitExceededError is raised, the error response is NOT saved to the cache."""
    # Patch query_mashvisor_api to raise ApiLimitExceededError
    with patch("app.pipeline.query_mashvisor_api", side_effect=ApiLimitExceededError("mashvisor_api", 2)):
        res1 = run_pipeline("Gatlinburg cabins")
        assert "API limit exceeded" in res1

    # Now verify that no report key for Gatlinburg is in the cache database
    # Let's run with standard query_mashvisor_api and check that it actually gets called
    # (if it was cached, it wouldn't call query_mashvisor_api)
    with patch("app.pipeline.query_mashvisor_api") as mock_mashvisor:
        mock_mashvisor.return_value = {
            "sample_size": 10,
            "median_property_price": 500000,
            "average_daily_rate_adr": 200,
            "annual_occupancy_rate_percentage": 60,
            "estimated_opex": {
                "property_management_pct": 15,
                "insurance_pct": 3,
                "utilities_pct": 5,
                "property_taxes_pct": 5
            },
            "active_listings_count": 5,
            "listings_growth_yoy_percentage": 2.0,
            "revenue_growth_yoy_percentage": 3.0,
            "seasonality_summary": "High",
            "optimal_config": {
                "property_type": "Cabin",
                "bedrooms": 2,
                "bathrooms": 2,
                "accommodates": 4
            }
        }
        res2 = run_pipeline("Gatlinburg cabins")
        mock_mashvisor.assert_called_once()
        assert "API limit exceeded" not in res2

def test_pipeline_logs_final_report():
    """Verify that the final report YAML is logged under logger.info."""
    with patch("app.pipeline.logger") as mock_logger:
        res = run_pipeline("Jersey City rentals")

        # Verify that logger.info was called with the report string
        # We search for any call to logger.info that contains "Final Report:"
        info_calls = [call for call in mock_logger.info.call_args_list if "Final Report:" in str(call)]
        assert len(info_calls) > 0, "Expected logger.info to be called with final report prefix"


def test_step_level_caching_pydantic_serialization():
    """Verify that functions returning Pydantic models cache results and hit the cache on subsequent calls."""
    from app.llm import parse_user_prompt, IngestedInputs

    p1 = parse_user_prompt("Union City, NJ")
    assert isinstance(p1, IngestedInputs)

    with patch("app.llm.call_gemini_flash") as mock_flash:
        p2 = parse_user_prompt("Union City, NJ")
        mock_flash.assert_not_called()
        assert p1.target_locations == p2.target_locations
