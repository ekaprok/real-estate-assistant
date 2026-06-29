# Real Estate Assistant Design Doc

# Goal

Build an automated, cost-efficient agent that ingests user location preferences and property types, verifies STR legality, and outputs an ROI-ranked list of target markets.

# Background

Identifying profitable short-term rental (STR) markets is a manual, fragmented process. Investors must currently cross-reference geographic data, complex local regulations, and financial metrics across multiple isolated platforms.

API calls for premium real estate data and LLM processing are expensive. Running comprehensive checks on entire states or large metropolitan areas without a pre-filtering strategy is cost-prohibitive.

# Future work

- **Build vs. Buy analysis (`build_vs_buy` report block):** cost-to-build per sqft and lot/permit feasibility (lot pricing, setbacks, min lot size, impact fees, utility/septic hookups). Not reliably available from Web Search or Mashvisor; would require RSMeans / local GC quotes plus municipal planning/GIS sources. Includes the original goal of build-from-scratch cost of labor and materials.
- **High-impact amenity analysis (`optimal_property_configuration.high_impact_amenities`):** quantifying which amenities drive ADR/occupancy in a given market. Mashvisor lists per-listing amenities but does not attribute lift; would require AirDNA (or a self-built regression over comp-level data).
- **Research on medium-term rentals and long-term rentals.**

# Design

## Data Sources

The core financial and legal data must originate from the following primary sources:

1. **Google Maps Geocoding API & Overpass API**
   - **Purpose:** Resolving colloquial regions (e.g., "Poconos") into specific municipalities.
   - **Cost:** Google Maps Geocoding is effectively free under 40,000 queries/month. Overpass API is 100% free and open source.
2. **Web Search (Serper.dev)**
   - **Purpose:** Google SERP API (snippets + result URLs) plus an HTTP page-fetch/scrape tool that retrieves the full text of those URLs for legal verification.
   - **Cost:** ~$0.30–$1.00 per 1,000 queries. Provides high-quality snippets at a fraction of the cost of other search APIs.
3. **The Mashvisor API**
   - **Purpose:** Financial and market data (Average Daily Rate, Occupancy, Revenue, property prices).
   - **Cost:** Premium/expensive API. Calls are minimized by placing them after the macro legal screen.
4. **LLMs (Gemini Flash & Gemini Pro)**
   - **Purpose:** Gemini Flash is used for lightweight triage and report synthesis. Gemini Pro is used for deep legal evaluation of zoning codes.
   - **Cost:** Gemini Flash costs fractions of a cent per query. Gemini Pro is more expensive but only used on the small subset of surviving municipalities.

## High-Level Overview

- **Step 1: Ingestion:** Accept user inputs (locations, budget, build vs. buy, property type).
- **Step 1.5: Geographic Resolution:** Convert user location inputs (e.g., "Poconos") into a specific list of municipalities using Google Maps Geocoding and Overpass API. Cache these results.
- **Step 2: The Macro Legal Screen (Search + Minimal LLM):** For the candidate municipalities, execute a single Web Search query for STR bans. Feed only the search snippets into a small, fast LLM to quickly drop municipalities where STRs are *definitely illegal*. Cache the results.
- **Step 3: Deep Legal Verification (LLM Scrape):** For the survivors of the macro screen, use an iterative web-research loop to locate and scrape the full official city zoning code. A larger LLM evaluates the full text to confirm STR legality and identify specific restrictions (e.g., permit caps, primary residence requirements).
- **Step 4: ROI Ranking & Optimal Configuration (Mashvisor API):** For the confirmed legal municipalities, fetch granular STR performance data (Average Daily Rate, Occupancy, Revenue) using the Mashvisor API. The system calculates overall ROI and identifies the most profitable hpme type. Present a financially-ranked shortlist to the user to select their top markets.
- **Step 5: Synthesis & Deterministic Report Assembly:** Deterministically compute scores/derived fields in Python, generate a short LLM synthesis, and assemble the final YAML report.

## Steps Deep-Dive

### Step 1: Ingestion

User Input:

- **Target Geography:** States, cities, ZIP codes, or metro areas (e.g., `"New Hampshire"`, `"Jersey City", "10023", "Poconos"`).
- **Home Types:** Traditional properties (e.g., `house`, `condo`) and Unique Stays (e.g., `tiny home`, `cabin`, `shipping container`, `dome`, `yurt`). (Note: the pipeline must check zoning and permits against the specific sub-type, as local regulations treat them differently.)
- **Execution Strategy:** `"Build from scratch"` vs. `"Buy existing."`.

