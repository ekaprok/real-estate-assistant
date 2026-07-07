import os
import sqlite3
import pytest
from unittest.mock import patch, MagicMock

import app.integrations
import app.tools
from app.api_limits import ApiLimitExceededError
from app.app_utils.cache import CACHE_DB_PATH, get_cached_response
from app.pipeline import run_pipeline

# Ensure mock mode is DISABLED for caching tests to allow caching to work
app.integrations.USE_MOCK_APIS = False
app.tools.USE_MOCK_APIS = False
os.environ["USE_MOCK_APIS"] = "False"

def clear_test_cache():
    """Helper to clear report cache entries from SQLite."""
    with sqlite3.connect(CACHE_DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM api_cache WHERE cache_key LIKE 'report_%'")
        conn.commit()

@pytest.fixture(autouse=True)
def setup_and_teardown():
    clear_test_cache()
    yield
    clear_test_cache()

@pytest.fixture
def mock_all_apis():
    """Mocks all external API calls to avoid hitting live endpoints during tests."""
    from tests.mocks.integrations_mocks import MOCK_MASHVISOR_DB
    from app.llm import IngestedInputs, MacroScreenResult, LegalStatus, ReportSynthesis

    with patch("app.pipeline.parse_user_prompt") as mock_parse, \
         patch("app.pipeline.geocode_location") as mock_geocode, \
         patch("app.pipeline.run_macro_legal_screen") as mock_macro, \
         patch("app.pipeline.run_agent") as mock_agent, \
         patch("app.pipeline.extract_legal_status") as mock_extract, \
         patch("app.pipeline.query_mashvisor_api") as mock_mashvisor, \
         patch("app.pipeline.synthesize_report") as mock_synth:

        # Setup mock returns
        mock_parse.return_value = IngestedInputs(target_locations=["Jersey City"])
        mock_geocode.return_value = [{"municipality": "Jersey City", "state": "NJ", "county": "Hudson County"}]
        mock_macro.return_value = MacroScreenResult(status="RESTRICTED", restriction_reason="Test")
        mock_agent.return_value = "Mock research summary"
        mock_extract.return_value = LegalStatus(
            status="RESTRICTED", restriction_reason="Test", eligible_zones_summary="Test",
            primary_residence_required=True, minimum_stay_days=30, permit_cap_exists=True,
            regulatory_trajectory_risk="Low", summary_of_restrictions="Test"
        )
        mock_mashvisor.return_value = MOCK_MASHVISOR_DB.get("Jersey City", {
            "sample_size": 10,
            "median_property_price": 500000,
            "annual_occupancy_rate_percentage": 60,
            "average_cap_rate_percentage": 6.0,
            "monthly_rental_income": 4000,
            "airbnb_properties_count": 5,
        })
        mock_synth.return_value = ReportSynthesis(qualitative_synthesis="Test synthesis")

        yield {
            "parse": mock_parse,
            "geocode": mock_geocode,
            "macro": mock_macro,
            "agent": mock_agent,
            "extract": mock_extract,
            "mashvisor": mock_mashvisor,
            "synth": mock_synth
        }

def test_pipeline_caching_bypasses_downstream(mock_all_apis):
    """Verify that a second run with the same prompt returns cached report and bypasses downstream pipeline steps."""
    # First run: populates cache
    res1 = run_pipeline("Jersey City rentals")
    assert "Jersey City" in res1
    assert "error" not in res1

    # Reset mock call counts
    mock_all_apis["mashvisor"].reset_mock()

    # Second run: must hit cache and bypass query_mashvisor_api
    res2 = run_pipeline("Jersey City rentals")
    mock_all_apis["mashvisor"].assert_not_called()
    assert res1 == res2

def test_pipeline_caching_equivalent_phrasings(mock_all_apis):
    """Verify that different phrasings that parse to the same parameters hit the same cache key."""
    # Run first phrasing: populates cache
    res1 = run_pipeline("Are there rentals in Jersey City?")
    assert "Jersey City" in res1

    # Reset mock call counts
    mock_all_apis["mashvisor"].reset_mock()

    # Run second phrasing (equivalent target geography/parameters): should hit the cache
    res2 = run_pipeline("jersey city rentals")
    mock_all_apis["mashvisor"].assert_not_called()
    assert res1 == res2

def test_pipeline_does_not_cache_api_limit_exceeded_error(mock_all_apis):
    """Verify that if an ApiLimitExceededError is raised, the error response is NOT saved to the cache."""
    # Patch query_mashvisor_api to raise ApiLimitExceededError
    mock_all_apis["mashvisor"].side_effect = ApiLimitExceededError("mashvisor_api", 2)

    res1 = run_pipeline("Gatlinburg cabins")
    assert "API limit exceeded" in res1

    # Now verify that no report key for Gatlinburg is in the cache database
    # Let's run with standard query_mashvisor_api and check that it actually gets called
    # (if it was cached, it wouldn't call query_mashvisor_api)
    mock_all_apis["mashvisor"].side_effect = None
    mock_all_apis["mashvisor"].reset_mock()
    mock_all_apis["mashvisor"].return_value = {
        "sample_size": 10,
        "median_property_price": 500000,
        "annual_occupancy_rate_percentage": 60,
        "average_cap_rate_percentage": 6.0,
        "monthly_rental_income": 4000,
        "airbnb_properties_count": 5,
    }

    res2 = run_pipeline("Gatlinburg cabins")
    mock_all_apis["mashvisor"].assert_called_once()
    assert "API limit exceeded" not in res2

def test_pipeline_logs_final_report(mock_all_apis):
    """Verify that the final report YAML is logged under logger.info."""
    with patch("app.pipeline.logger") as mock_logger:
        res = run_pipeline("Jersey City rentals")

        # Verify that logger.info was called with the report string
        # We search for any call to logger.info that contains "Final Report:"
        info_calls = [call for call in mock_logger.info.call_args_list if "Final Report:" in str(call)]
        assert len(info_calls) > 0, "Expected logger.info to be called with final report prefix"


def test_step_level_caching_pydantic_serialization(mock_all_apis):
    """Verify that functions returning Pydantic models cache results and hit the cache on subsequent calls."""
    # We need to unmock parse_user_prompt for this specific test
    # since we want to test its caching behavior directly
    mock_all_apis["parse"].stop()

    # We need to mock call_gemini_flash so parse_user_prompt doesn't hit the real API
    from app.llm import IngestedInputs
    with patch("app.llm.call_gemini_flash") as mock_gemini:
        mock_gemini.return_value = IngestedInputs(target_locations=["Union City, NJ"])

        from app.llm import parse_user_prompt

        # Clear cache for this specific key
        import hashlib
        val = "Union City, NJ".lower()
        args_hash = hashlib.md5(val.encode("utf-8")).hexdigest()
        cache_key = f"parse_{args_hash}"
        with sqlite3.connect(CACHE_DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM api_cache WHERE cache_key = ?", (cache_key,))
            conn.commit()

        p1 = parse_user_prompt("Union City, NJ")
        assert isinstance(p1, IngestedInputs)
        mock_gemini.assert_called_once()

        mock_gemini.reset_mock()

        p2 = parse_user_prompt("Union City, NJ")
        assert isinstance(p2, IngestedInputs)
        assert p1.target_locations == p2.target_locations

        # Should hit cache, not the mock
        mock_gemini.assert_not_called()
