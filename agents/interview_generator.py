"""
Interview Generator Agent - Creates interview questions from job descriptions
and customizes them based on the candidate's resume.
"""
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


class JobRequirements(BaseModel):
    """Structured requirements extracted from a job description."""

    role_title: str = Field(
        default="",
        description="The job title or role name",
    )
    technical_skills: list[str] = Field(
        default_factory=list,
        description="Required technical skills, languages, frameworks, and tools",
    )
    soft_skills: list[str] = Field(
        default_factory=list,
        description="Required soft skills and interpersonal abilities",
    )
    experience_areas: list[str] = Field(
        default_factory=list,
        description="Key areas of experience required (e.g., 'distributed systems', "
        "'team leadership')",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Core responsibilities of the role",
    )
    seniority_level: str = Field(
        default="mid",
        description="Estimated seniority: 'junior', 'mid', 'senior', or 'lead'",
    )


class InterviewQuestion(BaseModel):
    """A single interview question with metadata."""

    question: str = Field(description="The interview question text")
    category: str = Field(
        description="Question category: 'technical', 'behavioral', 'situational', "
        "or 'system_design'",
    )
    difficulty: str = Field(
        default="medium",
        description="Difficulty level: 'easy', 'medium', or 'hard'",
    )
    skill_assessed: str = Field(
        default="",
        description="The primary skill or competency this question evaluates",
    )
    follow_ups: list[str] = Field(
        default_factory=list,
        description="Follow-up questions to probe deeper",
    )
    what_to_look_for: str = Field(
        default="",
        description="Key points a strong answer should cover",
    )


class QuestionSet(BaseModel):
    """A collection of interview questions."""

    questions: list[InterviewQuestion] = Field(default_factory=list)


