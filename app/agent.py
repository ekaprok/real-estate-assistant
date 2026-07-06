# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

import datetime
from zoneinfo import ZoneInfo
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.apps import App

import os
import google.auth
import google.auth.exceptions

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

dev_key = os.environ.get("GOOGLE_API_KEY_DEV")
if dev_key and not any(p in dev_key.lower() for p in ["your_", "placeholder", "key_here"]):
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    os.environ["GEMINI_API_KEY"] = dev_key
else:
    # Graceful authentication handling for Vertex AI
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    try:
        _, project_id = google.auth.default()
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    except Exception:
        os.environ["GOOGLE_CLOUD_PROJECT"] = os.environ.get("GOOGLE_CLOUD_PROJECT", "fake-project")



class StrReportAgent(BaseAgent):
    """The root agent for the Real Estate Assistant.

    Takes user location preferences and outputs a structured STR compliance & ROI report.
    """
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        user_prompt = ""
        if ctx.user_content and ctx.user_content.parts:
            user_prompt = "".join(part.text for part in ctx.user_content.parts if part.text)

        if not user_prompt:
            # Fallback to session events history
            for event in reversed(ctx.session.events):
                if event.author == "user" and event.content and event.content.parts:
                    user_prompt = "".join(part.text for part in event.content.parts if part.text)
                    if user_prompt:
                        break

        if not user_prompt:
            user_prompt = "Can I operate a short term rental in Gatlinburg, TN?"

        # Execute the deterministic 5-step analysis funnel
        from app.pipeline import run_pipeline
        report_yaml = run_pipeline(user_prompt)

        from google.genai import types as genai_types
        yield Event(
            author=self.name,
            content=genai_types.Content(
                role="model",
                parts=[genai_types.Part.from_text(text=report_yaml)]
            )
        )


# Instantiate the StrReportAgent as the root agent
root_agent = StrReportAgent(
    name="root_agent",
    description="Automated Short-Term Rental Legality & ROI Assistant"
)

app = App(
    root_agent=root_agent,
    name="app",
)
