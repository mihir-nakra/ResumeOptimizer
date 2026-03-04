"""
Tests for Resume Parser Agent.
"""
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.resume_parser import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    MAX_FILE_SIZE_BYTES,
    ParserState,
    ProjectEntry,
    ResumeParserAgent,
    StructuredResume,
    SUPPORTED_FILE_TYPES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**overrides) -> ParserState:
    """Create a ParserState with sensible defaults, overridden by kwargs."""
    defaults: ParserState = {
        "request_id": "test-123",
        "file_path": "/tmp/test.pdf",
        "file_type": "pdf",
        "raw_text": "",
        "structured_data": {},
        "status": "pending",
        "error": None,
    }
    defaults.update(overrides)
    return defaults


SAMPLE_RESUME_TEXT = """
John Doe
Software Engineer
john.doe@email.com | (555) 123-4567 | San Francisco, CA
linkedin.com/in/johndoe

Summary:
Experienced software engineer with 5+ years building scalable web applications.

Experience:
Senior Developer at Tech Corp (2020-2023)
- Led migration of monolithic application to microservices architecture
- Reduced API response times by 40% through caching optimizations

Junior Developer at Startup Inc (2018-2020)
- Built RESTful APIs using Python and FastAPI
- Implemented CI/CD pipelines with GitHub Actions

Education:
B.S. Computer Science, Stanford University (2014-2018)
GPA: 3.8

Skills: Python, JavaScript, AWS, Docker, Kubernetes, FastAPI, PostgreSQL

Certifications:
AWS Solutions Architect Associate

Projects:
OpenSource CLI Tool - A command-line tool for automating deployments
Technologies: Python, Docker, GitHub Actions
"""


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parser_agent_initialization():
    """Test that parser agent initializes correctly."""
    agent = ResumeParserAgent()
    assert agent.name == "resume_parser"


def test_build_graph_returns_state_graph():
    """Test that build_graph returns a valid StateGraph."""
    agent = ResumeParserAgent()
    graph = agent.build_graph()
    assert graph is not None


# ---------------------------------------------------------------------------
# validate_file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_file_success():
    """Test validation succeeds for a valid file."""
    agent = ResumeParserAgent()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(b"fake pdf content")
        tmp_path = f.name
    try:
        state = _make_state(file_path=tmp_path, file_type="pdf")
        result = await agent.validate_file(state)
        assert result["status"] == "validating"
        assert "error" not in result
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_validate_file_no_path():
    """Test validation fails when no file path is provided."""
    agent = ResumeParserAgent()
    state = _make_state(file_path="", file_type="pdf")
    result = await agent.validate_file(state)
    assert result["status"] == "error"
    assert "No file path" in result["error"]


@pytest.mark.asyncio
async def test_validate_file_unsupported_type():
    """Test validation fails for unsupported file types."""
    agent = ResumeParserAgent()
    state = _make_state(file_type="txt")
    result = await agent.validate_file(state)
    assert result["status"] == "error"
    assert "Unsupported file type" in result["error"]


@pytest.mark.asyncio
async def test_validate_file_not_found():
    """Test validation fails when file does not exist."""
    agent = ResumeParserAgent()
    state = _make_state(file_path="/nonexistent/file.pdf", file_type="pdf")
    result = await agent.validate_file(state)
    assert result["status"] == "error"
    assert "File not found" in result["error"]


@pytest.mark.asyncio
async def test_validate_file_empty():
    """Test validation fails for an empty file."""
    agent = ResumeParserAgent()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name  # file is 0 bytes
    try:
        state = _make_state(file_path=tmp_path, file_type="pdf")
        result = await agent.validate_file(state)
        assert result["status"] == "error"
        assert "empty" in result["error"].lower()
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_validate_file_too_large():
    """Test validation fails when file exceeds size limit."""
    agent = ResumeParserAgent()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
        # Write just over the limit
        f.write(b"x" * (MAX_FILE_SIZE_BYTES + 1))
    try:
        state = _make_state(file_path=tmp_path, file_type="pdf")
        result = await agent.validate_file(state)
        assert result["status"] == "error"
        assert "maximum size" in result["error"].lower()
    finally:
        os.unlink(tmp_path)


