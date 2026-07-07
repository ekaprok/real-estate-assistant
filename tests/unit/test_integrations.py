"""Unit tests for the Mashvisor integration in ``app.integrations``.

These exercise the live-path mapping from the Mashvisor ``city/investment``
payload to our flat internal schema without hitting the network. Caching is
bypassed so each test asserts against the mocked HTTP response directly.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from app.api_limits import init_api_counts
from app.integrations import (
    _empty_mashvisor_result,
    _to_float,
    _to_int,
    is_placeholder_or_missing,
    query_mashvisor_api,
)

# A trimmed but representative city/investment response body.
SAMPLE_CITY_INVESTMENT = {
    "status": "success",
    "content": {
        "median_price": 450000,
        "sqft": 2100.5,
        "investment_properties": 120,
        "airbnb_properties": 300,
        "traditional_properties": 250,
        "occupancy": 68,
        "airbnb_cap_rate": 7.83,
        "traditional_cap_rate": 5.1,
        "airbnb_rental": 5895,
        "traditional_rental": 3200,
    },
    "message": "City Overview fetched successfully",
}


def _fake_response(json_body: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    return resp


class TestHelpers:
    @pytest.mark.parametrize(
        "value, expected",
        [(7.83, 7.83), ("7.83", 7.83), (None, 0.0), ("nan_text", 0.0), (5, 5.0)],
    )
    def test_to_float(self, value, expected):
        assert _to_float(value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [(68, 68), ("68", 68), (68.9, 68), (None, 0), ("bad", 0)],
    )
    def test_to_int(self, value, expected):
        assert _to_int(value) == expected

    def test_empty_result_has_full_schema(self):
        result = _empty_mashvisor_result()
        assert set(result) == {
            "sample_size",
            "median_property_price",
            "annual_occupancy_rate_percentage",
            "average_cap_rate_percentage",
            "monthly_rental_income",
            "airbnb_properties_count",
        }
        assert all(v == 0 for v in result.values())

    def test_placeholder_detection(self):
        assert is_placeholder_or_missing(None) is True
        assert is_placeholder_or_missing("") is True
        assert is_placeholder_or_missing("YOUR_KEY_HERE") is True
        assert is_placeholder_or_missing("prod_mashvisor_xyz") is True
        assert is_placeholder_or_missing("live_secret_123") is False


class TestQueryMashvisorLivePath:
    """Live-path mapping with the network + cache mocked out."""

    def _run(self, json_body: dict, key: str = "live_secret_123"):
        init_api_counts()
        with patch.dict(
            os.environ,
            {"USE_MOCK_APIS": "False", "MASHVISOR_API_KEY_DEV": key},
        ), patch(
            "app.app_utils.cache.get_cached_response", return_value=None
        ), patch(
            "app.app_utils.cache.set_cached_response"
        ), patch(
            "app.integrations.requests.get", return_value=_fake_response(json_body)
        ) as mock_get:
            result = query_mashvisor_api("Gatlinburg", "TN")
        return result, mock_get

    def test_maps_only_supported_fields(self):
        result, _ = self._run(SAMPLE_CITY_INVESTMENT)
        assert result == {
            "sample_size": 120,  # investment_properties
            "median_property_price": 450000,
            "annual_occupancy_rate_percentage": 68,
            "average_cap_rate_percentage": 7.8,  # rounded from 7.83
            "monthly_rental_income": 5895,
            "airbnb_properties_count": 300,
        }

    def test_no_fabricated_fields_leak_through(self):
        result, _ = self._run(SAMPLE_CITY_INVESTMENT)
        for banned in (
            "average_daily_rate_adr",
            "estimated_opex",
            "optimal_config",
            "seasonality_summary",
            "listings_growth_yoy_percentage",
            "revenue_growth_yoy_percentage",
        ):
            assert banned not in result

    def test_hits_city_investment_endpoint(self):
        _, mock_get = self._run(SAMPLE_CITY_INVESTMENT)
        called_url = mock_get.call_args.args[0]
        assert "/city/investment/TN/Gatlinburg" in called_url

    def test_rapidapi_key_uses_rapidapi_host(self):
        _, mock_get = self._run(SAMPLE_CITY_INVESTMENT, key="f817msh0276live")
        called_url = mock_get.call_args.args[0]
        assert called_url.startswith("https://mashvisor-api.p.rapidapi.com/")
        headers = mock_get.call_args.kwargs["headers"]
        assert "X-RapidAPI-Key" in headers

    def test_coerces_string_numbers(self):
        body = {
            "content": {
                "median_price": "450000",
                "investment_properties": "120",
                "airbnb_properties": "300",
                "occupancy": "68",
                "airbnb_cap_rate": "7.83",
                "airbnb_rental": "5895",
            }
        }
        result, _ = self._run(body)
        assert result["median_property_price"] == 450000
        assert result["average_cap_rate_percentage"] == 7.8

    def test_missing_content_returns_empty_metrics(self):
        result, _ = self._run({"status": "success"})
        assert result == _empty_mashvisor_result()

    def test_embedded_error_message_raises(self):
        with pytest.raises(ValueError, match="error message"):
            self._run({"message": "Invalid API key"})

    def test_placeholder_key_raises(self):
        init_api_counts()
        with patch.dict(
            os.environ,
            {"USE_MOCK_APIS": "False", "MASHVISOR_API_KEY_DEV": "your_key_here"},
        ), patch("app.integrations.requests.get") as mock_get:
            with pytest.raises(ValueError, match="missing or is a placeholder"):
                query_mashvisor_api("Gatlinburg", "TN")
        mock_get.assert_not_called()
