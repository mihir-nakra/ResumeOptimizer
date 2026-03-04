"""
Tests for Suggestion Generator Agent.
"""
import pytest
from agents.suggestion_generator import SuggestionGeneratorAgent, SuggestionState


@pytest.mark.asyncio
async def test_suggestion_agent_initialization():
    """Test that suggestion agent initializes correctly."""
    agent = SuggestionGeneratorAgent()
    assert agent.name == "suggestion_generator"


@pytest.mark.asyncio
async def test_analyze_gaps():
    """Test gap analysis between resume and job."""
    agent = SuggestionGeneratorAgent()
    state: SuggestionState = {
        "request_id": "test-123",
        "resume_data": {},
        "job_description": "Test job description",
        "gap_analysis": {},
        "suggestions": [],
        "priority_areas": [],
        "status": "pending",
        "error": None
    }
    result = await agent.analyze_gaps(state)
    assert result["status"] == "analyzing_gaps"


# TODO: Add more comprehensive tests
# - Test suggestion generation
# - Test prioritization logic
# - Test different types of suggestions