@pytest.mark.asyncio
async def test_validate_file_docx_type():
    """Test validation accepts DOCX files."""
    agent = ResumeParserAgent()
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        f.write(b"fake docx content")
        tmp_path = f.name
    try:
        state = _make_state(file_path=tmp_path, file_type="docx")
        result = await agent.validate_file(state)
        assert result["status"] == "validating"
    finally:
        os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# extract_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_text_pdf():
    """Test PDF text extraction delegates to _extract_from_pdf."""
    agent = ResumeParserAgent()
    state = _make_state(file_path="/tmp/test.pdf", file_type="pdf")

    with patch.object(agent, "_extract_from_pdf", return_value="Extracted PDF text"):
        result = await agent.extract_text(state)
        assert result["status"] == "extracting"
        assert result["raw_text"] == "Extracted PDF text"


@pytest.mark.asyncio
async def test_extract_text_docx():
    """Test DOCX text extraction delegates to _extract_from_docx."""
    agent = ResumeParserAgent()
    state = _make_state(file_path="/tmp/test.docx", file_type="docx")

    with patch.object(agent, "_extract_from_docx", return_value="Extracted DOCX text"):
        result = await agent.extract_text(state)
        assert result["status"] == "extracting"
        assert result["raw_text"] == "Extracted DOCX text"


@pytest.mark.asyncio
async def test_extract_text_empty_result():
    """Test extraction fails when no text is extracted."""
    agent = ResumeParserAgent()
    state = _make_state(file_path="/tmp/test.pdf", file_type="pdf")

    with patch.object(agent, "_extract_from_pdf", return_value="   "):
        result = await agent.extract_text(state)
        assert result["status"] == "error"
        assert "No text could be extracted" in result["error"]


@pytest.mark.asyncio
async def test_extract_text_exception():
    """Test extraction handles exceptions gracefully."""
    agent = ResumeParserAgent()
    state = _make_state(file_path="/tmp/test.pdf", file_type="pdf")

    with patch.object(agent, "_extract_from_pdf", side_effect=RuntimeError("corrupt file")):
        result = await agent.extract_text(state)
        assert result["status"] == "error"
        assert "Text extraction failed" in result["error"]


@pytest.mark.asyncio
async def test_extract_text_skips_on_error():
    """Test extraction is skipped if state already has an error."""
    agent = ResumeParserAgent()
    state = _make_state(error="previous error")
    result = await agent.extract_text(state)
    assert result == {}


# ---------------------------------------------------------------------------
# _extract_from_pdf / _extract_from_docx helpers
# ---------------------------------------------------------------------------


def test_extract_from_pdf():
    """Test PDF extraction using a mocked PdfReader."""
    page1 = MagicMock()
    page1.extract_text.return_value = "Page 1 content"
    page2 = MagicMock()
    page2.extract_text.return_value = "Page 2 content"

    mock_reader = MagicMock()
    mock_reader.pages = [page1, page2]

    with patch("PyPDF2.PdfReader", return_value=mock_reader):
        result = ResumeParserAgent._extract_from_pdf("/tmp/test.pdf")
        assert result == "Page 1 content\n\nPage 2 content"


def test_extract_from_pdf_skips_empty_pages():
    """Test that pages with no text are skipped."""
    page1 = MagicMock()
    page1.extract_text.return_value = "Content"
    page2 = MagicMock()
    page2.extract_text.return_value = None
    page3 = MagicMock()
    page3.extract_text.return_value = "More content"

    mock_reader = MagicMock()
    mock_reader.pages = [page1, page2, page3]

    with patch("PyPDF2.PdfReader", return_value=mock_reader):
        result = ResumeParserAgent._extract_from_pdf("/tmp/test.pdf")
        assert result == "Content\n\nMore content"


def test_extract_from_docx():
    """Test DOCX extraction using a mocked Document."""
    para1 = MagicMock()
    para1.text = "Paragraph 1"
    para2 = MagicMock()
    para2.text = "  "  # whitespace-only, should be skipped
    para3 = MagicMock()
    para3.text = "Paragraph 3"

    mock_doc = MagicMock()
    mock_doc.paragraphs = [para1, para2, para3]

    with patch("docx.Document", return_value=mock_doc):
        result = ResumeParserAgent._extract_from_docx("/tmp/test.docx")
        assert result == "Paragraph 1\nParagraph 3"