### Step 1.5: Geographic Resolution

Because ZIP codes and metro areas cross legal boundaries, the system must resolve all geographic inputs down to the specific **municipality (city/town/village/county)** and **zoning district** to accurately verify STR regulations. 

This resolution will be handled using a two-step approach: 
1. The **Google Maps Geocoding API** will resolve colloquial regions (e.g., "Poconos") into highly accurate bounding boxes.
2. The **Overpass API** will query for all `admin_level=8` (municipalities) intersecting that bounding box.

These results must be cached to avoid redundant API calls.

### Step 2: The Macro Legal Screen (Triage)

This step is designed to be the **absolute cheapest and fastest** filtering layer. The goal is to aggressively prune the list of municipalities using only low-cost Web Search APIs and the smallest, fastest LLMs available. 

#### Tools & Infrastructure Required
- **Search API:** Serper.dev
- **LLM:** the latest Gemini Flash (e.g. `gemini-flash-latest`).
- **Caching Layer:** **SQLite** (local file-based) or **Redis** (if scaling to a cloud service). For initial development and cost-efficiency, SQLite is the superior choice as it requires zero infrastructure setup, has no recurring hosting costs.

#### Process Flow

1. **Cached Web Search:**
   - **Query Structure to Serper API:** `"{municipality}" "{state}" ("short-term rental" OR "transient occupancy tax") (ban OR ordinance OR zoning) (site:.gov OR site:.us OR site:municode.com OR site:ecode360.com OR site:amlegal.com)`
   - *Relevance & Query Impact Note:* Including third-party civic platforms (Municode, eCode360, AmLegal) is strictly necessary for system accuracy. The vast majority of small-to-medium US municipalities lack the IT infrastructure to host searchable ordinances on their primary `.gov` or `.us` websites, outsourcing this entirely to these SaaS platforms. 
   - **Caching Strategy:** Cash by `hash(state + municipality + query)` in SQLite with a 90 day TTL.

2. **Lightweight LLM Triage:**
   The system feeds *only the text snippets* from the search results into the lightweight LLM. These snippets are returned natively in the Serper API JSON response and concatenate the top 5-10 snippets into a single short text block.
   - **Prompt & Output Design:** We strictly use **JSON with Structured Outputs** to enforce deterministic output. The enforced schema is: `{"status": "BANNED" | "ALLOWED" | "RESTRICTED" | "UNCLEAR"}`.
    - **Decision Logic:** 
      - If `BANNED`: The municipality is dropped from the main pipeline but recorded to be listed in the final report's banned section.
      - If `ALLOWED`, `RESTRICTED`, or `UNCLEAR`: The municipality survives and is passed to Step 3 for Deep Legal Verification. (It is cheaper to pass an "unclear" municipality to Step 3 than to run a heavy LLM in Step 2).

#### Optimization Notes
- **Parallel Execution:** the system should process all municipalities asynchronously.
- **Cost Ratio:** By restricting the LLM context window to just ~500 tokens of search snippets and using a flash-class model, 95%+ of the cost of this step is allocated to the Search API calls.

### Step 3: Deep Legal Verification
#### Iterative Web-Research Loop

A single search is rarely enough. Step 3 is therefore implemented as an **iterative research loop** (ADK `LoopAgent`, the `deep-search` pattern), run only over the small set of survivors:

1. **Search:** Issue a targeted Web Search (Serper). The first iteration reuses the URLs already returned in Step 2; later iterations refine the query (specific zoning chapter, "transient occupancy tax", county site, etc.). If the user specified `desired_home_types` that include unique stays (e.g., "Tiny Home", "Yurt"), the search query must explicitly include these terms (e.g., `"tiny home" OR "accessory dwelling unit"`).
2. **Scrape:** Select the "highest-confidence" URLs by filtering for official municipal domains (e.g., `.gov`, `.us`) or known zoning hosts (e.g., `municode.com`, `ecode360.com`, `amlegal.com`, `hostcompliance.com`), take the top 2-3, and scrape the *full text* with the page-fetch tool.
3. **Evaluate:** A frontier LLM evaluates the accumulated text against the structured schema defined in the final report template. The LLM must be explicitly prompted with the user's `desired_home_types` to ensure it checks for explicitly banned or allowed unique structures within the zoning code.
  - Enforce a strict JSON Schema output for this step, just as we did in the triage phase. Returning structured JSON with a schema matching the `legal_and_compliance` block from `specs/final_report_template.yaml`.
  - Cache the output by the municipality name and state. 
