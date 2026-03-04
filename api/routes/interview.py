"""
Interview question generation endpoints.
"""
import uuid
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from agents.interview_generator import InterviewGeneratorAgent
from api.config import settings
from api.pipeline import get_producer

logger = logging.getLogger(__name__)
router = APIRouter()


class InterviewRequest(BaseModel):
    job_description: str
    resume_data: dict | None = None
    difficulty: str = "medium"


class InterviewResponse(BaseModel):
    request_id: str
    questions: list[dict]
    difficulty_levels: dict
    candidate_strengths_to_probe: list[str] = []
    potential_gaps_to_assess: list[str] = []


@router.post("/generate", response_model=InterviewResponse)
async def generate_questions(request: InterviewRequest):
    """Generate interview questions based on job description and optional resume data."""
    request_id = str(uuid.uuid4())
    resume_data = request.resume_data or {}

    try:
        agent = InterviewGeneratorAgent()
        result = await agent.run({
            "request_id": request_id,
            "job_description": request.job_description,
            "resume_data": resume_data,
            "requirements": {},
            "technical_questions": [],
            "behavioral_questions": [],
            "questions": [],
            "candidate_strengths_to_probe": [],
            "potential_gaps_to_assess": [],
            "difficulty_levels": {},
            "status": "pending",
            "error": None,
        })
    except Exception as exc:
        logger.exception("Interview generation failed")
        raise HTTPException(status_code=500, detail=f"Interview generation failed: {exc}")

    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])

    producer = get_producer()
    if producer:
        await producer.send_message(
            settings.kafka_topic_interviews,
            {"request_id": request_id, "questions": result.get("questions", [])},
        )

    return InterviewResponse(
        request_id=request_id,
        questions=result.get("questions", []),
        difficulty_levels=result.get("difficulty_levels", {}),
        candidate_strengths_to_probe=result.get("candidate_strengths_to_probe", []),
        potential_gaps_to_assess=result.get("potential_gaps_to_assess", []),
    )