# ---------------------------------------------------------------------------
# structure_data
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_structure_data_success():
    """Test LLM-based structuring returns structured data."""
    agent = ResumeParserAgent()

    mock_structured_resume = StructuredResume(
        contact_info=ContactInfo(name="John Doe", email="john@email.com"),
        summary="Experienced software engineer",
        experience=[
            ExperienceEntry(
                title="Senior Developer",
                company="Tech Corp",
                start_date="2020",
                end_date="2023",
                description=["Led migration to microservices"],
            )
        ],
        education=[
            EducationEntry(
                degree="B.S. Computer Science",
                institution="Stanford University",
            )
        ],
        skills=["Python", "JavaScript", "AWS"],
        certifications=["AWS Solutions Architect Associate"],
        projects=[
            ProjectEntry(name="CLI Tool", description="Automation tool", technologies=["Python"])
        ],
    )

    mock_llm = AsyncMock(return_value=mock_structured_resume)

    state = _make_state(raw_text=SAMPLE_RESUME_TEXT)
    with patch.object(agent.llm, "with_structured_output", return_value=mock_llm):
        result = await agent.structure_data(state)

    assert result["status"] == "completed"
    assert result["structured_data"]["contact_info"]["name"] == "John Doe"
    assert len(result["structured_data"]["experience"]) == 1
    assert result["structured_data"]["skills"] == ["Python", "JavaScript", "AWS"]


@pytest.mark.asyncio
async def test_structure_data_empty_text():
    """Test structuring fails when raw_text is empty."""
    agent = ResumeParserAgent()
    state = _make_state(raw_text="")
    result = await agent.structure_data(state)
    assert result["status"] == "error"
    assert "No raw text" in result["error"]


@pytest.mark.asyncio
async def test_structure_data_llm_exception():
    """Test structuring handles LLM errors gracefully."""
    agent = ResumeParserAgent()

    mock_llm = AsyncMock(side_effect=RuntimeError("LLM service unavailable"))

    state = _make_state(raw_text=SAMPLE_RESUME_TEXT)
    with patch.object(agent.llm, "with_structured_output", return_value=mock_llm):
        result = await agent.structure_data(state)

    assert result["status"] == "error"
    assert "Data structuring failed" in result["error"]


@pytest.mark.asyncio
async def test_structure_data_skips_on_error():
    """Test structuring is skipped if state already has an error."""
    agent = ResumeParserAgent()
    state = _make_state(error="previous error")
    result = await agent.structure_data(state)
    assert result == {}


# ---------------------------------------------------------------------------
# Graph routing (_check_error)
# ---------------------------------------------------------------------------


def test_check_error_continues():
    """Test routing continues when no error is present."""
    agent = ResumeParserAgent()
    state = _make_state(error=None)
    assert agent._check_error(state) == "continue"


def test_check_error_routes_to_error():
    """Test routing goes to error when error is set."""
    agent = ResumeParserAgent()
    state = _make_state(error="Something failed")
    assert agent._check_error(state) == "error"


# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------


def test_structured_resume_defaults():
    """Test StructuredResume has sensible defaults for all fields."""
    resume = StructuredResume()
    assert resume.contact_info.name == ""
    assert resume.summary == ""
    assert resume.experience == []
    assert resume.education == []
    assert resume.skills == []
    assert resume.certifications == []
    assert resume.projects == []


def test_structured_resume_serialization():
    """Test StructuredResume can round-trip through model_dump."""
    resume = StructuredResume(
        contact_info=ContactInfo(name="Jane Smith"),
        skills=["Python", "Go"],
    )
    data = resume.model_dump()
    restored = StructuredResume(**data)
    assert restored.contact_info.name == "Jane Smith"
    assert restored.skills == ["Python", "Go"]


def test_supported_file_types():
    """Test supported file types include pdf and docx."""
    assert "pdf" in SUPPORTED_FILE_TYPES
    assert "docx" in SUPPORTED_FILE_TYPES