4. **Decide / Refine:** If legality, minimum-stay, permits, taxes, and rules regarding the specific `desired_home_types` are resolved (status != `UNCLEAR`), exit the loop. Otherwise refine the query and repeat, up to a max iteration cap (e.g., 3) to bound cost.

A secondary tax-focused search (e.g., `"{municipality}" "{state}" ("transient occupancy tax" OR "hotel tax" OR "short-term rental tax") site:.gov OR site:.us`) is part of the loop to capture tax rules hosted separately from zoning codes.

### Step 4: ROI Ranking & Optimal Configuration (Mashvisor API)

For the municipalities that passed the legal verification, the system fetches granular financial performance data to rank the markets and determine the most profitable property configurations.

#### Tools & Infrastructure Required
- **Financial Data API:** Mashvisor API.
- **Data Processing:** Python (`pandas`) for fast aggregation, ranking, and filtering of the API JSON responses.

#### Process Flow

1. **Market-Level Financial Pull (Where to Buy):**
   - Query the API for the approved municipalities to extract ZIP-code level data.
   - **Key Metrics:**
     - **Average Daily Rate (ADR) & Occupancy Rate:** To understand revenue potential.
     - **Seasonality:** Peak vs. low season revenue variance (critical for investor cash flow planning).
     - **Market Saturation & Trends:** Active listing count and Year-over-Year (YoY) revenue growth.
     - **Average Annual Revenue (RevPAR):** Gross income expectations.
     - **Median Property Price:** To establish the cost basis.
     - **Operating Expenses (OpEx):** Estimated property management (20-30% for STRs), STR insurance, utilities, and property taxes.
     - **Average Cap Rate & Cash-on-Cash Return:** To evaluate the actual profitability and yield of the market.

2. **Optimal Configuration Analysis (What to Buy):**
   - Read the Mashvisor Lookup subgroups (comparable-property groups by bed/bath/type) to identify the best-performing configuration.
   - **Data Points:**
     - **Optimal Property Type:** Compare yields across the property types Mashvisor returns (e.g., Single-Family, Condo, Cabin). Note: subgroup granularity is driven mostly by bed/bath, so the property-type label may be coarse.
     - **Optimal Bedroom/Bathroom Count & Capacity:** Identify the "sweet spot" (e.g., a 3-bedroom/2-bath might yield a higher ROI percentage than a 5-bedroom due to significantly lower acquisition costs). `accommodates` comes from `median_guests_capacity`.

3. **Deterministic JSON Construction & Ranking:**
   - Instead of relying on an LLM to parse raw financial data (which can lead to hallucinations in math), the system **deterministically constructs the output** directly from the Mashvisor API responses using Python.
   - The system calculates a final composite `municipal_str_score` for each municipality from the documented `score_weights` (cap-rate yield, budget fit, legal friendliness).
   - The top 3-5 markets are shortlisted and passed to Step 5 for synthesis and report assembly.

### Step 5: Synthesis & Deterministic Report Assembly

The final step turns the per-municipality data gathered in Steps 2-4 into the structured report defined by `specs/final_report_template.yaml`.

#### Process Flow
1. **Deterministic computation (Python):** All numeric and boolean fields are computed in Python directly from the source data — never by an LLM — to avoid math hallucinations. This includes:
   - `municipal_str_score` from `score_weights` (cap-rate yield, budget fit, legal friendliness; weights sum to 100).
   - `budget_fit.within_budget` and `budget_fit.budget_headroom` (`max_budget - median_property_price`).
   - `annual_revenue_estimate`, `annual_noi_estimate`, and `data_quality` (from `sample_size` thresholds: high ≥80, medium ≥30, low ≥15, very_low <15).
   - Ranking the shortlist (typically 3-5 municipalities).
2. **Qualitative synthesis (LLM):** Pass the deterministically built per-municipality object to a fast LLM (latest Gemini Flash) to generate the 2-3 sentence `qualitative_synthesis`, grounded only in the supplied data (e.g., "Gatlinburg ranks first for 3-bedroom cabins at a 7.4% cap rate, within your $500K budget...").
3. **Assembly:** Validate every field against typed (Pydantic) models that mirror the template, then serialize to YAML.
