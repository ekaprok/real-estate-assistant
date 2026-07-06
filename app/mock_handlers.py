import os
from pydantic import BaseModel

def _use_mock_apis() -> bool:
    return os.environ.get("USE_MOCK_APIS", "False").lower() == "true"

def mock_research_summary(prompt: str) -> str:
    """Return canned deep-research text in mock mode (avoids live ADK/Gemini loop)."""
    try:
        from tests.mocks.tools_mocks import MOCK_PAGES
    except ImportError:
        MOCK_PAGES = {}

    prompt_lower = prompt.lower()
    for url, text in MOCK_PAGES.items():
        host = url.split("//")[-1].split("/")[0].replace("www.", "")
        city_token = host.split(".")[0]
        if city_token and city_token in prompt_lower:
            return f"Source: {url}\n{text}"

    if "new york" in prompt_lower:
        return (
            "Source: https://www.nyc.gov/site/specialenforcement/registration-law/registration-law-for-hosts.page\n"
            "Local Law 18 strictly prohibits short-term rentals under 30 days unless the host is present. "
            "Unhosted STRs are fully banned in residential areas."
        )
    if "gatlinburg" in prompt_lower:
        return MOCK_PAGES.get(
            "https://www.gatlinburgtn.gov/departments/finance/business_licenses.php",
            "STRs allowed with Tourist Accommodation Permit.",
        )

    return (
        "Source: https://www.example.gov/str-ordinance\n"
        "Short-term rentals are allowed with a local permit. Minimum stay: 2 days. "
        "Primary residence not required. Transient occupancy tax applies at 9%. "
        "Yurts and RVs are restricted as temporary structures. Regulatory trajectory: low risk."
    )

def mock_gemini_response(
    prompt: str,
    response_schema: type[BaseModel] | None,
) -> str | BaseModel:
    """Deterministic mock LLM outputs for tests and offline development."""
    from app.llm import IngestedInputs, MacroScreenResult, LegalStatus, ReportSynthesis, Permit, SpecialTax

    prompt_lower = prompt.lower()

    if response_schema is IngestedInputs:
        locations: list[str] = []
        for token in ("jersey city", "gatlinburg", "new york", "new hampshire", "poconos", "union city"):
            if token in prompt_lower:
                locations.append(token.title() if token != "new hampshire" else "New Hampshire")
        if not locations and "query:" in prompt_lower:
            query_part = prompt_lower.split('query: "', 1)[-1].rsplit('"', 1)[0]
            locations = [query_part.strip()] if query_part.strip() else ["Gatlinburg"]
        if not locations:
            locations = ["Gatlinburg"]
        return IngestedInputs(target_locations=locations)

    if response_schema is MacroScreenResult:
        if any(k in prompt_lower for k in ("new york", "irvine")):
            return MacroScreenResult(
                status="BANNED",
                restriction_reason="STRs are prohibited or illegal in residential areas.",
            )
        if any(k in prompt_lower for k in ("los angeles", "denver", "san diego", "honolulu", "austin", "las vegas")):
            return MacroScreenResult(
                status="RESTRICTED",
                restriction_reason="STRs are allowed with significant restrictions.",
            )
        return MacroScreenResult(
            status="ALLOWED",
            restriction_reason="STRs are generally permitted with registration.",
        )

    if response_schema is LegalStatus:
        municipality = "Unknown"
        state = "XX"
        for line in prompt.splitlines():
            if "zoning research summary for" in line.lower():
                parts = line.split(" for ", 1)[-1].strip().rstrip(".")
                if "," in parts:
                    municipality, state = [p.strip() for p in parts.split(",", 1)]
                break
        if any(k in prompt_lower for k in ("not found", "unclear", "could not be found")):
            return LegalStatus(
                status="UNCLEAR",
                restriction_reason=f"STR regulations could not be found/confirmed for {municipality}, {state}.",
                eligible_zones_summary="Unknown",
                primary_residence_required=False,
                minimum_stay_days=0,
                permit_cap_exists=False,
                regulatory_trajectory_risk="Unknown",
                summary_of_restrictions=f"STR regulations could not be found/confirmed for {municipality}, {state}.",
            )
        return LegalStatus(
            status="RESTRICTED" if "restricted" in prompt_lower else "ALLOWED",
            restriction_reason="STR permitted subject to local registration and zoning rules.",
            eligible_zones_summary="Tourist overlay and commercial zones.",
            primary_residence_required="primary residence" in prompt_lower,
            minimum_stay_days=2,
            permit_cap_exists="cap" in prompt_lower,
            permits=[Permit(name="STR Permit", process_summary="Annual registration required.", application_url="https://example.gov/str")],
            special_taxes=[SpecialTax(name="Transient Occupancy Tax", rate="9%", description="Applied to gross rental income.")],
            regulatory_trajectory_risk="Low risk based on available sources.",
            summary_of_restrictions="STRs allowed with permit, tax, and zoning compliance.",
        )

    if response_schema is ReportSynthesis:
        return ReportSynthesis(
            qualitative_synthesis="This market shows solid STR fundamentals with favorable legal conditions for investment.",
            demand_drivers=["Tourism", "Outdoor recreation", "Regional events"],
        )

    return "Mock LLM response."
