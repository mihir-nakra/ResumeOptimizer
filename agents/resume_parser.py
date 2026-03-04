"""
Resume Parser Agent - Extracts content from PDF/DOCX files and structures it via LLM.
"""
import os
from typing import TypedDict

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from api.config import settings
from .base import BaseAgent

# ---------------------------------------------------------------------------
# Pydantic models for structured LLM output
# ---------------------------------------------------------------------------

SUPPORTED_FILE_TYPES = {"pdf", "docx"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class ContactInfo(BaseModel):
    """Parsed contact information from a resume."""

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    website: str = ""


class ExperienceEntry(BaseModel):
    """A single work experience entry."""

    title: str
    company: str
    start_date: str = ""
    end_date: str = ""
    description: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    """A single education entry."""

    degree: str
    institution: str
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    details: list[str] = Field(default_factory=list)


class ProjectEntry(BaseModel):
    """A single project entry."""

    name: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    url: str = ""


class StructuredResume(BaseModel):
    """Complete structured resume parsed from raw text."""

    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ParserState(TypedDict):
    """State for resume parser agent."""

    request_id: str
    file_path: str
    file_type: str
    raw_text: str
    structured_data: dict
    status: str
    error: str | None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ResumeParserAgent(BaseAgent):
    """Agent responsible for parsing resume files."""

    def __init__(self) -> None:
        super().__init__("resume_parser")
        self.llm = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.0,
            region_name=settings.aws_region,
            max_tokens=4096,
        )

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> StateGraph:
        """Build the resume parser graph."""
        workflow = StateGraph(ParserState)

        workflow.add_node("validate_file", self.validate_file)
        workflow.add_node("extract_text", self.extract_text)
        workflow.add_node("structure_data", self.structure_data)

        workflow.set_entry_point("validate_file")
        workflow.add_conditional_edges(
            "validate_file",
            self._check_error,
            {"continue": "extract_text", "error": END},
        )
        workflow.add_conditional_edges(
            "extract_text",
            self._check_error,
            {"continue": "structure_data", "error": END},
        )
        workflow.add_edge("structure_data", END)

        return workflow

    def _check_error(self, state: ParserState) -> str:
        """Route to END on error, otherwise continue to the next node."""
        if state.get("error"):
            return "error"
        return "continue"

    # ------------------------------------------------------------------
    # Node: validate_file
    # ------------------------------------------------------------------

    async def validate_file(self, state: ParserState) -> dict:
        """Validate the uploaded file exists and is a supported type."""
        file_path = state.get("file_path", "")
        file_type = state.get("file_type", "").lower()

        if not file_path:
            return {"status": "error", "error": "No file path provided"}

        if file_type not in SUPPORTED_FILE_TYPES:
            return {
                "status": "error",
                "error": f"Unsupported file type '{file_type}'. Supported: {', '.join(SUPPORTED_FILE_TYPES)}",
            }

        if not os.path.exists(file_path):
            return {"status": "error", "error": f"File not found: {file_path}"}

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return {"status": "error", "error": "File is empty"}

        if file_size > MAX_FILE_SIZE_BYTES:
            return {
                "status": "error",
                "error": f"File exceeds maximum size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB",
            }

        return {"status": "validating"}

    # ------------------------------------------------------------------
    # Node: extract_text
    # ------------------------------------------------------------------

    async def extract_text(self, state: ParserState) -> dict:
        """Extract raw text from the uploaded PDF or DOCX file."""
        if state.get("error"):
            return {}

        file_path = state["file_path"]
        file_type = state["file_type"].lower()

        try:
            if file_type == "pdf":
                raw_text = self._extract_from_pdf(file_path)
            elif file_type == "docx":
                raw_text = self._extract_from_docx(file_path)
            else:
                return {"status": "error", "error": f"Unsupported file type: {file_type}"}

            if not raw_text.strip():
                return {"status": "error", "error": "No text could be extracted from the file"}

            return {"status": "extracting", "raw_text": raw_text}

        except Exception as e:
            return {"status": "error", "error": f"Text extraction failed: {e}"}

    # ------------------------------------------------------------------
    # Node: structure_data
    # ------------------------------------------------------------------

    async def structure_data(self, state: ParserState) -> dict:
        """Use LLM to parse raw resume text into structured sections."""
        if state.get("error"):
            return {}

        raw_text = state.get("raw_text", "")
        if not raw_text.strip():
            return {"status": "error", "error": "No raw text available to structure"}

        try:
            structured_llm = self.llm.with_structured_output(StructuredResume)

            result: StructuredResume = await structured_llm.ainvoke([
                SystemMessage(
                    content=(
                        "You are an expert resume parser. Extract all information from the "
                        "resume text and organize it into the structured format. Rules:\n"
                        "1. Extract ALL information — do not omit any details.\n"
                        "2. For experience entries, each bullet point should be a separate "
                        "item in the description list.\n"
                        "3. Normalize dates to a consistent format (e.g., 'Jan 2020', '2020').\n"
                        "4. If a section is not present in the resume, leave it empty.\n"
                        "5. List individual skills separately (split comma-separated lists).\n"
                        "6. Preserve the original wording — do not rephrase or embellish."
                    )
                ),
                HumanMessage(
                    content=f"Parse the following resume text into structured data:\n\n{raw_text}"
                ),
            ])

            return {
                "status": "completed",
                "structured_data": result.model_dump(),
            }

        except Exception as e:
            return {"status": "error", "error": f"Data structuring failed: {e}"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """Extract text from a PDF file using PyPDF2."""
        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)

    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """Extract text from a DOCX file using python-docx."""
        from docx import Document

        doc = Document(file_path)
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                paragraphs.append(text)
        return "\n".join(paragraphs)
