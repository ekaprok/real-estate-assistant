"""Deterministic 5-step short-term rental analysis pipeline.

The pipeline is split into small, single-responsibility classes:

* :class:`GeoResolver`      - Step 1.5: geocode user locations into municipalities.
* :class:`LegalScreener`    - Steps 2-3: macro screen + deep legal verification.
* :class:`FinancialAnalyzer`- Steps 4-5: Mashvisor financials + synthesis.
* :class:`ReportBuilder`    - assembles/serializes the final YAML report.
* :class:`Pipeline`         - orchestrates the stages, caching and API limits.
"""

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime

import yaml
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from app.api_limits import (
    ApiLimitExceededError,
    _get_limit,
    get_current_counts,
    init_api_counts,
)
from app.app_utils.cache import get_cached_response, set_cached_response, with_cache
from app.app_utils.finance import (
    calculate_annual_revenue,
    calculate_cap_rate,
    calculate_noi,
    calculate_opex_breakdown,
    determine_data_quality,
)
from app.integrations import geocode_location, query_mashvisor_api
from app.llm import (
    LegalStatus,
    extract_legal_status,
    get_deep_legal_loop_agent,
    parse_user_prompt,
    run_macro_legal_screen,
    synthesize_report,
)
from app.mock_handlers import _use_mock_apis, mock_research_summary

logger = logging.getLogger(__name__)

HOA_DISCLAIMER = (
    "Resort and planned communities in this market commonly carry HOAs whose "
    "CC&Rs may restrict STRs. This system verifies only government zoning/law "
    "— confirm HOA rules independently before closing."
)

MAX_MUNICIPALITIES = 5


@with_cache("agent_run")
async def run_agent(agent, prompt: str) -> str:
    """Run the DeepLegalLoopAgent ReAct loop asynchronously via the ADK Runner."""
    if _use_mock_apis():
        return mock_research_summary(prompt)

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        user_id="pipeline_user", app_name="pipeline"
    )
    runner = Runner(agent=agent, session_service=session_service, app_name="pipeline")

    new_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=prompt)],
    )

    response_text = ""
    async for event in runner.run_async(
        new_message=new_message,
        user_id="pipeline_user",
        session_id=session.id,
    ):
        if event.error_code:
            if event.error_code == "ApiLimitExceededError":
                raise ApiLimitExceededError(
                    "llm_gemini_flash_loop",
                    _get_limit("llm_gemini_flash_loop"),
                )
            raise RuntimeError(
                f"Agent execution failed: {event.error_message} ({event.error_code})"
            )
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    refreshed = await session_service.get_session(
        app_name="pipeline",
        user_id="pipeline_user",
        session_id=session.id,
    )
    if refreshed and refreshed.state.get("research_findings"):
        return str(refreshed.state["research_findings"])

    return response_text


def generate_research_prompt(municipality: str, state: str, county: str) -> str:
    return (
        f"Research the zoning laws and short term rental (STR) regulations for "
        f"{municipality}, {state} (County: {county})."
    )


@dataclass(frozen=True)
class ResolvedMunicipality:
    """A geocoded municipality that the pipeline will analyze."""

    municipality: str
    state: str
    county: str = ""

    @classmethod
    def from_geocode(cls, data: dict) -> "ResolvedMunicipality":
        return cls(
            municipality=data["municipality"],
            state=data["state"],
            county=data.get("county", ""),
        )

    @property
    def cache_key(self) -> tuple[str, str]:
        """Canonical case-insensitive identity (municipality + state).

        Used both for de-duplication and for building report cache keys.
        """
        return (self.municipality.lower(), self.state.lower())

    def location_dict(self, include_county: bool = False) -> dict:
        loc = {"municipality": self.municipality, "state": self.state}
        if include_county:
            loc["county"] = self.county
        return loc


@dataclass
class ClearedMunicipality:
    """A municipality that passed legal screening and awaits financial analysis."""

    muni: ResolvedMunicipality
    legal: LegalStatus
    base_muni_data: dict


@dataclass
class ScreeningOutcome:
    """Aggregated result of legal screening across all municipalities."""

    cleared: list[ClearedMunicipality] = field(default_factory=list)
    banned: list[dict] = field(default_factory=list)
    undetermined: list[dict] = field(default_factory=list)


class GeoResolver:
    """Step 1.5: resolve user locations into de-duplicated municipalities."""

    def resolve(self, target_locations: list[str]) -> list[ResolvedMunicipality]:
        resolved: list[ResolvedMunicipality] = []
        seen: set[tuple[str, str]] = set()
        logger.info("Step 1.5: Performing geographic resolution/geocoding...")
        for loc in target_locations:
            try:
                for res in geocode_location(loc):
                    muni = ResolvedMunicipality.from_geocode(res)
                    if muni.cache_key not in seen:
                        seen.add(muni.cache_key)
                        resolved.append(muni)
            except ValueError as e:
                logger.warning(f"Could not geocode location '{loc}': {e}")
                raise ValueError(loc) from e
        logger.info(f"Resolved municipalities to process: {resolved}")
        return resolved


