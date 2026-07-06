import os
import logging

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

from pydantic import BaseModel, Field
from typing import Literal
from google import genai
from google.genai import types
from google.adk.agents import Agent, LlmAgent
from google.adk.workflow import Workflow, node
from google.adk.agents.context import Context
from google.adk.events import Event
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from app.api_limits import increment_api_count
from app.tools import serper_search, fetch_page
from app.app_utils.cache import with_cache

# Pydantic models for structured outputs
class IngestedInputs(BaseModel):
    target_locations: list[str] = Field(default_factory=list)

class MacroScreenResult(BaseModel):
    status: Literal["BANNED", "ALLOWED", "RESTRICTED", "UNCLEAR"]
    restriction_reason: str

class Permit(BaseModel):
    name: str
    process_summary: str
    application_url: str

class SpecialTax(BaseModel):
    name: str
    rate: str
    description: str

class LegalStatus(BaseModel):
    status: Literal["ALLOWED", "RESTRICTED", "UNCLEAR"]
    restriction_reason: str
    eligible_zones_summary: str
    primary_residence_required: bool
    minimum_stay_days: int
    permit_cap_exists: bool
    permits: list[Permit] = Field(default_factory=list)
    special_taxes: list[SpecialTax] = Field(default_factory=list)
    regulatory_trajectory_risk: str
    summary_of_restrictions: str

class ReportSynthesis(BaseModel):
    qualitative_synthesis: str
    demand_drivers: list[str] = Field(default_factory=list)

class SearchQuery(BaseModel):
    search_query: str = Field(description="A highly specific and targeted query for web search.")

class Feedback(BaseModel):
    grade: Literal["pass", "fail"] = Field(description="Evaluation result. 'pass' if the research is sufficient, 'fail' if it needs revision.")
    comment: str = Field(description="Detailed explanation of the evaluation.")
    follow_up_queries: list[SearchQuery] | None = Field(default=None, description="Queries to fill gaps if grade is 'fail'.")



def get_genai_client() -> genai.Client:
    """Helper to initialize genai.Client checking dev keys and Vertex settings."""
    dev_key = os.environ.get("GOOGLE_API_KEY_DEV")
    if dev_key and not any(p in dev_key.lower() for p in ["your_", "placeholder", "key_here"]):
        os.environ["GEMINI_API_KEY"] = dev_key
        return genai.Client(api_key=dev_key)

    use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True"
    if use_vertex:
        try:
            return genai.Client(vertexai=True, location="global")
        except Exception:
            return genai.Client()
    return genai.Client()


from app.app_utils.cache import get_cached_response, set_cached_response

def call_gemini_flash(prompt: str, response_schema: type[BaseModel] | None = None) -> str | BaseModel:
    """Calls Gemini Flash and increments call counter. Caches queries to save costs."""
    import hashlib
    schema_name = response_schema.__name__ if response_schema else "None"
    val = f"{prompt}_{schema_name}".lower()
    args_hash = hashlib.md5(val.encode("utf-8")).hexdigest()

    use_mock = os.environ.get("USE_MOCK_APIS", "False").lower() == "true"
    if use_mock:
        cache_key = f"mock_llm_{args_hash}"
    else:
        cache_key = f"llm_{args_hash}"

    cached = get_cached_response(cache_key)
    if cached is not None:
        logger.info(f"Cache hit for LLM key {cache_key}")
        if response_schema:
            if hasattr(response_schema, "model_validate"):
                return response_schema.model_validate(cached)
            else:
                return response_schema.parse_obj(cached)
        return cached

    # Cache miss
    increment_api_count("llm_gemini_flash")
    client = get_genai_client()

    # Use standard 1.5 Flash model
    model_name = "gemini-3.5-flash"

    config = types.GenerateContentConfig()
    if response_schema:
        config.response_mime_type = "application/json"
        config.response_schema = response_schema

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=config
    )

    if response_schema:
        import json
        validated = response_schema.model_validate_json(response.text)
        if hasattr(validated, "model_dump"):
            dumped = validated.model_dump()
        else:
            dumped = validated.dict()
        set_cached_response(cache_key, dumped)
        return validated

    set_cached_response(cache_key, response.text)
    return response.text



# Callback to track LLM agent calls during ReAct loops
async def count_agent_model_call(callback_context, llm_request) -> None:
    increment_api_count("llm_gemini_flash_loop")

@node
def check_evaluation(ctx: Context, node_input: dict):
    """Checks research evaluation and counts iterations to handle loop routing."""
    iterations = ctx.state.get("research_iterations", 0) + 1
    grade = node_input.get("grade", "")

    state_delta = {"research_iterations": iterations}

    if grade == "pass":
        logger.info("[check_evaluation] Research passed. Stopping loop.")
        return Event(route="pass", state=state_delta)
    elif iterations >= 3:
        logger.info("[check_evaluation] Max iterations reached. Stopping loop.")
        return Event(route="pass", state=state_delta)
    else:
        logger.info(f"[check_evaluation] Research failed (iteration {iterations}). Loop continues.")
        return Event(route="fail", state=state_delta, output="Continue research based on feedback.")

