# Real Estate Assistant

The Real Estate Assistant is an AI-powered tool designed to analyze short-term rental (STR) markets. It evaluates the legal landscape (zoning laws, regulations, permits) and financial viability (ROI, Cap Rate, OpEx) of specific municipalities to help real estate investors make data-driven decisions.

## Quick Start

Follow these steps to get the project running locally.

### 1. Prerequisites

Ensure you have [uv](https://docs.astral.sh/uv/getting-started/installation/) installed. `uv` is an extremely fast Python package manager used for this project.

### 2. Install the Agents CLI

This project uses the Google Agents CLI for development and testing. Install it globally:

```bash
uv tool install google-agents-cli
uvx google-agents-cli setup
```



### 3. Install Dependencies

Install the project dependencies using the Agents CLI:

```bash
agents-cli install
```



### 4. Configure API Keys

Before running the project, you need to set up your API keys. Create a `.env` file in the root of the project and add the following variables.

**Note:** The Mashvisor API key (`MASHVISOR_API_KEY_DEV`) is optional if you plan to skip financial calculations by setting `SKIP_MASHVISOR=true` (explained below).

```bash
# .env
GOOGLE_API_KEY_DEV=your_gemini_api_key
SERPER_API_KEY_DEV=your_serper_api_key
GOOGLE_MAPS_API_KEY_DEV=your_maps_api_key
MASHVISOR_API_KEY_DEV=your_mashvisor_api_key
```



### 5. Run the Agent

Run the Real Estate Assistant from the project root with the Google Agents CLI. Pass the target municipality as the prompt:

```bash
agents-cli run "Austin, TX"
```

Optional environment variables:

- `SKIP_MASHVISOR=true` — skip financial calculations (legal/compliance data only). Useful if you do not have a Mashvisor API key.
- `USE_MOCK_APIS=true` — use mock data instead of live API calls. Useful for local testing without API keys.

Examples:

```bash
# Full analysis with live APIs
agents-cli run "Austin, TX"

# Legal/compliance only (no Mashvisor key needed)
SKIP_MASHVISOR=true agents-cli run "Austin, TX"

# Local testing with mock data
USE_MOCK_APIS=true agents-cli run "Austin, TX"
```

## Run the Playground

Launch a local web UI for interactive testing. The server auto-reloads when you save changes to agent code:

```bash
agents-cli playground
```

Use the playground when you want to iterate on prompts, inspect agent behavior, or demo the assistant in a browser.

## Project Structure

- `app/`: Core agent code and pipeline logic.
- `tests/`: Unit and integration tests.