class LegalScreener:
    """Steps 2-3: macro legal screen followed by deep legal verification.

    A single deep-research agent is instantiated once and reused for every
    municipality, matching the original per-run behaviour.
    """

    def __init__(self, agent=None):
        self._agent = agent if agent is not None else get_deep_legal_loop_agent()

    def screen_all(self, municipalities: list[ResolvedMunicipality]) -> ScreeningOutcome:
        outcome = ScreeningOutcome()
        for muni in municipalities:
            self._screen_one(muni, outcome)
        return outcome

    def _screen_one(self, muni: ResolvedMunicipality, outcome: ScreeningOutcome) -> None:
        name, state = muni.municipality, muni.state
        try:
            logger.info(f"Step 2: Running macro legal screen for {name}, {state}...")
            macro_res = run_macro_legal_screen(name, state)
            logger.info(f"Macro legal screen result for {name}, {state}: {macro_res.status}")

            if macro_res.status == "BANNED":
                logger.info(
                    f"Municipality {name}, {state} is BANNED "
                    f"(Reason: {macro_res.restriction_reason})"
                )
                outcome.banned.append(
                    {
                        "location": muni.location_dict(),
                        "restriction_reason": macro_res.restriction_reason,
                    }
                )
                return

            research_prompt = generate_research_prompt(name, state, muni.county)
            logger.info(f"Step 3: Executing Deep Legal verification loop for {name}, {state}...")
            research_summary = asyncio.run(run_agent(self._agent, research_prompt))

            legal_status = extract_legal_status(name, state, research_summary)
            logger.info(
                f"Deep Legal verification status for {name}, {state}: {legal_status.status}"
            )

            if legal_status.status == "BANNED":
                logger.info(
                    f"Municipality {name}, {state} failed deep verification "
                    f"(Reason: {legal_status.restriction_reason})"
                )
                outcome.banned.append(
                    {
                        "location": muni.location_dict(),
                        "restriction_reason": legal_status.restriction_reason,
                    }
                )
                return

            logger.info(
                f"Municipality {name}, {state} passed legal verification. "
                "Adding to surviving list."
            )
            base_muni_data = {
                "location": muni.location_dict(include_county=True),
                "legal_and_compliance": ReportBuilder.legal_and_compliance(legal_status),
                # TODO: Define a proper HOA disclaimer instead of a static string
                "hoa_disclaimer": HOA_DISCLAIMER,
            }
            outcome.cleared.append(
                ClearedMunicipality(muni=muni, legal=legal_status, base_muni_data=base_muni_data)
            )
        except (ApiLimitExceededError, RuntimeError) as e:
            logger.warning(
                f"Legal verification could not be completed for {name}, {state}: {e}"
            )
            outcome.undetermined.append(
                {
                    "location": muni.location_dict(),
                    "reason": f"Legal verification could not be completed: {e}",
                }
            )


