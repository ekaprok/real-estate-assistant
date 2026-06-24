# Real Estate Assistant Design Doc

# Goal

Build an automated, cost-efficient agent that ingests user location preferences and property types, aggressively filters down to high-potential ZIP codes, verifies STR legality, and outputs an ROI-ranked list of target markets.

# Background

Identifying profitable short-term rental (STR) markets is a manual, fragmented process. Investors must currently cross-reference geographic data, complex local regulations, and financial metrics across multiple isolated platforms.

API calls for premium real estate data and LLM processing are expensive. Running comprehensive checks on entire states or large metropolitan areas without a pre-filtering strategy is cost-prohibitive.

# Future work

* Support getting information about building from scratch vs buying, e.g. cost of labor and materials.  
* Support research on medium-term rentals and long-term rentals.

# Design

## High-Level Overview

* **Phase 1: Ingestion & Pre-Filtering:** Accept user inputs. Map geographic inputs to specific ZIP codes and aggressively filter them (e.g., dropping ZIPs outside the user's budget before checking STR rules).  
* **Phase 2: Regulatory Compliance (LLM):** Identify the governing municipality for the surviving ZIP codes. Scrape municipal codes and use an LLM to determine if STRs for the specified property type are legal, restricted, or banned.  
* **Phase 3: Financial & ROI Analysis:** For the cleared ZIPs, fetch granular STR performance data (Average Daily Rate, Occupancy) and calculate estimated ROI/Cap Rate.  
* **Phase 4: Output Rendering:** Deliver a ranked dataset featuring ROI-ranked markets. Include granular property-level specifications, such as asset type (e.g., tiny home, cabin) and optimal configurations for bathrooms and occupancy.

## Infrastructure \+ Frameworks

Python and ADK

## User Input Specification

Inputs:

* **Target Locations (`locations`):** An array containing location identifiers. Can accept a mix of City names (e.g., `"Austin, TX"`), specific ZIP codes (e.g., `"90210"`), or entire States (e.g., `"Utah"`).  
* **Property Type (`property_type`):** An explicit string enum matching supported architectural classifications (e.g., `["tiny home", "cabin", "house", "condo"]`). This directly dictates the municipal zoning rules the LLM will parse.  
* **Max Purchase Budget (`max_budget`):** Used immediately in Phase 1 to drop over-budget ZIP codes before any downstream LLM or STR data calls are made.  
* **Strategy Type (`rental_strategy`):** Defaults strictly to `"STR"` (Short-Term Rental) for this phase.

## Location Filtering & ZIP Code Reduction

**Goal:** Reduce hundreds of potential ZIP codes down to a top 10-20 list to save downstream API costs.

**Logic:**

* Map state/city inputs to an array of ZIP codes.  
* *Constraint Addition:* Prompt the user for a "Max Purchase Budget."  
* Filter out ZIPs where the median property price for the desired type (e.g., cabin, tiny home) exceeds the budget using free or cheap-tier real estate aggregators.  
* Filter out ZIPs with zero existing STR footprint (which strongly indicates either zero market demand or an existing total ban).

**Tools & APIs:**

**Model:**

**Skills:**

## Regulation Checking via LLM

**Goal:** Determine STR legality with high confidence and minimal hallucination.

**Logic:**

* Convert ZIP codes to Municipalities/Counties (regulations are enacted at the city/county level, not by ZIP code).  
* Use an autonomous search agent to locate the official city zoning code or STR ordinance page.  
* Feed the scraped text into an LLM with a strict system prompt and structured JSON output: `{"status": "LEGAL" | "RESTRICTED" | "BANNED", "reasoning": "1-sentence justification"}`.  
* Drop "BANNED" municipalities immediately. Flag "RESTRICTED" (e.g., primary residence only, permit caps) for user review.

**Tools & APIs:**

**Model:**

**Skills:**

## ROI & Profitability Analysis

**Goal:** Calculate standardized profitability metrics for the final, legal ZIP codes.

**Logic:**

* Query premium STR APIs for trailing 12-month Average Daily Rate (ADR) and Annual Occupancy Rate.  
* Calculate Gross Revenue: **ADR \* (365 \* Occupancy Rate)**.  
* Calculate estimated Net Operating Income (NOI) by applying standardized expense ratios (e.g., 35% for property management, cleaning, taxes, and maintenance).  
* Calculate the Cap Rate and rank the final array of ZIP codes by highest yield.

**Tools & APIs:**

**Model:**

**Skills:**

