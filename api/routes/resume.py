"""
Resume optimization endpoints.
"""
import asyncio
import os
import uuid
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from api.store import request_store
from api.pipeline import run_pipeline, run_pipeline_from_data

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = "uploads"


class UploadResponse(BaseModel):
    request_id: str
    status: str


class OptimizationRequest(BaseModel):
    job_description: str
    resume_data: dict


class OptimizationResponse(BaseModel):
    request_id: str
    status: str


@router.post("/upload", response_model=UploadResponse)
async def upload_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """Upload a resume file and start the full optimization pipeline."""
    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '.{ext}'. Upload a PDF or DOCX file.",
        )

    request_id = str(uuid.uuid4())
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{request_id}.{ext}")

    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    request_store.create_request(request_id, file_path, job_description)

    asyncio.create_task(run_pipeline(request_id, file_path, ext, job_description))

    return UploadResponse(request_id=request_id, status="processing")


@router.get("/status/{request_id}", response_model=dict)
async def get_optimization_status(request_id: str):
    """Get the status of an optimization request, including per-stage progress."""
    req = request_store.get_request(request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return req


@router.post("/optimize", response_model=OptimizationResponse)
async def optimize_resume(request: OptimizationRequest):
    """
    Optimize resume from pre-parsed data (skips file upload and parsing).
    Runs ATS, Suggestions, and Interview generation in parallel.
    """
    request_id = str(uuid.uuid4())

    request_store.create_request(request_id, file_path="", job_description=request.job_description)
    request_store.update_stage(
        request_id, "parsing", "completed",
        result={"structured_data": request.resume_data},
    )

    asyncio.create_task(
        run_pipeline_from_data(request_id, request.resume_data, request.job_description)
    )

    return OptimizationResponse(request_id=request_id, status="processing")
