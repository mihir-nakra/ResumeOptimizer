"""
Pytest configuration and shared fixtures.
"""
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_resume_text():
    """Sample resume text for testing."""
    return """
    John Doe
    Software Engineer

    Experience:
    - Senior Developer at Tech Corp (2020-2023)
    - Junior Developer at Startup Inc (2018-2020)

    Skills: Python, JavaScript, AWS, Docker
    """


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return """
    Senior Software Engineer

    Requirements:
    - 5+ years of Python experience
    - Experience with cloud platforms (AWS, GCP)
    - Strong understanding of microservices
    - Knowledge of Kubernetes and Docker
    """
