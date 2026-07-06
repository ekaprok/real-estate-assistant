import os
import yaml
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from app.api_limits import init_api_counts, get_current_counts, ApiLimitExceededError, API_LIMITS
from app.integrations import geocode_location, query_mashvisor_api
from app.llm import (
    parse_user_prompt,
    run_macro_legal_screen,
    get_deep_legal_loop_agent,
    extract_legal_status,
    synthesize_report
)
from app.app_utils.finance import (
    determine_data_quality,
    calculate_annual_revenue,
    calculate_opex_breakdown,
    calculate_noi,
    calculate_cap_rate,
    calculate_composite_score
)

from app.app_utils.cache import with_cache, get_cached_response, set_cached_response

@with_cache("agent_run")
async def run_agent(agent, prompt: str) -> str:
    """Helper to run the DeepLegalLoopAgent ReAct loop asynchronously via Runner."""
    session_service = InMemorySessionService()
    session = await session_service.create_session(user_id="pipeline_user", app_name="pipeline")
    runner = Runner(agent=agent, session_service=session_service, app_name="pipeline")

    new_message = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=prompt)]
    )

    events = []
    async for event in runner.run_async(
        new_message=new_message,
        user_id="pipeline_user",
        session_id=session.id,
    ):
        events.append(event)

    response_text = ""
    for event in events:
        if event.error_code:
            if event.error_code == "ApiLimitExceededError":
                # Find current count if possible or use limit from config
                limit = API_LIMITS.get("llm_gemini_flash_loop", 10)
                raise ApiLimitExceededError("llm_gemini_flash_loop", limit)
            raise RuntimeError(f"Agent execution failed: {event.error_message} ({event.error_code})")
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    response_text += part.text

    final_summary = session.state.get("final_research_summary")
    if final_summary:
        return str(final_summary)

    return response_text


def generate_research_prompt(municipality: str, state: str, county: str) -> str:
    return (
        f"Research the zoning laws and short term rental (STR) regulations for "
        f"{municipality}, {state} (County: {county})."
    )