class CustomizedQuestionSet(BaseModel):
    """Questions tailored to a specific candidate's resume."""

    questions: list[InterviewQuestion] = Field(default_factory=list)
    candidate_strengths_to_probe: list[str] = Field(
        default_factory=list,
        description="Candidate strengths worth exploring in the interview",
    )
    potential_gaps_to_assess: list[str] = Field(
        default_factory=list,
        description="Areas where the candidate may have gaps to assess",
    )


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class InterviewState(TypedDict):
    """State for interview generator agent."""

    request_id: str
    job_description: str
    resume_data: dict

    # Populated by extract_requirements
    requirements: dict

    # Populated by generate_technical
    technical_questions: list[dict]

    # Populated by generate_behavioral
    behavioral_questions: list[dict]

    # Populated by customize_to_resume
    questions: list[dict]
    candidate_strengths_to_probe: list[str]
    potential_gaps_to_assess: list[str]

    difficulty_levels: dict
    status: str
    error: str | None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class InterviewGeneratorAgent(BaseAgent):
    """Agent responsible for generating interview questions."""

    def __init__(self) -> None:
        super().__init__("interview_generator")
        self.llm = ChatBedrockConverse(
            model="us.anthropic.claude-sonnet-4-20250514-v1:0",
            temperature=0.4,
            region_name=settings.aws_region,
            max_tokens=4096,
        )

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build_graph(self) -> StateGraph:
        """Build the interview generator graph."""
        workflow = StateGraph(InterviewState)

        workflow.add_node("extract_requirements", self.extract_requirements)
        workflow.add_node("generate_technical", self.generate_technical)
        workflow.add_node("generate_behavioral", self.generate_behavioral)
        workflow.add_node("customize_to_resume", self.customize_to_resume)

        workflow.set_entry_point("extract_requirements")
        workflow.add_conditional_edges(
            "extract_requirements",
            self._check_error,
            {"continue": "generate_technical", "error": END},
        )
        workflow.add_conditional_edges(
            "generate_technical",
            self._check_error,
            {"continue": "generate_behavioral", "error": END},
        )
        workflow.add_conditional_edges(
            "generate_behavioral",
            self._check_error,
            {"continue": "customize_to_resume", "error": END},
        )
        workflow.add_edge("customize_to_resume", END)

        return workflow

    def _check_error(self, state: InterviewState) -> str:
        """Route to END on error, otherwise continue to the next node."""
        if state.get("error"):
            return "error"
        return "continue"

    # ------------------------------------------------------------------
    # Node: extract_requirements
    # ------------------------------------------------------------------

    async def extract_requirements(self, state: InterviewState) -> dict:
        """Extract key requirements from the job description using LLM."""
        try:
            structured_llm = self.llm.with_structured_output(JobRequirements)

            result: JobRequirements = await structured_llm.ainvoke([
                SystemMessage(
                    content=(
                        "You are an expert technical recruiter and interviewer. "
                        "Analyze the job description and extract structured requirements "
                        "that will be used to generate targeted interview questions. "
                        "Be thorough: capture both explicit requirements and skills "
                        "implied by the responsibilities. Estimate the seniority level "
                        "based on the requirements and language used."
                    )
                ),
                HumanMessage(
                    content=(
                        "Extract structured requirements from this job description:\n\n"
                        f"{state['job_description']}"
                    )
                ),
            ])

            return {
                "status": "extracting_requirements",
                "requirements": result.model_dump(),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Requirement extraction failed: {e}",
            }

    # ------------------------------------------------------------------
    # Node: generate_technical
    # ------------------------------------------------------------------

    async def generate_technical(self, state: InterviewState) -> dict:
        """Generate technical interview questions based on extracted requirements."""
        if state.get("error"):
            return {}

        try:
            requirements = JobRequirements(**state["requirements"])

            skills_str = ", ".join(requirements.technical_skills) or "None specified"
            experience_str = ", ".join(requirements.experience_areas) or "None specified"
            responsibilities_str = "\n".join(
                f"- {r}" for r in requirements.responsibilities
            ) or "None specified"

            structured_llm = self.llm.with_structured_output(QuestionSet)

            result: QuestionSet = await structured_llm.ainvoke([
                SystemMessage(
                    content=(
                        "You are an expert technical interviewer. Generate technical "
                        "interview questions for the given role. Rules:\n"
                        "1. Cover the key technical skills and experience areas.\n"
                        "2. Include a mix of difficulties: some 'easy' warmup questions, "
                        "several 'medium' core questions, and a few 'hard' deep-dive questions.\n"
                        "3. For senior/lead roles, include system design questions.\n"
                        "4. Each question should assess a specific skill.\n"
                        "5. Provide 2-3 follow-up questions for each to probe deeper.\n"
                        "6. Describe what a strong answer looks like in 'what_to_look_for'.\n"
                        "7. Generate 8-12 technical questions total.\n"
                        "8. Use category 'technical' for coding/knowledge questions and "
                        "'system_design' for architecture questions."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Role: {requirements.role_title}\n"
                        f"Seniority: {requirements.seniority_level}\n\n"
                        f"Technical Skills: {skills_str}\n\n"
                        f"Experience Areas: {experience_str}\n\n"
                        f"Responsibilities:\n{responsibilities_str}"
                    )
                ),
            ])

            return {
                "status": "generating_technical",
                "technical_questions": [q.model_dump() for q in result.questions],
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Technical question generation failed: {e}",
            }

    # ------------------------------------------------------------------
    # Node: generate_behavioral
    # ------------------------------------------------------------------

    async def generate_behavioral(self, state: InterviewState) -> dict:
        """Generate behavioral interview questions based on role requirements."""
        if state.get("error"):
            return {}

        try:
            requirements = JobRequirements(**state["requirements"])

            soft_skills_str = ", ".join(requirements.soft_skills) or "None specified"
            responsibilities_str = "\n".join(
                f"- {r}" for r in requirements.responsibilities
            ) or "None specified"

            structured_llm = self.llm.with_structured_output(QuestionSet)

            result: QuestionSet = await structured_llm.ainvoke([
                SystemMessage(
                    content=(
                        "You are an expert behavioral interviewer. Generate behavioral "
                        "and situational interview questions for the given role. Rules:\n"
                        "1. Use the STAR format style (Situation, Task, Action, Result) "
                        "for behavioral questions.\n"
                        "2. Cover soft skills, teamwork, conflict resolution, leadership, "
                        "and role-specific scenarios.\n"
                        "3. For senior/lead roles, include questions about mentoring, "
                        "cross-team collaboration, and technical decision-making.\n"
                        "4. Each question should assess a specific competency.\n"
                        "5. Provide 2-3 follow-up questions to probe for specifics.\n"
                        "6. Describe what a strong answer looks like in 'what_to_look_for'.\n"
                        "7. Generate 5-8 behavioral/situational questions total.\n"
                        "8. Use category 'behavioral' for past-experience questions and "
                        "'situational' for hypothetical scenario questions."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Role: {requirements.role_title}\n"
                        f"Seniority: {requirements.seniority_level}\n\n"
                        f"Soft Skills: {soft_skills_str}\n\n"
                        f"Responsibilities:\n{responsibilities_str}"
                    )
                ),
            ])

            return {
                "status": "generating_behavioral",
                "behavioral_questions": [q.model_dump() for q in result.questions],
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Behavioral question generation failed: {e}",
            }

    # ------------------------------------------------------------------
    # Node: customize_to_resume
    # ------------------------------------------------------------------

    async def customize_to_resume(self, state: InterviewState) -> dict:
        """Customize and finalize questions based on the candidate's resume."""
        if state.get("error"):
            return {}

        try:
            resume_data = state["resume_data"]
            resume_text = self._flatten_resume_text(resume_data)

            all_questions = (
                state.get("technical_questions", [])
                + state.get("behavioral_questions", [])
            )

            if not all_questions:
                return {
                    "status": "completed",
                    "questions": [],
                    "candidate_strengths_to_probe": [],
                    "potential_gaps_to_assess": [],
                    "difficulty_levels": {"easy": 0, "medium": 0, "hard": 0},
                }

            questions_str = "\n\n".join(
                f"[{q['category'].upper()}] ({q['difficulty']}) {q['question']}\n"
                f"  Skill assessed: {q['skill_assessed']}"
                for q in all_questions
            )

            structured_llm = self.llm.with_structured_output(CustomizedQuestionSet)

            result: CustomizedQuestionSet = await structured_llm.ainvoke([
                SystemMessage(
                    content=(
                        "You are an expert interviewer preparing for a specific candidate. "
                        "Review the candidate's resume and the generated interview questions. "
                        "Customize the question set:\n"
                        "1. Adjust questions to reference the candidate's specific experience "
                        "where relevant (e.g., 'You worked at X on Y, tell me about...').\n"
                        "2. Add targeted follow-ups based on resume claims that need verification.\n"
                        "3. Identify candidate strengths worth probing deeper in the interview.\n"
                        "4. Identify potential gaps between the resume and role requirements.\n"
                        "5. Reorder questions to start with the candidate's comfort areas "
                        "before moving to gaps.\n"
                        "6. Keep all original question metadata (category, difficulty, "
                        "skill_assessed, what_to_look_for) and update as needed.\n"
                        "7. You may add 1-2 extra questions specifically targeting resume claims "
                        "or gaps, but do not remove existing questions."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Candidate Resume:\n{resume_text}\n\n"
                        f"Job Description:\n{state['job_description']}\n\n"
                        f"Generated Questions:\n{questions_str}"
                    )
                ),
            ])

            questions = [q.model_dump() for q in result.questions]

            difficulty_levels = {"easy": 0, "medium": 0, "hard": 0}
            for q in result.questions:
                if q.difficulty in difficulty_levels:
                    difficulty_levels[q.difficulty] += 1

            return {
                "status": "completed",
                "questions": questions,
                "candidate_strengths_to_probe": result.candidate_strengths_to_probe,
                "potential_gaps_to_assess": result.potential_gaps_to_assess,
                "difficulty_levels": difficulty_levels,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Resume customization failed: {e}",
            }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _flatten_resume_text(resume_data: dict) -> str:
        """Recursively flatten resume_data into a single readable string."""
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
