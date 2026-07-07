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

Run the Real Estate Assistant through the Google Agents CLI. This goes through the ADK agent entry point (`app/agent.py`).

Set **Skip Mashvisor** and **Mock APIs** as environment variables when needed:

<div id="command-builder">
  <table>
    <thead>
      <tr>
        <th>Input</th>
        <th>Value</th>
        <th>Description</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><label for="cb-location">Location</label></td>
        <td><input type="text" id="cb-location" value="Austin, TX" size="40" placeholder="Austin, TX"></td>
        <td>Target municipality to analyze (required)</td>
      </tr>
      <tr>
        <td><label for="cb-skip-mashvisor">Skip Mashvisor</label></td>
        <td>
          <select id="cb-skip-mashvisor">
            <option value="false" selected>false</option>
            <option value="true">true</option>
          </select>
        </td>
        <td>Skip financial calculations; legal/compliance data only</td>
      </tr>
      <tr>
        <td><label for="cb-mock-apis">Mock APIs</label></td>
        <td>
          <select id="cb-mock-apis">
            <option value="false" selected>false</option>
            <option value="true">true</option>
          </select>
        </td>
        <td>Use mock data instead of live API calls</td>
      </tr>
    </tbody>
  </table>
  <p><strong>Generated command</strong></p>
  <pre id="cb-output"><code>agents-cli run "Austin, TX"</code></pre>
  <button type="button" id="cb-copy">Copy command</button>
</div>

<script>
(function () {
  var locationInput = document.getElementById("cb-location");
  var skipInput = document.getElementById("cb-skip-mashvisor");
  var mockInput = document.getElementById("cb-mock-apis");
  var output = document.getElementById("cb-output");
  var copyButton = document.getElementById("cb-copy");

  if (!locationInput || !skipInput || !mockInput || !output) return;

  function escapeShellArg(value) {
    return '"' + value.replace(/\\/g, "\\\\").replace(/"/g, '\\"') + '"';
  }

  function buildCommand() {
    var location = locationInput.value.trim() || "Austin, TX";
    var envVars = [];
    if (skipInput.value === "true") envVars.push("SKIP_MASHVISOR=true");
    if (mockInput.value === "true") envVars.push("USE_MOCK_APIS=true");
    var command = "";
    if (envVars.length) command += envVars.join(" ") + " ";
    command += "agents-cli run " + escapeShellArg(location);
    return command;
  }

  function updateCommand() {
    output.textContent = buildCommand();
  }

  locationInput.addEventListener("input", updateCommand);
  skipInput.addEventListener("change", updateCommand);
  mockInput.addEventListener("change", updateCommand);

  if (copyButton) {
    copyButton.addEventListener("click", function () {
      navigator.clipboard.writeText(buildCommand()).then(function () {
        copyButton.textContent = "Copied!";
        setTimeout(function () {
          copyButton.textContent = "Copy command";
        }, 1500);
      });
    });
  }

  updateCommand();
})();
</script>

## Run the Playground

Launch a local web UI for interactive testing. The server auto-reloads when you save changes to agent code:

```bash
agents-cli playground
```

Use the playground when you want to iterate on prompts, inspect agent behavior, or demo the assistant in a browser.

## Project Structure

- `app/`: Core agent code and pipeline logic.
- `tests/`: Unit and integration tests.
