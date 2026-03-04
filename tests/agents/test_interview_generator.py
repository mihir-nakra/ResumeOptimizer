"""
Tests for Interview Generator Agent.
"""
import pytest
from agents.interview_generator import InterviewGeneratorAgent, InterviewState


@pytest.mark.asyncio
async def test_interview_agent_initialization():
    """Test that interview agent initializes correctly."""
    agent = InterviewGeneratorAgent()
    assert agent.name == "interview_generator"


@pytest.mark.asyncio
async def test_extract_requirements(sample_job_description):
    """Test requirement extraction from job description."""
    agent = InterviewGeneratorAgent()
    state: InterviewState = {
        "request_id": "test-123",
        "job_description": sample_job_description,
        "resume_data": {},
        "questions": [],
        "difficulty_levels": {},
        "status": "pending",
        "error": None
    }
    result = await agent.extract_requirements(state)
    assert result["status"] == "extracting_requirements"


# TODO: Add more comprehensive tests
# - Test technical question generation
# - Test behavioral question generation
# - Test resume-based customization
# - Test different difficulty levels
