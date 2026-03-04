"""
Pipeline orchestrator: chains agents, publishes to Kafka, updates the request store.
"""
import asyncio
import logging
from typing import Any

from agents.resume_parser import ResumeParserAgent
from agents.ats_optimizer import ATSOptimizerAgent
from agents.suggestion_generator import SuggestionGeneratorAgent
from agents.interview_generator import InterviewGeneratorAgent
from api.config import settings
from api.store import request_store
from messaging.producer import AgentProducer

logger = logging.getLogger(__name__)

_producer: AgentProducer | None = None


def set_producer(producer: AgentProducer) -> None:
    global _producer
    _producer = producer


def get_producer() -> AgentProducer | None:
    return _producer


# ---------------------------------------------------------------------------
# Individual stage runners
# ---------------------------------------------------------------------------


async def _run_ats_optimization(
    request_id: str,
    structured_data: dict[str, Any],
    job_description: str,
) -> dict[str, Any]:
    request_store.update_stage(request_id, "ats_optimization", "running")
    try:
        agent = ATSOptimizerAgent()
        result = await agent.run({
            "request_id": request_id,
            "resume_data": structured_data,
            "job_description": job_description,
            "keyword_set": {},
            "match_analysis": {},
            "optimized_sections": [],
            "optimized_resume": {},
            "ats_score": 0.0,
            "score_breakdown": {},
            "status": "pending",
            "error": None,
        })

        if result.get("error"):
            request_store.update_stage(
                request_id, "ats_optimization", "failed", error=result["error"]
            )
            return result

        stage_result = {
            "ats_score": result.get("ats_score", 0.0),
            "score_breakdown": result.get("score_breakdown", {}),
            "optimized_resume": result.get("optimized_resume", {}),
            "optimized_sections": result.get("optimized_sections", []),
        }
        request_store.update_stage(
            request_id, "ats_optimization", "completed", result=stage_result
        )

        if _producer:
            await _producer.send_message(
                settings.kafka_topic_ats_optimized,
                {"request_id": request_id, **stage_result},
            )

        return result

    except Exception as exc:
        error_msg = f"ATS optimization failed: {exc}"
        logger.exception(error_msg)
        request_store.update_stage(
            request_id, "ats_optimization", "failed", error=error_msg
        )
        return {"error": error_msg}


async def _run_suggestion_generation(
    request_id: str,
    structured_data: dict[str, Any],
    job_description: str,
) -> dict[str, Any]:
    request_store.update_stage(request_id, "suggestions", "running")
    try:
        agent = SuggestionGeneratorAgent()
        result = await agent.run({
            "request_id": request_id,
            "resume_data": structured_data,
            "job_description": job_description,
            "gap_analysis": {},
            "suggestions": [],
            "priority_areas": [],
            "status": "pending",
            "error": None,
        })

        if result.get("error"):
            request_store.update_stage(
                request_id, "suggestions", "failed", error=result["error"]
            )
            return result

        stage_result = {
            "suggestions": result.get("suggestions", []),
            "priority_areas": result.get("priority_areas", []),
        }
        request_store.update_stage(
            request_id, "suggestions", "completed", result=stage_result
        )

        if _producer:
            await _producer.send_message(
                settings.kafka_topic_suggestions,
                {"request_id": request_id, **stage_result},
            )

        return result

    except Exception as exc:
        error_msg = f"Suggestion generation failed: {exc}"
        logger.exception(error_msg)
        request_store.update_stage(
            request_id, "suggestions", "failed", error=error_msg
        )
        return {"error": error_msg}


async def _run_interview_generation(
    request_id: str,
    structured_data: dict[str, Any],
    job_description: str,
) -> dict[str, Any]:
    request_store.update_stage(request_id, "interview", "running")
    try:
        agent = InterviewGeneratorAgent()
        result = await agent.run({
            "request_id": request_id,
            "job_description": job_description,
            "resume_data": structured_data,
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

        if result.get("error"):
            request_store.update_stage(
                request_id, "interview", "failed", error=result["error"]
            )
            return result

        stage_result = {
            "questions": result.get("questions", []),
            "difficulty_levels": result.get("difficulty_levels", {}),
            "candidate_strengths_to_probe": result.get("candidate_strengths_to_probe", []),
            "potential_gaps_to_assess": result.get("potential_gaps_to_assess", []),
        }
        request_store.update_stage(
            request_id, "interview", "completed", result=stage_result
        )

        if _producer:
            await _producer.send_message(
                settings.kafka_topic_interviews,
                {"request_id": request_id, **stage_result},
            )

        return result

    except Exception as exc:
        error_msg = f"Interview generation failed: {exc}"
        logger.exception(error_msg)
        request_store.update_stage(
            request_id, "interview", "failed", error=error_msg
        )
        return {"error": error_msg}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def run_pipeline(
    request_id: str,
    file_path: str,
    file_type: str,
    job_description: str,
) -> None:
    """
    Full pipeline: parse -> (ATS + Suggestions + Interview) in parallel.
    Runs as an asyncio background task. Updates the request store throughout.
    """
    # --- Stage 1: Parsing ---
    request_store.update_stage(request_id, "parsing", "running")
    try:
        parser = ResumeParserAgent()
        parse_result = await parser.run({
            "request_id": request_id,
            "file_path": file_path,
            "file_type": file_type,
            "raw_text": "",
            "structured_data": {},
            "status": "pending",
            "error": None,
        })
    except Exception as exc:
        error_msg = f"Resume parsing crashed: {exc}"
        logger.exception(error_msg)
        request_store.update_stage(request_id, "parsing", "failed", error=error_msg)
        request_store.set_overall_status(request_id, "failed", error=error_msg)
        return

    if parse_result.get("error"):
        request_store.update_stage(
            request_id, "parsing", "failed", error=parse_result["error"]
        )
        request_store.set_overall_status(
            request_id, "failed", error=parse_result["error"]
        )
        return

    structured_data = parse_result.get("structured_data", {})
    request_store.update_stage(
        request_id, "parsing", "completed", result={"structured_data": structured_data}
    )

    # Publish parsed resume to Kafka
    if _producer:
        await _producer.send_message(
            settings.kafka_topic_resume_parsed,
            {"request_id": request_id, "structured_data": structured_data},
        )

    # --- Stage 2: Parallel agents ---
    results = await asyncio.gather(
        _run_ats_optimization(request_id, structured_data, job_description),
        _run_suggestion_generation(request_id, structured_data, job_description),
        _run_interview_generation(request_id, structured_data, job_description),
        return_exceptions=True,
    )

    any_failed = any(isinstance(r, Exception) for r in results)
    if any_failed:
        request_store.set_overall_status(
            request_id, "failed", error="One or more pipeline stages failed"
        )
    else:
        request_store.set_overall_status(request_id, "completed")

    logger.info("Pipeline completed for request %s", request_id)


async def run_pipeline_from_data(
    request_id: str,
    structured_data: dict[str, Any],
    job_description: str,
) -> None:
    """
    Partial pipeline: skip parsing, run ATS + Suggestions + Interview in parallel.
    Used by the /optimize endpoint when resume_data is provided directly.
    """
    results = await asyncio.gather(
        _run_ats_optimization(request_id, structured_data, job_description),
        _run_suggestion_generation(request_id, structured_data, job_description),
        _run_interview_generation(request_id, structured_data, job_description),
        return_exceptions=True,
    )

    any_failed = any(isinstance(r, Exception) for r in results)
    if any_failed:
        request_store.set_overall_status(
            request_id, "failed", error="One or more pipeline stages failed"
        )
    else:
        request_store.set_overall_status(request_id, "completed")
