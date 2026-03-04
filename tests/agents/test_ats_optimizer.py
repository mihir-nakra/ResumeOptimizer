"""
Tests for ATS Optimizer Agent.
"""
import pytest
from agents.ats_optimizer import ATSOptimizerAgent, ATSState


@pytest.mark.asyncio
async def test_ats_agent_initialization():
    """Test that ATS agent initializes correctly."""
    agent = ATSOptimizerAgent()
    assert agent.name == "ats_optimizer"


@pytest.mark.asyncio
async def test_extract_keywords(sample_job_description):
    """Test keyword extraction from job description."""
    agent = ATSOptimizerAgent()
    state: ATSState = {
        "request_id": "test-123",
        "resume_data": {},
        "job_description": sample_job_description,
        "keywords": [],
        "optimized_resume": {},
        "ats_score": 0.0,
        "status": "pending",
        "error": None
    }
    result = await agent.extract_keywords(state)
    assert result["status"] == "extracting_keywords"


# TODO: Add more comprehensive tests
# - Test keyword matching
# - Test optimization logic
# - Test score calculation
# - Test with real job descriptions