class FinancialAnalyzer:
    """Steps 4-5: Mashvisor financial metrics + qualitative synthesis."""

    def __init__(self, skip_mashvisor: bool):
        self.skip_mashvisor = skip_mashvisor

    def analyze_all(self, cleared: list[ClearedMunicipality]) -> list[dict]:
        return [self._analyze_one(item) for item in cleared]

    def _analyze_one(self, item: ClearedMunicipality) -> dict:
        muni, legal, base_muni_data = item.muni, item.legal, item.base_muni_data
        name, state = muni.municipality, muni.state

        if self.skip_mashvisor:
            logger.info(f"Step 4: Skipping Mashvisor API for {name}, {state}...")
            return base_muni_data

        logger.info(f"Step 4: Querying Mashvisor financial metrics for {name}, {state}...")
        mv_data = query_mashvisor_api(name, state)
        financial_metrics = self._compute_financial_metrics(mv_data)

        logger.info(f"Step 5: Synthesizing report for {name}, {state}...")
        calculated_data = {
            "municipality": name,
            "state": state,
            "cap_rate": financial_metrics["average_cap_rate_percentage"],
            "legal_status": legal.status,
            "restriction_reason": legal.restriction_reason,
        }
        synthesis_res = synthesize_report(name, state, calculated_data)

        return {
            **base_muni_data,
            "financial_metrics": financial_metrics,
            "optimal_property_configuration": {
                "property_type": mv_data["optimal_config"]["property_type"],
                "bedrooms": mv_data["optimal_config"]["bedrooms"],
                "bathrooms": mv_data["optimal_config"]["bathrooms"],
                "accommodates": mv_data["optimal_config"]["accommodates"],
            },
            "demand_drivers": synthesis_res.demand_drivers,
            "qualitative_synthesis": synthesis_res.qualitative_synthesis,
        }

    @staticmethod
    def _compute_financial_metrics(mv_data: dict) -> dict:
        sample_size = mv_data["sample_size"]
        median_price = mv_data["median_property_price"]
        adr = mv_data["average_daily_rate_adr"]
        occ = mv_data["annual_occupancy_rate_percentage"]

        annual_revenue = calculate_annual_revenue(adr, occ)
        opex_breakdown, total_annual_opex, total_opex_pct = calculate_opex_breakdown(
            annual_revenue, mv_data["estimated_opex"]
        )
        annual_noi = calculate_noi(annual_revenue, total_annual_opex)
        cap_rate = calculate_cap_rate(annual_noi, median_price)

        return {
            "sample_size": sample_size,
            "data_quality": determine_data_quality(sample_size),
            "median_property_price": median_price,
            "average_daily_rate_adr": adr,
            "annual_occupancy_rate_percentage": occ,
            "annual_revenue_estimate": annual_revenue,
            "annual_noi_estimate": annual_noi,
            "average_cap_rate_percentage": cap_rate,
            "active_listings_count": mv_data["active_listings_count"],
            "listings_growth_yoy_percentage": mv_data["listings_growth_yoy_percentage"],
            "revenue_growth_yoy_percentage": mv_data["revenue_growth_yoy_percentage"],
            "seasonality_summary": mv_data["seasonality_summary"],
            "estimated_opex": {
                "total_annual": total_annual_opex,
                "total_percentage_of_revenue": total_opex_pct,
                "breakdown": opex_breakdown,
            },
        }


class ReportBuilder:
    """Serializes pipeline results into the final YAML report."""

    @staticmethod
    def legal_and_compliance(legal: LegalStatus) -> dict:
        return {
            "status": legal.status,
            "restriction_reason": legal.restriction_reason,
            "eligible_zones_summary": legal.eligible_zones_summary,
            "primary_residence_required": legal.primary_residence_required,
            "minimum_stay_days": legal.minimum_stay_days,
            "permit_cap_exists": legal.permit_cap_exists,
            "permits": [
                {
                    "name": p.name,
                    "process_summary": p.process_summary,
                    "application_url": p.application_url,
                }
                for p in legal.permits
            ],
            "special_taxes": [
                {"name": t.name, "rate": t.rate, "description": t.description}
                for t in legal.special_taxes
            ],
            "regulatory_trajectory_risk": legal.regulatory_trajectory_risk,
            "summary_of_restrictions": legal.summary_of_restrictions,
        }

    @staticmethod
    def rank_by_cap_rate(municipalities: list[dict]) -> list[dict]:
        """Sort municipalities by cap rate (desc) and assign 1-based ranks."""
        ranked = sorted(
            municipalities,
            key=lambda x: x.get("financial_metrics", {}).get(
                "average_cap_rate_percentage", 0
            ),
            reverse=True,
        )
        for idx, rec in enumerate(ranked):
            rec["rank"] = idx + 1
        return ranked

    @staticmethod
    def _dump(report: dict) -> str:
        return yaml.dump(report, default_flow_style=False, sort_keys=False)

    def invalid_input_report(self) -> str:
        return self._dump(
            {
                "error": "Invalid input",
                "message": (
                    "Please provide valid target locations to analyze short-term "
                    "rental rules, such as 'Austin, TX'."
                ),
            }
        )

    def too_broad_report(self) -> str:
        return self._dump(
            {
                "error": "Scope too broad",
                "message": (
                    "The region you specified is too broad for a single analysis. "
                    f"Please name up to {MAX_MUNICIPALITIES} specific cities or towns."
                ),
            }
        )

    def too_many_locations_report(self, count: int, limit: int) -> str:
        return self._dump(
            {
                "error": "Too many locations",
                "message": (
                    f"You requested analysis for {count} municipalities, but this "
                    f"system is limited to {limit} per request. Please narrow your "
                    "list to your top priorities."
                ),
            }
        )

    def unresolved_location_report(self, location: str) -> str:
        return self._dump(
            {
                "error": "Unresolved location",
                "message": (
                    f"Could not find a valid municipality for '{location}'. "
                    "Please provide a specific city and state, such as 'Austin, TX'."
                ),
            }
        )

    def api_limit_report(self, error: ApiLimitExceededError) -> str:
        report_yaml = self._dump(
            {
                "error": "API limit exceeded",
                "details": str(error),
                "current_counts": get_current_counts(),
            }
        )
        logger.info(f"Final Report:\n{report_yaml}")
        return report_yaml

    def build(
        self,
        target_locations: list[str],
        survived: list[dict],
        outcome: ScreeningOutcome,
        skip_mashvisor: bool,
    ) -> str:
        if not skip_mashvisor:
            survived = self.rank_by_cap_rate(survived)

        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "user_inputs": {"target_locations": target_locations},
                "data_sources": {
                    "financial_data_source": "Mashvisor",
                    "legal_data_source": (
                        "Serper.dev web search + municipal / Municode / eCode360 / "
                        "AmLegal scrape"
                    ),
                },
            },
            "survived_municipalities": survived,
            "banned_municipalities": outcome.banned,
            "undetermined_municipalities": outcome.undetermined,
        }

        report_yaml = self._dump(report)
        logger.info(f"Final Report:\n{report_yaml}")
        return report_yaml


