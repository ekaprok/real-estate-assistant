"""Unit tests for conversational error handling in the root agent."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

from app.agent import StrReportAgent


@pytest.mark.asyncio
async def test_agent_formats_pipeline_error_as_conversational_text():
    error_yaml = yaml.dump(
        {
            "error": "Scope too broad",
            "message": "Please name up to 5 specific cities.",
        }
    )

    agent = StrReportAgent(name="root_agent")
    part = MagicMock()
    part.text = "Bay Area"
    ctx = MagicMock()
    ctx.user_content = MagicMock()
    ctx.user_content.parts = [part]

    with patch("app.pipeline.run_pipeline", return_value=error_yaml):
        events = [event async for event in agent._run_async_impl(ctx)]

    assert len(events) == 1
    text = events[0].content.parts[0].text
    assert "I'd love to help" in text
    assert "Please name up to 5 specific cities." in text
    assert "error:" not in text.lower()