def run_pipeline(user_prompt: str) -> str:
    """Runs the 5-step real estate analysis pipeline deterministically.

    Enforces API call limits and handles mock fallbacks. Returns the YAML report.
    """
    # 1. Initialize API call counts in this context
    logger.info(f"Starting pipeline with user prompt: '{user_prompt}'")
    init_api_counts()

    try:
        # Step 1: Ingestion & Parse prompt
        inputs = parse_user_prompt(user_prompt)

        logger.info(f"Step 1: Parsed inputs -> locations: {inputs.target_locations}")

        # Step 1.5: Geographic Resolution
        resolved_municipalities = []
        seen_keys = set()
        logger.info("Step 1.5: Performing geographic resolution/geocoding...")
        for loc in inputs.target_locations:
            resolved_list = geocode_location(loc)
            for res in resolved_list:
                key = (res["municipality"], res["state"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    resolved_municipalities.append(res)
        logger.info(f"Resolved municipalities to process: {resolved_municipalities}")

        # Check Final Report Cache based on resolved parameters
        # Sort municipalities to guarantee consistent order
        muni_keys = sorted([(m["municipality"].lower(), m["state"].lower()) for m in resolved_municipalities])
        canonical_key_data = {
            "municipalities": muni_keys,
        }
        import json
        import hashlib
        key_str = json.dumps(canonical_key_data, sort_keys=True)
        args_hash = hashlib.md5(key_str.encode("utf-8")).hexdigest()

        use_mock = os.environ.get("USE_MOCK_APIS", "False").lower() == "true"
        cache_key = f"mock_report_{args_hash}" if use_mock else f"report_{args_hash}"

        cached = get_cached_response(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for report key {cache_key}")
            logger.info(f"Final Report:\n{cached}")
            return cached

        logger.info(f"Cache miss for report key {cache_key}")

        # Step 2: Macro Legal Screen & Step 3: Deep Legal Loop
        surviving_municipalities = []
        banned_municipalities = []

        deep_research_agent = get_deep_legal_loop_agent()

        for muni in resolved_municipalities:
            name = muni["municipality"]
            state = muni["state"]
            county = muni.get("county", "")

            # Step 2: Macro Legal Screen
            logger.info(f"Step 2: Running macro legal screen for {name}, {state}...")
            macro_res = run_macro_legal_screen(name, state)
            logger.info(f"Macro legal screen result for {name}, {state}: {macro_res.status}")

            if macro_res.status == "BANNED":
                logger.info(f"Municipality {name}, {state} is BANNED (Reason: {macro_res.restriction_reason})")
                banned_municipalities.append({
                    "location": {
                        "municipality": name,
                        "state": state
                    },
                    "restriction_reason": macro_res.restriction_reason
                })
                continue

            # Step 3: Deep Legal Verification (LoopAgent ReAct)
            research_prompt = generate_research_prompt(name, state, county)
            logger.info(f"Step 3: Executing Deep Legal verification loop for {name}, {state}...")
            research_summary = run_agent(deep_research_agent, research_prompt)

            # Extract structured LegalStatus
            legal_status = extract_legal_status(name, state, research_summary)
            logger.info(f"Deep Legal verification status for {name}, {state}: {legal_status.status}")

            if legal_status.status == "BANNED":
                logger.info(f"Municipality {name}, {state} failed deep verification (Reason: {legal_status.restriction_reason})")
                banned_municipalities.append({
                    "location": {
                        "municipality": name,
                        "state": state
                    },
                    "restriction_reason": legal_status.restriction_reason
                })
                continue

            logger.info(f"Municipality {name}, {state} passed legal verification. Adding to surviving list.")
            surviving_municipalities.append({
                "muni": muni,
                "legal": legal_status
            })

        # Step 4: ROI Ranking & Optimal Configuration (Mashvisor)
        survived_municipalities = []
        for index, item in enumerate(surviving_municipalities):
            muni = item["muni"]
            name = muni["municipality"]
            state = muni["state"]
            legal = item["legal"]

            # Fetch Mashvisor financial data
            logger.info(f"Step 4: Querying Mashvisor financial metrics for {name}, {state}...")
            mv_data = query_mashvisor_api(name, state)

            # Financial calculations
            sample_size = mv_data["sample_size"]
            data_quality = determine_data_quality(sample_size)

            median_price = mv_data["median_property_price"]
            adr = mv_data["average_daily_rate_adr"]
            occ = mv_data["annual_occupancy_rate_percentage"]

            annual_revenue = calculate_annual_revenue(adr, occ)

            # OpEx calculations
            opex_pct = mv_data["estimated_opex"]
            opex_breakdown, total_annual_opex, total_opex_pct = calculate_opex_breakdown(annual_revenue, opex_pct)

            annual_noi = calculate_noi(annual_revenue, total_annual_opex)
            cap_rate = calculate_cap_rate(annual_noi, median_price)

            # Score Calculation (cap_rate_yield = 60%, legal_friendliness = 40%)
            composite_score = calculate_composite_score(cap_rate, legal)
            logger.info(f"Calculated composite score for {name}, {state}: {composite_score} (Cap Rate: {cap_rate}%, Legal Status: {legal.status})")

            # Step 5: Synthesis & Demand Drivers
            logger.info(f"Step 5: Synthesizing report for {name}, {state}...")
            calculated_data = {
                "municipality": name,
                "state": state,
                "cap_rate": cap_rate,
                "legal_status": legal.status,
                "restriction_reason": legal.restriction_reason
            }
            synthesis_res = synthesize_report(name, state, calculated_data)

            # Construct survived muni item
            survived_municipalities.append({
                "location": {
                    "municipality": name,
                    "state": state,
                    "county": muni.get("county", "")
                },
                "municipal_str_score": composite_score,
                "score_weights": {
                    "cap_rate_yield": 60,
                    "legal_friendliness": 40
                },
                "legal_and_compliance": {
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
                            "application_url": p.application_url
                        } for p in legal.permits
                    ],
                    "special_taxes": [
                        {
                            "name": t.name,
                            "rate": t.rate,
                            "description": t.description
                        } for t in legal.special_taxes
                    ],
                    "regulatory_trajectory_risk": legal.regulatory_trajectory_risk,
                    "summary_of_restrictions": legal.summary_of_restrictions
                },
                "hoa_disclaimer": "Resort and planned communities in this market commonly carry HOAs whose CC&Rs may restrict STRs. This system verifies only government zoning/law — confirm HOA rules independently before closing.",
                "financial_metrics": {
                    "sample_size": sample_size,
                    "data_quality": data_quality,
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
                        "breakdown": opex_breakdown
                    }
                },
                "optimal_property_configuration": {
                    "property_type": mv_data["optimal_config"]["property_type"],
                    "bedrooms": mv_data["optimal_config"]["bedrooms"],
                    "bathrooms": mv_data["optimal_config"]["bathrooms"],
                    "accommodates": mv_data["optimal_config"]["accommodates"]
                },
                "demand_drivers": synthesis_res.demand_drivers,
                "qualitative_synthesis": synthesis_res.qualitative_synthesis
            })

        # Sort survived municipalities by municipal_str_score descending
        survived_municipalities.sort(key=lambda x: x["municipal_str_score"], reverse=True)
        # Assign rank based on sorted order
        for idx, rec in enumerate(survived_municipalities):
            rec["rank"] = idx + 1

        # Build final report yaml
        report = {
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "user_inputs": {
                    "target_locations": inputs.target_locations
                },
                "data_sources": {
                    "financial_data_source": "Mashvisor",
                    "legal_data_source": "Serper.dev web search + municipal / Municode / eCode360 / AmLegal scrape"
                }
            },
            "survived_municipalities": survived_municipalities,
            "banned_municipalities": banned_municipalities
        }

        report_yaml = yaml.dump(report, default_flow_style=False, sort_keys=False)
        logger.info(f"Final Report:\n{report_yaml}")

        # Save to cache
        set_cached_response(cache_key, report_yaml)

        logger.info(f"Pipeline completed successfully. API call counts: {get_current_counts()}")
        return report_yaml

    except ApiLimitExceededError as e:
        logger.error(f"Pipeline aborted: API limit exceeded: {e}")
        # Exceeded API limits - immediately return error output
        report = {
            "error": "API limit exceeded",
            "details": str(e),
            "current_counts": get_current_counts()
        }
        report_yaml = yaml.dump(report, default_flow_style=False, sort_keys=False)
        logger.info(f"Final Report:\n{report_yaml}")
        return report_yaml
