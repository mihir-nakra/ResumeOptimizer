"""
In-memory request state store for tracking pipeline progress.
"""
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

STAGE_NAMES = ("parsing", "ats_optimization", "suggestions", "interview")


def _new_stage() -> dict[str, Any]:
    return {"status": "pending", "result": None, "error": None}


class RequestStore:
    """Tracks request state across the optimization pipeline."""

    def __init__(self) -> None:
        self._requests: dict[str, dict[str, Any]] = {}

    def create_request(
        self,
        request_id: str,
        file_path: str,
        job_description: str,
    ) -> dict[str, Any]:
        entry = {
            "request_id": request_id,
            "status": "processing",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "file_path": file_path,
            "job_description": job_description,
            "stages": {name: _new_stage() for name in STAGE_NAMES},
            "error": None,
        }
        self._requests[request_id] = entry
        logger.info("Created request %s", request_id)
        return entry

    def update_stage(
        self,
        request_id: str,
        stage: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        req = self._requests.get(request_id)
        if req is None:
            logger.warning("update_stage: request %s not found", request_id)
            return
        req["stages"][stage]["status"] = status
        if result is not None:
            req["stages"][stage]["result"] = result
        if error is not None:
            req["stages"][stage]["error"] = error

    def set_overall_status(
        self,
        request_id: str,
        status: str,
        error: str | None = None,
    ) -> None:
        req = self._requests.get(request_id)
        if req is None:
            return
        req["status"] = status
        if error:
            req["error"] = error

    def get_request(self, request_id: str) -> dict[str, Any] | None:
        return self._requests.get(request_id)


request_store = RequestStore()
