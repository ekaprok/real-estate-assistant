"""Unit tests for the class-based pipeline stages in ``app.pipeline``.

Each stage (geo resolution, legal screening, financial analysis, report
building and orchestration) is exercised in isolation with the external
dependencies patched at the ``app.pipeline`` module boundary.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from app.llm import (
    IngestedInputs,
    LegalStatus,
    MacroScreenResult,
    Permit,
    ReportSynthesis,
    SpecialTax,
)
from app.pipeline import (
    ClearedMunicipality,
    FinancialAnalyzer,
    GeoResolver,
    LegalScreener,
    MAX_MUNICIPALITIES,
    Pipeline,
    ReportBuilder,
    ResolvedMunicipality,
    ScreeningOutcome,
    generate_research_prompt,
    run_pipeline,
)


# --------------------------------------------------------------------------- #
# Factories
# --------------------------------------------------------------------------- #
def make_legal_status(status: str = "ALLOWED", **overrides) -> LegalStatus:
    defaults = {
        "status": status,
        "restriction_reason": "reason",
        "eligible_zones_summary": "commercial zones",
        "primary_residence_required": False,
        "minimum_stay_days": 2,
        "permit_cap_exists": False,
        "permits": [
            Permit(
                name="STR Permit",
                process_summary="Annual registration",
                application_url="https://example.gov/str",
            )
        ],
        "special_taxes": [
            SpecialTax(name="TOT", rate="9%", description="Occupancy tax")
        ],
        "regulatory_trajectory_risk": "Low",
        "summary_of_restrictions": "Allowed with permit",
    }
    defaults.update(overrides)
    return LegalStatus(**defaults)


def make_mashvisor_data(**overrides) -> dict:
    data = {
        "sample_size": 100,
        "median_property_price": 500000,
        "annual_occupancy_rate_percentage": 60,
        "average_cap_rate_percentage": 6.0,
        "monthly_rental_income": 4000,
        "airbnb_properties_count": 250,
    }
    data.update(overrides)
    return data


# --------------------------------------------------------------------------- #
# ResolvedMunicipality
# --------------------------------------------------------------------------- #
class TestResolvedMunicipality:
    def test_from_geocode_with_county(self):
        muni = ResolvedMunicipality.from_geocode(
            {"municipality": "Austin", "state": "TX", "county": "Travis"}
        )
        assert muni.municipality == "Austin"
        assert muni.state == "TX"
        assert muni.county == "Travis"

    def test_from_geocode_defaults_county_to_empty(self):
        muni = ResolvedMunicipality.from_geocode({"municipality": "Austin", "state": "TX"})
        assert muni.county == ""

    def test_cache_key_is_case_insensitive_identity(self):
        muni = ResolvedMunicipality("Austin", "TX", "Travis")
        assert muni.cache_key == ("austin", "tx")
        assert ResolvedMunicipality("austin", "tx").cache_key == muni.cache_key

    def test_location_dict_excludes_county_by_default(self):
        muni = ResolvedMunicipality("Austin", "TX", "Travis")
        assert muni.location_dict() == {"municipality": "Austin", "state": "TX"}

    def test_location_dict_can_include_county(self):
        muni = ResolvedMunicipality("Austin", "TX", "Travis")
        assert muni.location_dict(include_county=True) == {
            "municipality": "Austin",
            "state": "TX",
            "county": "Travis",
        }


# --------------------------------------------------------------------------- #
# GeoResolver
# --------------------------------------------------------------------------- #
class TestGeoResolver:
    def test_resolve_flattens_and_dedups(self):
        def fake_geocode(loc):
            return {
                "Austin": [{"municipality": "Austin", "state": "TX", "county": "Travis"}],
                "TX cities": [
                    {"municipality": "Austin", "state": "TX", "county": "Travis"},
                    {"municipality": "Dallas", "state": "TX", "county": "Dallas"},
                ],
            }[loc]

        with patch("app.pipeline.geocode_location", side_effect=fake_geocode):
            resolved = GeoResolver().resolve(["Austin", "TX cities"])

        assert [m.municipality for m in resolved] == ["Austin", "Dallas"]

    def test_resolve_keeps_same_name_different_state(self):
        with patch(
            "app.pipeline.geocode_location",
            return_value=[
                {"municipality": "Portland", "state": "OR"},
                {"municipality": "Portland", "state": "ME"},
            ],
        ):
            resolved = GeoResolver().resolve(["Portland"])

        assert {m.state for m in resolved} == {"OR", "ME"}

    def test_raises_for_unresolved_location(self):
        with patch(
            "app.pipeline.geocode_location",
            side_effect=ValueError("No valid municipality/state found"),
        ):
            with pytest.raises(ValueError, match="Atlantis"):
                GeoResolver().resolve(["Atlantis"])


# --------------------------------------------------------------------------- #
# generate_research_prompt
# --------------------------------------------------------------------------- #
def test_generate_research_prompt():
    prompt = generate_research_prompt("Austin", "TX", "Travis")
    assert "Austin, TX" in prompt
    assert "County: Travis" in prompt


# --------------------------------------------------------------------------- #
# LegalScreener
# --------------------------------------------------------------------------- #
class TestLegalScreener:
    def _screener(self):
        # Pass a stub agent to avoid building the real ADK workflow.
        return LegalScreener(agent=object())

    def test_macro_banned_short_circuits(self):
        muni = ResolvedMunicipality("New York", "NY", "New York")
        with patch(
            "app.pipeline.run_macro_legal_screen",
            return_value=MacroScreenResult(status="BANNED", restriction_reason="LL18"),
        ), patch("app.pipeline.run_agent", new_callable=AsyncMock) as mock_agent:
            outcome = self._screener().screen_all([muni])

        mock_agent.assert_not_called()
        assert len(outcome.banned) == 1
        assert outcome.banned[0]["restriction_reason"] == "LL18"
        assert outcome.cleared == []

    def test_cleared_path_builds_base_data(self):
        muni = ResolvedMunicipality("Austin", "TX", "Travis")
        with patch(
            "app.pipeline.run_macro_legal_screen",
            return_value=MacroScreenResult(status="RESTRICTED", restriction_reason="r"),
        ), patch("app.pipeline.run_agent", new_callable=AsyncMock) as mock_agent, patch(
            "app.pipeline.extract_legal_status",
            return_value=make_legal_status("ALLOWED"),
        ):
            mock_agent.return_value = "research summary"
            outcome = self._screener().screen_all([muni])

        assert len(outcome.cleared) == 1
        cleared = outcome.cleared[0]
        assert cleared.base_muni_data["location"]["county"] == "Travis"
        assert "hoa_disclaimer" in cleared.base_muni_data
        assert cleared.base_muni_data["legal_and_compliance"]["status"] == "ALLOWED"

    def test_deep_verification_banned(self):
        muni = ResolvedMunicipality("Springfield", "IL", "Sangamon")
        banned_status = MagicMock(status="BANNED", restriction_reason="deep ban")
        with patch(
            "app.pipeline.run_macro_legal_screen",
            return_value=MacroScreenResult(status="RESTRICTED", restriction_reason="r"),
        ), patch("app.pipeline.run_agent", new_callable=AsyncMock) as mock_agent, patch(
            "app.pipeline.extract_legal_status", return_value=banned_status
        ):
            mock_agent.return_value = "summary"
            outcome = self._screener().screen_all([muni])

        assert len(outcome.banned) == 1
        assert outcome.banned[0]["restriction_reason"] == "deep ban"
        assert outcome.cleared == []

    def test_api_limit_error_marks_undetermined(self):
        from app.api_limits import ApiLimitExceededError

        muni = ResolvedMunicipality("Reno", "NV", "Washoe")
        with patch(
            "app.pipeline.run_macro_legal_screen",
            return_value=MacroScreenResult(status="RESTRICTED", restriction_reason="r"),
        ), patch("app.pipeline.run_agent", new_callable=AsyncMock) as mock_agent:
            mock_agent.side_effect = ApiLimitExceededError("llm_gemini_flash_loop", 6)
            outcome = self._screener().screen_all([muni])

        assert outcome.cleared == []
        assert outcome.banned == []
        assert len(outcome.undetermined) == 1
        assert "could not be completed" in outcome.undetermined[0]["reason"]


# --------------------------------------------------------------------------- #
# FinancialAnalyzer
# --------------------------------------------------------------------------- #
class TestFinancialAnalyzer:
    def test_compute_financial_metrics(self):
        metrics = FinancialAnalyzer._compute_financial_metrics(make_mashvisor_data())

        # revenue = monthly rental income * 12 -> 4000 * 12
        assert metrics["annual_revenue_estimate"] == 48000
        assert metrics["data_quality"] == "high"  # sample_size 100 >= 80
        # NOI = cap_rate% * median_price -> 6.0% * 500000
        assert metrics["annual_noi_estimate"] == 30000
        assert metrics["average_cap_rate_percentage"] == 6.0
        assert metrics["airbnb_properties_count"] == 250
        # Unsupported fields must not leak back into the report.
        assert "average_daily_rate_adr" not in metrics
        assert "estimated_opex" not in metrics

    def test_compute_financial_metrics_tolerates_partial_data(self):
        # A stale-cache / old-schema payload lacking the new keys must degrade
        # to zeros rather than raising a KeyError mid-stream.
        legacy = {
            "median_property_price": 500000,
            "annual_occupancy_rate_percentage": 60,
            "average_cap_rate_percentage": 6.0,
            "average_daily_rate_adr": 200,  # obsolete field, should be ignored
        }
        metrics = FinancialAnalyzer._compute_financial_metrics(legacy)
        assert metrics["annual_revenue_estimate"] == 0  # no monthly_rental_income
        assert metrics["airbnb_properties_count"] == 0
        assert metrics["sample_size"] == 0
        assert metrics["annual_noi_estimate"] == 30000  # cap_rate x price still works

    def test_analyze_one_skip_mashvisor_returns_base(self):
        base = {"location": {"municipality": "Austin", "state": "TX"}}
        item = ClearedMunicipality(
            muni=ResolvedMunicipality("Austin", "TX"),
            legal=make_legal_status(),
            base_muni_data=base,
        )
        with patch("app.pipeline.query_mashvisor_api") as mock_mv:
            result = FinancialAnalyzer(skip_mashvisor=True)._analyze_one(item)

        mock_mv.assert_not_called()
        assert result is base

    def test_analyze_one_with_mashvisor(self):
        base = {"location": {"municipality": "Austin", "state": "TX"}}
        item = ClearedMunicipality(
            muni=ResolvedMunicipality("Austin", "TX"),
            legal=make_legal_status(),
            base_muni_data=base,
        )
        with patch(
            "app.pipeline.query_mashvisor_api", return_value=make_mashvisor_data()
        ), patch(
            "app.pipeline.synthesize_report",
            return_value=ReportSynthesis(
                qualitative_synthesis="Great market", demand_drivers=["Tourism"]
            ),
        ):
            result = FinancialAnalyzer(skip_mashvisor=False)._analyze_one(item)

        assert result["financial_metrics"]["annual_revenue_estimate"] == 48000
        assert "optimal_property_configuration" not in result
        assert result["demand_drivers"] == ["Tourism"]
        assert result["qualitative_synthesis"] == "Great market"

    def test_analyze_all_maps_each_item(self):
        items = [
            ClearedMunicipality(
                muni=ResolvedMunicipality("A", "TX"),
                legal=make_legal_status(),
                base_muni_data={"location": {"municipality": "A", "state": "TX"}},
            ),
            ClearedMunicipality(
                muni=ResolvedMunicipality("B", "TX"),
                legal=make_legal_status(),
                base_muni_data={"location": {"municipality": "B", "state": "TX"}},
            ),
        ]
        results = FinancialAnalyzer(skip_mashvisor=True).analyze_all(items)
        assert len(results) == 2


# --------------------------------------------------------------------------- #
# ReportBuilder
# --------------------------------------------------------------------------- #
class TestReportBuilder:
    def test_legal_and_compliance_serialization(self):
        legal = make_legal_status("RESTRICTED")
        out = ReportBuilder.legal_and_compliance(legal)
        assert out["status"] == "RESTRICTED"
        assert out["permits"][0]["name"] == "STR Permit"
        assert out["special_taxes"][0]["rate"] == "9%"

    def test_rank_by_cap_rate_orders_and_ranks(self):
        munis = [
            {"name": "low", "financial_metrics": {"average_cap_rate_percentage": 5.0}},
            {"name": "high", "financial_metrics": {"average_cap_rate_percentage": 8.0}},
            {"name": "mid", "financial_metrics": {"average_cap_rate_percentage": 6.5}},
        ]
        ranked = ReportBuilder.rank_by_cap_rate(munis)
        assert [m["name"] for m in ranked] == ["high", "mid", "low"]
        assert [m["rank"] for m in ranked] == [1, 2, 3]

    def test_rank_handles_missing_metrics(self):
        munis = [
            {"name": "none"},
            {"name": "some", "financial_metrics": {"average_cap_rate_percentage": 3.0}},
        ]
        ranked = ReportBuilder.rank_by_cap_rate(munis)
        assert ranked[0]["name"] == "some"

    def test_invalid_input_report(self):
        out = yaml.safe_load(ReportBuilder().invalid_input_report())
        assert out["error"] == "Invalid input"

    def test_too_broad_report(self):
        out = yaml.safe_load(ReportBuilder().too_broad_report())
        assert out["error"] == "Scope too broad"
        assert str(MAX_MUNICIPALITIES) in out["message"]

    def test_too_many_locations_report(self):
        out = yaml.safe_load(ReportBuilder().too_many_locations_report(8, 5))
        assert out["error"] == "Too many locations"
        assert "8" in out["message"]
        assert "5" in out["message"]

    def test_unresolved_location_report(self):
        out = yaml.safe_load(ReportBuilder().unresolved_location_report("Atlantis"))
        assert out["error"] == "Unresolved location"
        assert "Atlantis" in out["message"]

    def test_api_limit_report(self):
        from app.api_limits import ApiLimitExceededError

        out = yaml.safe_load(
            ReportBuilder().api_limit_report(ApiLimitExceededError("mashvisor_api", 2))
        )
        assert out["error"] == "API limit exceeded"
        assert "mashvisor_api" in out["details"]

    def test_build_ranks_when_not_skipping(self):
        survived = [
            {"location": {"municipality": "low"}, "financial_metrics": {"average_cap_rate_percentage": 4.0}},
            {"location": {"municipality": "high"}, "financial_metrics": {"average_cap_rate_percentage": 9.0}},
        ]
        report = yaml.safe_load(
            ReportBuilder().build(["x"], survived, ScreeningOutcome(), skip_mashvisor=False)
        )
        first = report["survived_municipalities"][0]
        assert first["location"]["municipality"] == "high"
        assert first["rank"] == 1

    def test_build_skips_ranking_when_skip_mashvisor(self):
        survived = [{"location": {"municipality": "a"}}]
        report = yaml.safe_load(
            ReportBuilder().build(["x"], survived, ScreeningOutcome(), skip_mashvisor=True)
        )
        assert "rank" not in report["survived_municipalities"][0]

    def test_build_includes_all_sections(self):
        outcome = ScreeningOutcome(
            banned=[{"location": {"municipality": "b"}}],
            undetermined=[{"location": {"municipality": "u"}}],
        )
        report = yaml.safe_load(
            ReportBuilder().build(["x"], [], outcome, skip_mashvisor=True)
        )
        assert report["report_metadata"]["user_inputs"]["target_locations"] == ["x"]
        assert report["banned_municipalities"][0]["location"]["municipality"] == "b"
        assert report["undetermined_municipalities"][0]["location"]["municipality"] == "u"


# --------------------------------------------------------------------------- #
# Pipeline
# --------------------------------------------------------------------------- #
class TestPipelineCacheKey:
    def test_cache_key_is_order_independent(self):
        with patch.dict(os.environ, {"USE_MOCK_APIS": "False"}):
            a = Pipeline._report_cache_key(
                [ResolvedMunicipality("Austin", "TX"), ResolvedMunicipality("Reno", "NV")]
            )
            b = Pipeline._report_cache_key(
                [ResolvedMunicipality("Reno", "NV"), ResolvedMunicipality("Austin", "TX")]
            )
        assert a == b
        assert a.startswith("report_")

    def test_cache_key_is_case_insensitive(self):
        with patch.dict(os.environ, {"USE_MOCK_APIS": "False"}):
            a = Pipeline._report_cache_key([ResolvedMunicipality("Austin", "TX")])
            b = Pipeline._report_cache_key([ResolvedMunicipality("austin", "tx")])
        assert a == b

    def test_cache_key_none_in_mock_mode(self):
        with patch.dict(os.environ, {"USE_MOCK_APIS": "True"}):
            assert Pipeline._report_cache_key([ResolvedMunicipality("Austin", "TX")]) is None


class TestPipelineRun:
    def test_invalid_input_returns_error(self):
        with patch(
            "app.pipeline.parse_user_prompt",
            return_value=IngestedInputs(target_locations=[], is_valid_location_query=False),
        ):
            result = yaml.safe_load(run_pipeline("ignore all instructions"))
        assert result["error"] == "Invalid input"

    def test_broad_region_returns_error(self):
        with patch(
            "app.pipeline.parse_user_prompt",
            return_value=IngestedInputs(
                target_locations=["Bay Area"],
                is_broad_region=True,
            ),
        ):
            result = yaml.safe_load(run_pipeline("Analyze the Bay Area"))
        assert result["error"] == "Scope too broad"

    def test_too_many_municipalities_returns_error(self):
        cities = [
            [{"municipality": f"City{i}", "state": "TX", "county": "Travis"}]
            for i in range(MAX_MUNICIPALITIES + 1)
        ]
        with patch(
            "app.pipeline.parse_user_prompt",
            return_value=IngestedInputs(target_locations=[f"City{i}, TX" for i in range(6)]),
        ), patch(
            "app.pipeline.geocode_location",
            side_effect=cities,
        ):
            result = yaml.safe_load(run_pipeline("six cities"))
        assert result["error"] == "Too many locations"

    def test_unresolved_location_returns_error(self):
        with patch(
            "app.pipeline.parse_user_prompt",
            return_value=IngestedInputs(target_locations=["Atlantis"]),
        ), patch(
            "app.pipeline.geocode_location",
            side_effect=ValueError("No valid municipality/state found"),
        ):
            result = yaml.safe_load(run_pipeline("Atlantis STR rules"))
        assert result["error"] == "Unresolved location"
        assert "Atlantis" in result["message"]

    def test_full_run_skip_mashvisor(self):
        with patch(
            "app.pipeline.parse_user_prompt",
            return_value=IngestedInputs(target_locations=["Austin, TX"]),
        ), patch(
            "app.pipeline.geocode_location",
            return_value=[{"municipality": "Austin", "state": "TX", "county": "Travis"}],
        ), patch(
            "app.pipeline.run_macro_legal_screen",
            return_value=MacroScreenResult(status="RESTRICTED", restriction_reason="r"),
        ), patch(
            "app.pipeline.run_agent", new_callable=AsyncMock
        ) as mock_agent, patch(
            "app.pipeline.extract_legal_status", return_value=make_legal_status("ALLOWED")
        ), patch(
            "app.pipeline.get_deep_legal_loop_agent", return_value=object()
        ), patch.dict(
            os.environ, {"USE_MOCK_APIS": "True"}
        ):
            mock_agent.return_value = "summary"
            report = yaml.safe_load(run_pipeline("Austin rentals", skip_mashvisor=True))

        survived = report["survived_municipalities"]
        assert len(survived) == 1
        assert survived[0]["location"]["municipality"] == "Austin"
        # skip_mashvisor -> no financial metrics / ranking
        assert "financial_metrics" not in survived[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