# ADK agent for deep research loop
def get_deep_legal_loop_agent() -> Workflow:
    research_executor = LlmAgent(
        name="research_executor",
        model="gemini-3.5-flash",
        instruction="""
You are an expert real-estate zoning researcher. Your goal is to gather facts on short-term rental (STR) legality and regulations for a specific municipality.
Use serper_search and fetch_page to find and read municipal codes and local ordinances.
Find out:
1. Is STR allowed, restricted, or banned?
2. Specific rules, minimum stay requirements, permit caps, required permits, and special taxes.
3. Regulatory trajectory or local debate.
If this is a follow-up, you must also address the feedback and follow_up_queries provided in the 'research_evaluation' state. Execute new targeted searches for any missing information.
Synthesize all your findings into a comprehensive research summary.
""",
        tools=[serper_search, fetch_page],
        before_model_callback=count_agent_model_call,
        output_key="research_findings",
    )

    research_evaluator = LlmAgent(
        name="research_evaluator",
        model="gemini-3.5-flash",
        instruction="""
You are a meticulous evaluator. Review the research in 'research_findings'.
Does it clearly answer:
1. If STR is allowed/restricted/banned?
2. Specific minimum stays, caps, permits, taxes?
3. Regulatory trajectory?
4. Unique stays rules (e.g. yurts, RVs, temporary structures)?
Grade 'pass' only if all details (including unique stays) are found or conclusively proven unavailable. Otherwise grade 'fail' and provide explicit follow-up queries targeting the exact missing information.
""",
        output_schema=Feedback,
        output_key="research_evaluation",
        before_model_callback=count_agent_model_call,
    )

    report_composer = LlmAgent(
        name="report_composer",
        model="gemini-3.5-flash",
        instruction="""
Format the final research findings from 'research_findings' into a single coherent summary document.
Do not perform any new searches.
""",
        before_model_callback=count_agent_model_call,
        output_key="final_research_summary",
    )

    edges = [
        ('START', research_executor),
        (research_executor, research_evaluator),
        (research_evaluator, check_evaluation),
        (check_evaluation, {
            "pass": report_composer,
            "fail": research_executor
        })
    ]

    return Workflow(
        name="DeepLegalLoopAgent",
        edges=edges
    )


# Step 1: Parse user prompt
@with_cache("parse")
def parse_user_prompt(prompt_text: str) -> IngestedInputs:
    prompt = f"""
Analyze the following user real estate query and extract:
Target geographies/locations (list of states, cities, ZIP codes, regions).

Query: "{prompt_text}"
"""
    return call_gemini_flash(prompt, response_schema=IngestedInputs)


# Step 2: Macro Legal Screen
@with_cache("macro")
def run_macro_legal_screen(municipality: str, state: str) -> MacroScreenResult:
    # Get Serper snippets first
    query = f'"{municipality}" "{state}" "short-term rental" OR "transient occupancy tax" ban OR ordinance OR zoning'
    search_data = serper_search(query)

    snippets = []
    if "organic" in search_data:
        for result in search_data["organic"][:5]:
            snippets.append(result.get("snippet", ""))
    snippets_text = " ".join(snippets)

    prompt = f"""
You are doing a quick macro legal screen for short-term rentals (STR) in {municipality}, {state}.
Based ONLY on the following search snippets, classify the municipality as:
- "BANNED": If STRs are completely prohibited or illegal in residential/city areas.
- "ALLOWED": If STRs are generally allowed with simple registration/permit and no major caps.
- "RESTRICTED": If STRs are allowed but face significant restrictions (e.g. only primary residence allowed, strict caps, zoning overlays, 90+ day minimum stay).
- "UNCLEAR": If the snippets do not contain clear evidence.

Search snippets:
{snippets_text}

Provide the response matching the schema.
"""
    return call_gemini_flash(prompt, response_schema=MacroScreenResult)


# Step 3: Extract structured legal status from research history
def extract_legal_status(municipality: str, state: str, research_summary: str) -> LegalStatus:
    prompt = f"""
Analyze the zoning research summary for {municipality}, {state}. Ensure that the analysis covers all home types (e.g. yurts, tiny homes, cabins, etc.) and execution strategies for the legal report.
Extract and fill out the structured LegalStatus JSON matching the required schema.
Evaluate if unique stays / temporary structures (e.g. Yurts, RVs) are prohibited or restricted.

Zoning research summary:
{research_summary}
"""
    return call_gemini_flash(prompt, response_schema=LegalStatus)


# Step 5: Synthesis
def synthesize_report(municipality: str, state: str, calculated_data: dict) -> ReportSynthesis:
    calculated_data_str = json_dumps_clean(calculated_data)
    prompt = f"""
Write a 2-3 sentence qualitative synthesis for a short term rental investment in {municipality}, {state}.
Use ONLY the following calculated financial and legal data:
{calculated_data_str}

Also, generate a list of 2-4 major tourist demand drivers for {municipality}, {state} (using your general world knowledge).

Provide the output matching the schema.
"""
    return call_gemini_flash(prompt, response_schema=ReportSynthesis)

def json_dumps_clean(obj):
    import json
    return json.dumps(obj, default=str)
