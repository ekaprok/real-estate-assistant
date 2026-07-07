# Short-Term Rental Market Intelligence Agent

![Short-Term Rental Market Intelligence Agent](images/hero-banner.png)

A hybrid system that tells Short-Term Rental (STR) investors where they can legally operate and where the money is—built to be highly cost-effective.

**Video demo:** *[paste public link here]*

**Github link:** [https://github.com/ekaprok/real-estate-assistant](https://github.com/ekaprok/real-estate-assistant)

---

## Project Description

Short-term rental (STR) investing is complicated. A city might look profitable but have strict rules against STRs, like bans, permit caps, or minimum stay requirements. These rules change constantly, forcing investors to spend days reading complex municipal codes.

**Real Estate Assistant** automates this process. You give it a list of locations (e.g., *"Austin and Denver"*), and it gives you a clear report answering two questions: **Can I legally run an STR here?** and **Is it financially worth it?**

It works through a **5-step process** that only uses AI when necessary to save costs:

1. **Understand the request:** Parses the user's input using a fast AI model.
2. **Quick screen:** Checks search summaries to quickly eliminate cities where STRs are banned, saving time and money.
3. **Deep legal research:** An AI agent searches the web, reads official rules, and double-checks its findings in a loop (one AI gathers facts, another AI grades them and asks follow-up questions until satisfied).
4. **Financial data & math:** Pulls market data from the Mashvisor API and calculates profitability (Cap Rate, NOI, etc.) using standard code, not AI.
5. **Final report:** Creates an easy-to-read summary, ranked by profitability.

Every claim includes a link to the web source.

The main focus is **saving money**: we use cheaper AI models for simple tasks, filter text before sending it to the AI, use free or cheap data sources, and cache previous results. This makes the tool a powerful, affordable starting point for your research.

**Example run** (`Union City, NJ`):

```yaml
report_metadata:
  generated_at: '2026-07-07T02:51:15.088499Z'
  user_inputs:
    target_locations:
    - Union City, NJ
  data_sources:
    financial_data_source: Mashvisor
    legal_data_source:
      method: Serper.dev web search + municipal / Municode / eCode360 / AmLegal scrape
      source_urls:
      - https://ecode360.com/31144893
survived_municipalities:
- location:
    municipality: Union City
    state: NJ
    county: Hudson County
  legal_and_compliance:
    status: RESTRICTED
    restriction_reason: Short-term rentals under 30 consecutive days are generally
      prohibited in Union City.
    eligible_zones_summary: Unknown
    primary_residence_required: false
    minimum_stay_days: 30
    permit_cap_exists: false
    permits: []
    special_taxes: []
    regulatory_trajectory_risk: The city is actively cracking down on illegal short-term
      rentals and strengthening penalties for rental ordinance violations.
    summary_of_restrictions: Short-term rentals of less than 30 consecutive days are
      prohibited in Union City. Additionally, temporary structures such as RVs, tiny
      homes, and yurts are not permitted as accessory or primary residential dwellings.
    source_urls:
    - https://ecode360.com/31144893
  hoa_disclaimer: Resort and planned communities in this market commonly carry HOAs
    whose CC&Rs may restrict STRs. This system verifies only government zoning/law —
    confirm HOA rules independently before closing.
banned_municipalities: []
undetermined_municipalities: []
```

---



## The Problem & Impact

STR rules vary wildly across thousands of cities.

**Real Estate Assistant turns days of manual web searching into a single, organized starting point.** It makes professional-level research available to everyday investors. Because every claim links to an official source, the results are easy to verify, giving you a massive head start on your due diligence.

---



## How It Works

The system uses standard code for math and routing, and saves AI strictly for reading and research. This makes it both effective and cheap.

```
User query
   │
   ▼
[1] Understand Request ──► Fast AI (Gemini Flash-Lite)
   │  (Stops early if the request is invalid or requests additional info from a user)
   ▼
[1.5] Find Cities ──► Matches city names to real places using Google Maps Geocoding API
   │
   ▼
[2] Quick Screen ──► Web search + Fast AI classifies search snippets
   │  (Eliminates banned cities immediately)
   ▼
[3] Deep Research ──► AI Research Loop (Executor AI finds facts, Evaluator AI grades them)
   │  ├─ Searches and reads official rules
   │  ├─ Filters out useless text
   │  └─ Double-checks its own work
   ▼
[4] Financial Math ──► Mashvisor API + Standard Code (No AI)
   │
   ▼
[5] Final Report ──► Fast AI creates the summary
```

Key design choices:

- **Structured data:** The AI always returns data in a specific format, preventing errors.
- **Self-checking research:** We use an "Executor" AI to gather facts from the web, and an "Evaluator" AI to grade if those facts are correct and complete. If not, the Evaluator sends the Executor back to search again.
- **No guessing:** The AI must link every fact to a source. If it can't find the answer, it says "NOT FOUND" instead of making something up.

---



## Cost Optimization

Building this the simple way (sending entire webpages to an expensive AI) would cost too much. We reduced costs in four ways:

### 1. Using the right AI for the job

We use two different AI models:

- **Fast and Cheap (Gemini Flash-Lite):** Handles simple, repetitive tasks like understanding the prompt and writing the final report.
- **Smart and Detailed (Gemini Flash):** Only used for complex tasks, like evaluating legal text.



### 2. Shrinking text before the AI reads it

Official city websites have a lot of useless text. We clean it up first:

- **Remove junk:** We strip out menus, footers, and code.
- **Keep only what matters:** We only keep paragraphs that mention keywords like *"short-term rental"* or *"permit"*, shrinking a huge page into a few relevant paragraphs.
- **Quick summaries:** We use search engine summaries for the first check, avoiding full webpage downloads when possible.



### 3. Using free or cheap data sources

- We use affordable search APIs (Serper API for Google search results and standard web scraping for page fetching).
- We read free official government websites instead of paid legal databases.
- Financial data is pulled from the Mashvisor API, but it is optional, so you can run a free legal-only check.



### 4. Avoiding unnecessary work

- **Saving results (Caching):** If someone asks about a city we've already researched, we use the saved answer. It costs $0.
- **Standard math:** We use regular code for calculations on the Mashvisor data, never paying AI to do math.
- **Strict limits:** We set hard limits on how many searches the tool can do, preventing runaway costs.



### Approximate cost per request

**Bottom line: a typical single-city analysis costs roughly $0.05–$0.15 on a cache miss, and effectively $0 when served from cache.**

The estimate below is for one city on a *fresh* run (no cache), assuming the research loop converges in 1–2 iterations (the common case). **The dominant cost is the agentic research loop**, for two reasons specific to modern Gemini models:

| Component                | What runs                                                      | Typical usage (incl. reasoning tokens) | Approx. cost                                           |
| ------------------------ | -------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------ |
| Cheap model (Flash-Lite) | Prompt parse, quick screen, research executor, final synthesis | ~30–40K input + ~15K output tokens      | ~$0.015                                                |
| Smart model (Flash)      | Research evaluator, structured legal extraction                | ~8K input + ~7K output tokens           | ~$0.030                                                |
| Web search (Serper)      | Quick screen + deep-research queries                           | ~6–10 searches                          | ~$0.008                                                |
| Geocoding (Google Maps)  | Resolve city → municipality                                    | 1 lookup                                | ~$0.005                                                |
| Page scraping            | Fetch official ordinance pages                                 | ~3–5 fetches                            | ~$0 (self-hosted)                                      |
| Financials (Mashvisor)   | Market/ROI data                                                | 1 lookup                                | subscription (optional; $0 with `SKIP_MASHVISOR=true`) |
| **Total**                |                                                                |                                         | **~$0.05–$0.15 / city**                                |

Without the optimizations this would be several times higher. The **hard per-run API limits** (up to ~25 loop model calls, 20 searches, and 10 fetches per city) act as a cost ceiling — a pathological, non-converging run (3 full iterations, heavy reasoning) tops out around **$0.30–$0.50/city** rather than spiraling.

*(These are engineering estimates, not billed figures.


## Technologies Used

- **Framework:** Google Agent Development Kit (ADK)
- **Language:** Python
- **AI Models:**
  - **Gemini 3.1 Flash-Lite:** Used for fast, low-cost tasks (parsing user requests, quick screening, and final report synthesis).
  - **Gemini 3.5 Flash:** Used for complex reasoning tasks (evaluating legal text and deep research).
- **APIs & Data Sources:**
  - **Google Maps Geocoding API:** Resolves city names to precise locations.
  - **Overpass API:** OpenStreetMap fallback for municipality resolution.
  - **Serper API:** Provides Google Search results and text snippets for the quick screen.
  - **Mashvisor API:** Provides real estate financial data (property prices, revenue, cap rates).

---



## Future Work

- **Financial data analysis:** Improve the depth of financial data analyses and expand testing coverage to ensure calculation accuracy.
- **More flexible user input:** Allow users to query larger regions or more cities at once. Currently, there are strict limits on how many API calls are allowed and how many locations can be processed simultaneously to control costs.
- **Cache invalidation:** Improve how we update saved research when city rules change so that cached data doesn't become permanently stale.
- **Distributed cache:** Replace the local SQLite cache with a shared, networked cache like Redis.
- **Broader coverage:** Support international cities and verify HOA/CC&R rules (currently handled with a disclaimer).