class Pipeline:
    """Orchestrates the deterministic 5-step analysis pipeline."""

    def __init__(self, skip_mashvisor: bool):
        self.skip_mashvisor = skip_mashvisor

    def run(self, user_prompt: str) -> str:
        logger.info(f"Starting pipeline with user prompt: '{user_prompt}'")
        # Step 1: initialize per-run API counters.
        init_api_counts()

        report_builder = ReportBuilder()
        try:
            # Step 1: ingestion & prompt parsing.
            inputs = parse_user_prompt(user_prompt)
            if not inputs.is_valid_location_query or not inputs.target_locations:
                logger.warning(
                    f"Invalid location query or no locations found: {user_prompt}"
                )
                return report_builder.invalid_input_report()

            logger.info(f"Step 1: Parsed inputs -> locations: {inputs.target_locations}")

            if inputs.is_broad_region:
                logger.warning(
                    f"Broad region query rejected before geocoding: {user_prompt}"
                )
                return report_builder.too_broad_report()

            # Step 1.5: geographic resolution.
            try:
                resolved = GeoResolver().resolve(inputs.target_locations)
            except ValueError as e:
                logger.warning(f"Unresolved location during geocoding: {e}")
                return report_builder.unresolved_location_report(str(e))

            if len(resolved) > MAX_MUNICIPALITIES:
                logger.warning(
                    f"Too many municipalities resolved ({len(resolved)} > {MAX_MUNICIPALITIES})"
                )
                return report_builder.too_many_locations_report(
                    len(resolved), MAX_MUNICIPALITIES
                )

            init_api_counts(len(resolved), reset=False)

            # Report-level cache lookup based on resolved parameters.
            # TODO: Re-enable report caching once cache invalidation strategy is defined.
            # cache_key = self._report_cache_key(resolved)
            # if cache_key is not None:
            #     cached = get_cached_response(cache_key)
            #     if cached is not None:
            #         logger.info(f"Cache hit for report key {cache_key}")
            #         logger.info(f"Final Report:\n{cached}")
            #         return cached
            #     logger.info(f"Cache miss for report key {cache_key}")

            # Steps 2-3: legal screening.
            outcome = LegalScreener().screen_all(resolved)

            # Steps 4-5: financial analysis + synthesis.
            survived = FinancialAnalyzer(self.skip_mashvisor).analyze_all(outcome.cleared)

            # Assemble the report.
            report_yaml = report_builder.build(
                inputs.target_locations, survived, outcome, self.skip_mashvisor
            )

            # TODO: Re-enable report caching once cache invalidation strategy is defined.
            # if cache_key is not None:
            #     set_cached_response(cache_key, report_yaml)

            logger.info(
                f"Pipeline completed successfully. API call counts: {get_current_counts()}"
            )
            return report_yaml

        except ApiLimitExceededError as e:
            logger.error(f"Pipeline aborted: API limit exceeded: {e}")
            return report_builder.api_limit_report(e)

    @staticmethod
    def _report_cache_key(resolved: list[ResolvedMunicipality]) -> str | None:
        """Compute a deterministic report cache key, or None when mocks are active."""
        if _use_mock_apis():
            return None
        muni_keys = sorted(m.cache_key for m in resolved)
        key_str = json.dumps({"municipalities": muni_keys}, sort_keys=True)
        args_hash = hashlib.md5(key_str.encode("utf-8")).hexdigest()
        return f"report_{args_hash}"


def run_pipeline(user_prompt: str, skip_mashvisor: bool | None = None) -> str:
    """Runs the 5-step real estate analysis pipeline deterministically.

    Enforces API call limits and handles mock fallbacks. Returns the YAML report.
    """
    if skip_mashvisor is None:
        skip_mashvisor = os.environ.get("SKIP_MASHVISOR", "False").lower() == "true"
    return Pipeline(skip_mashvisor=skip_mashvisor).run(user_prompt)
