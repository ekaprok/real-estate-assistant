# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pytest
from app.api_limits import init_api_counts, increment_api_count, ApiLimitExceededError, get_current_counts
from app.integrations import geocode_location, query_mashvisor_api
from app.tools import serper_search, fetch_page

def test_api_limits_tracking():
    # Initialize call counters
    init_api_counts()

    # Test tracking works
    increment_api_count("google_maps_geocoding")
    increment_api_count("google_maps_geocoding")
    counts = get_current_counts()
    assert counts["google_maps_geocoding"] == 2
    # Counters are created lazily, so an un-called API simply isn't present yet.
    assert counts.get("overpass_api", 0) == 0

def test_api_limits_enforcement():
    init_api_counts(1)

    # Intentionally trigger limit violation for overpass_api (limit = 2 + 1*1 = 3)
    with pytest.raises(ApiLimitExceededError) as exc_info:
        for _ in range(25):
            increment_api_count("overpass_api")

    assert "The rate has been met" in str(exc_info.value)

def test_geocode_location_mock():
    init_api_counts()

    # Test that Irvine query geocodes to Irvine
    res = geocode_location("Irvine, CA")
    assert len(res) == 1
    assert res[0]["municipality"] == "Irvine"
    assert res[0]["state"] == "CA"

    import os
    orig = os.environ.get("USE_MOCK_APIS")
    os.environ["USE_MOCK_APIS"] = "True"

    try:
        # Test exception on unknown location
        res_default = geocode_location("Unknown Location 123")
    except ValueError:
        pass
    finally:
        if orig is None:
            del os.environ["USE_MOCK_APIS"]
        else:
            os.environ["USE_MOCK_APIS"] = orig
    assert len(res_default) == 1
    assert res_default[0]["municipality"] == "Gatlinburg"

def test_query_mashvisor_mock():
    init_api_counts()

    import os
    orig = os.environ.get("USE_MOCK_APIS")
    os.environ["USE_MOCK_APIS"] = "True"

    try:
        res = query_mashvisor_api("Gatlinburg", "TN")
        assert res["sample_size"] == 142
        assert res["median_property_price"] == 450000
        assert res["average_daily_rate_adr"] == 285

        res_default = query_mashvisor_api("Unknown City", "XX")
        assert res_default["sample_size"] == 142
    finally:
        if orig is None:
            del os.environ["USE_MOCK_APIS"]
        else:
            os.environ["USE_MOCK_APIS"] = orig
    assert res_default["average_daily_rate_adr"] == 285

def test_serper_search_mock():
    init_api_counts()

    import os
    orig = os.environ.get("USE_MOCK_APIS")
    os.environ["USE_MOCK_APIS"] = "True"

    try:
        res = serper_search("New York City short term rental ban")
        assert "organic" in res
    finally:
        if orig is None:
            del os.environ["USE_MOCK_APIS"]
        else:
            os.environ["USE_MOCK_APIS"] = orig
    assert len(res["organic"]) > 0
    assert "Local Law 18" in res["organic"][0]["snippet"]

def test_fetch_page_mock():
    init_api_counts()

    import os
    orig = os.environ.get("USE_MOCK_APIS")
    os.environ["USE_MOCK_APIS"] = "True"

    try:
        res = fetch_page("https://www.nyc.gov/site/specialenforcement/registration-law/registration-law-for-hosts.page")
        assert "url" in res
        assert "Local Law 18" in res["text"]
    finally:
        if orig is None:
            del os.environ["USE_MOCK_APIS"]
        else:
            os.environ["USE_MOCK_APIS"] = orig

def test_filter_str_relevant_text():
    from app.tools import filter_str_relevant_text

    text = "Welcome to our city website. " * 50
    text += "Short-term rental permits require a minimum stay of 30 days in residential zones."
    text += " Contact us for more information. " * 50

    filtered = filter_str_relevant_text(text)
    assert "short-term rental" in filtered.lower()
    assert len(filtered) <= 3000
    assert len(filtered) < len(text)
