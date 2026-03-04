"""
Health check endpoints.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}


@router.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes/load balancers."""
    # TODO: Check Kafka connection
    # TODO: Check agent availability
    return {"status": "ready"}
