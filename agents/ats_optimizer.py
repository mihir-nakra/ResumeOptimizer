"""
ATS Optimizer Agent - Optimizes resumes for Applicant Tracking Systems.
"""
import json
from typing import Any, TypedDict

from langchain_aws import ChatBedrockConverse
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from api.config import settings
from .base import BaseAgent

# ---------------------------------------------------------------------------
# Pydantic models for structured LLM output
# ---------------------------------------------------------------------------


class KeywordSet(BaseModel):
    """A categorized set of keywords extracted from a job description."""

    technical_skills: list[str] = Field(
        default_factory=list,
        description="Programming languages, frameworks, tools, databases, platforms",
    )
    soft_skills: list[str] = Field(
        default_factory=list,
        description="Communication, leadership, teamwork, problem-solving, etc.",
    )
    qualifications: list[str] = Field(
        default_factory=list,
        description="Degrees, certifications, clearances, licenses",
    )
    experience_requirements: list[str] = Field(
        default_factory=list,
        description="Years of experience, specific role experience, domain expertise",
    )


class KeywordMatch(BaseModel):
    """Match status for a single keyword against the resume."""

    keyword: str
    category: str
    status: str  # "present", "missing", or "partial"
    evidence: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class MatchAnalysis(BaseModel):
    """Complete match analysis across all keyword categories."""

    matches: list[KeywordMatch]
    category_scores: dict[str, float]
    overall_pre_optimization_score: float = Field(ge=0.0, le=1.0)
    missing_keywords: list[str]
    partial_keywords: list[str]


class OptimizedSection(BaseModel):
    """An optimized version of a single resume section."""

    section_name: str
    original_content: str
    optimized_content: str
    keywords_incorporated: list[str]
    changes_summary: str


class LLMMatchResult(BaseModel):
    """Wrapper for LLM keyword matching output."""

    matches: list[KeywordMatch]


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ATSState(TypedDict):
    """State for ATS optimizer agent."""

    request_id: str
    resume_data: dict
    job_description: str

    # Populated by extract_keywords
    keyword_set: dict

    # Populated by analyze_match
    match_analysis: dict

    # Populated by optimize_content
    optimized_sections: list[dict]
    optimized_resume: dict

    # Populated by calculate_score
    ats_score: float
    score_breakdown: dict

    status: str
    error: str | None


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORY_WEIGHTS: dict[str, float] = {
    "technical_skills": 0.40,
    "soft_skills": 0.15,
    "qualifications": 0.25,
    "experience_requirements": 0.20,
}

HIGH_SCORE_THRESHOLD = 0.85

OPTIMIZABLE_SECTIONS = {"summary", "experience", "skills", "education", "projects"}


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ATSOptimizerAgent(BaseAgent):
    """Agent responsible for ATS optimization."""

    def __init__(self) -> None:
        super().__init__("ats_optimizer")
        self.llm = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.1,
            region_name=settings.aws_region,
            max_tokens=4096,
        )

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> StateGraph:
        """Build the ATS optimizer graph."""
        workflow = StateGraph(ATSState)

        workflow.add_node("extract_keywords", self.extract_keywords)
        workflow.add_node("analyze_match", self.analyze_match)
        workflow.add_node("optimize_content", self.optimize_content)
        workflow.add_node("calculate_score", self.calculate_score)

        workflow.set_entry_point("extract_keywords")
        workflow.add_edge("extract_keywords", "analyze_match")

        # Conditional: skip optimization when the resume already scores well
        workflow.add_conditional_edges(
            "analyze_match",
            self._should_optimize,
            {
                "optimize": "optimize_content",
                "skip": "calculate_score",
            },
        )

        workflow.add_edge("optimize_content", "calculate_score")
        workflow.add_edge("calculate_score", END)

        return workflow

    def _should_optimize(self, state: ATSState) -> str:
        """Route: skip optimization if pre-score is already high or on error."""
        if state.get("error"):
            return "skip"

        match_analysis = state.get("match_analysis", {})
        pre_score = match_analysis.get("overall_pre_optimization_score", 0.0)

        if pre_score >= HIGH_SCORE_THRESHOLD:
            return "skip"
        return "optimize"

    # ------------------------------------------------------------------
    # Node: extract_keywords
    # ------------------------------------------------------------------

    async def extract_keywords(self, state: ATSState) -> dict:
        """Extract categorized keywords from the job description using LLM."""
        try:
            structured_llm = self.llm.with_structured_output(KeywordSet)

            result: KeywordSet = await structured_llm.ainvoke([
                SystemMessage(
                    content=(
                        "You are an expert ATS (Applicant Tracking System) analyst. "
                        "Extract all important keywords and requirements from the job "
                        "description. Categorize each keyword into exactly one category. "
                        "Be thorough: include specific technologies, version numbers, "
                        "methodologies, and both explicit and implied requirements. "
                        "Normalize keywords to their canonical form "
                        '(e.g., "k8s" -> "Kubernetes").'
                    )
                ),
                HumanMessage(
                    content=(
                        "Extract categorized keywords from this job description:\n\n"
                        f"{state['job_description']}"
                    )
                ),
            ])

            return {
                "status": "extracting_keywords",
                "keyword_set": result.model_dump(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Keyword extraction failed: {e}",
            }

    # ------------------------------------------------------------------
    # Node: analyze_match
    # ------------------------------------------------------------------

    async def analyze_match(self, state: ATSState) -> dict:
        """Analyze keyword match between resume and job description."""
        if state.get("error"):
            return {}

        try:
            keyword_set = KeywordSet(**state["keyword_set"])
            resume_data = state["resume_data"]
            resume_text = self._flatten_resume_text(resume_data).lower()

            matches: list[KeywordMatch] = []
            categories = {
                "technical_skills": keyword_set.technical_skills,
                "soft_skills": keyword_set.soft_skills,
                "qualifications": keyword_set.qualifications,
                "experience_requirements": keyword_set.experience_requirements,
            }

            # Phase 1: deterministic substring matching
            uncertain_keywords: list[tuple[str, str]] = []
            for category_name, keywords in categories.items():
                for kw in keywords:
                    kw_lower = kw.lower()
                    if kw_lower in resume_text:
                        idx = resume_text.index(kw_lower)
                        start = max(0, idx - 30)
                        end = min(len(resume_text), idx + len(kw_lower) + 30)
                        evidence = resume_text[start:end].strip()
                        matches.append(
                            KeywordMatch(
                                keyword=kw,
                                category=category_name,
                                status="present",
                                evidence=f"...{evidence}...",
                                confidence=1.0,
                            )
                        )
                    else:
                        uncertain_keywords.append((kw, category_name))

            # Phase 2: LLM-based matching for uncertain keywords
            if uncertain_keywords:
                llm_matches = await self._llm_match_keywords(
                    uncertain_keywords, resume_text
                )
                matches.extend(llm_matches)

            # Compute per-category scores
            category_scores: dict[str, float] = {}
            for category_name in categories:
                cat_matches = [m for m in matches if m.category == category_name]
                if not cat_matches:
                    category_scores[category_name] = 0.0
                    continue
                score_sum = sum(
                    1.0 if m.status == "present" else 0.5 if m.status == "partial" else 0.0
                    for m in cat_matches
                )
                category_scores[category_name] = score_sum / len(cat_matches)

            missing = [m.keyword for m in matches if m.status == "missing"]
            partial = [m.keyword for m in matches if m.status == "partial"]

            active_scores = [s for s in category_scores.values()]
            overall = sum(active_scores) / len(active_scores) if active_scores else 0.0

            analysis = MatchAnalysis(
                matches=matches,
                category_scores=category_scores,
                overall_pre_optimization_score=overall,
                missing_keywords=missing,
                partial_keywords=partial,
            )

            return {
                "status": "analyzing",
                "match_analysis": analysis.model_dump(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Match analysis failed: {e}",
            }

    # ------------------------------------------------------------------
    # Node: optimize_content
    # ------------------------------------------------------------------

    async def optimize_content(self, state: ATSState) -> dict:
        """Optimize resume content to incorporate missing keywords naturally."""
        if state.get("error"):
            return {}

        try:
            analysis = MatchAnalysis(**state["match_analysis"])
            resume_data = state["resume_data"]

            missing_and_partial = analysis.missing_keywords + analysis.partial_keywords

            if not missing_and_partial:
                return {
                    "status": "optimizing",
                    "optimized_sections": [],
                    "optimized_resume": resume_data,
                }

            sections_to_optimize = {
                k: v
                for k, v in resume_data.items()
                if k.lower() in OPTIMIZABLE_SECTIONS and v
            }

            structured_llm = self.llm.with_structured_output(OptimizedSection)
            optimized_sections: list[dict] = []

            for section_name, section_content in sections_to_optimize.items():
                if isinstance(section_content, (dict, list)):
                    content_str = json.dumps(section_content, indent=2)
                else:
                    content_str = str(section_content)

                result: OptimizedSection = await structured_llm.ainvoke([
                    SystemMessage(
                        content=(
                            "You are an expert resume writer specializing in ATS optimization. "
                            "Rewrite the given resume section to naturally incorporate the "
                            "missing keywords where truthfully applicable. Rules:\n"
                            "1. Do NOT fabricate experience or skills the candidate does not have.\n"
                            "2. DO rephrase existing content to use ATS-friendly terminology.\n"
                            "3. DO add keywords to skills sections where the candidate likely has "
                            "the skill based on their other listed experience.\n"
                            "4. Keep the tone professional and consistent with the original.\n"
                            "5. Preserve all factual information (dates, company names, titles).\n"
                            "6. For the 'skills' section, you may add keywords as new entries.\n"
                            "7. Return the optimized content in the same format as the original."
                        )
                    ),
                    HumanMessage(
                        content=(
                            f"Section: {section_name}\n\n"
                            f"Original content:\n{content_str}\n\n"
                            f"Missing/partial keywords to incorporate where appropriate:\n"
                            f"{', '.join(missing_and_partial)}\n\n"
                            f"Full job description for context:\n{state['job_description']}"
                        )
                    ),
                ])

                result.section_name = section_name
                result.original_content = content_str
                optimized_sections.append(result.model_dump())

            # Merge optimized sections back into resume
            optimized_resume = dict(resume_data)
            for section in optimized_sections:
                name = section["section_name"]
                content = section["optimized_content"]
                try:
                    optimized_resume[name] = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    optimized_resume[name] = content

            return {
                "status": "optimizing",
                "optimized_sections": optimized_sections,
                "optimized_resume": optimized_resume,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Content optimization failed: {e}",
            }

    # ------------------------------------------------------------------
    # Node: calculate_score
    # ------------------------------------------------------------------

    async def calculate_score(self, state: ATSState) -> dict:
        """Calculate weighted ATS score based on keyword coverage."""
        if state.get("error"):
            return {"ats_score": 0.0, "status": "error"}

        try:
            keyword_set = KeywordSet(**state["keyword_set"])
            optimized_resume = state.get("optimized_resume", state["resume_data"])
            resume_text = self._flatten_resume_text(optimized_resume).lower()

            categories = {
                "technical_skills": keyword_set.technical_skills,
                "soft_skills": keyword_set.soft_skills,
                "qualifications": keyword_set.qualifications,
                "experience_requirements": keyword_set.experience_requirements,
            }

            score_breakdown: dict[str, dict] = {}
            weighted_total = 0.0
            weight_total = 0.0

            for category_name, keywords in categories.items():
                if not keywords:
                    score_breakdown[category_name] = {
                        "matched": 0,
                        "total": 0,
                        "rate": 0.0,
                        "weighted_contribution": 0.0,
                    }
                    continue

                matched = sum(1 for kw in keywords if kw.lower() in resume_text)
                rate = matched / len(keywords)
                weight = CATEGORY_WEIGHTS.get(category_name, 0.25)
                contribution = rate * weight

                score_breakdown[category_name] = {
                    "matched": matched,
                    "total": len(keywords),
                    "rate": round(rate, 4),
                    "weighted_contribution": round(contribution, 4),
                }

                weighted_total += contribution
                weight_total += weight

            if weight_total > 0:
                final_score = round((weighted_total / weight_total) * 100, 1)
            else:
                final_score = 0.0

            return {
                "ats_score": final_score,
                "score_breakdown": score_breakdown,
                "status": "completed",
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Score calculation failed: {e}",
                "ats_score": 0.0,
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _flatten_resume_text(self, resume_data: dict) -> str:
        """Recursively flatten resume_data into a single searchable string."""
        parts: list[str] = []

        def _recurse(obj: Any) -> None:
            if isinstance(obj, str):
                parts.append(obj)
            elif isinstance(obj, list):
                for item in obj:
                    _recurse(item)
            elif isinstance(obj, dict):
                for value in obj.values():
                    _recurse(value)

        _recurse(resume_data)
        return " ".join(parts)

    async def _llm_match_keywords(
        self,
        uncertain_keywords: list[tuple[str, str]],
        resume_text: str,
    ) -> list[KeywordMatch]:
        """Use LLM to classify uncertain keywords as present/partial/missing."""
        keywords_str = "\n".join(
            f"- {kw} (category: {cat})" for kw, cat in uncertain_keywords
        )

        # Truncate to avoid token limits
        truncated_resume = resume_text[:3000]

        structured_llm = self.llm.with_structured_output(LLMMatchResult)

        result: LLMMatchResult = await structured_llm.ainvoke([
            SystemMessage(
                content=(
                    "You are an expert resume analyst. For each keyword below, determine "
                    "if the resume demonstrates the skill/requirement, even through "
                    "synonyms, related technologies, or implied experience. Classify each "
                    "as 'present' (clearly demonstrated), 'partial' (related experience "
                    "but not exact match), or 'missing' (not found). Provide evidence text "
                    "from the resume when status is 'present' or 'partial'. Set confidence "
                    "between 0.0 and 1.0."
                )
            ),
            HumanMessage(
                content=(
                    f"Resume content:\n{truncated_resume}\n\n"
                    f"Keywords to match:\n{keywords_str}"
                )
            ),
        ])

        return result.matches
