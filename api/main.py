"""
Main FastAPI application entry point.
"""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .routes import health, resume, interview
from .config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ResumeOptimizer API",
    description="Multi-agent system for resume optimization and interview preparation",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(resume.router, prefix="/api/v1/resume", tags=["resume"])
app.include_router(interview.router, prefix="/api/v1/interview", tags=["interview"])

# OpenTelemetry instrumentation
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    os.makedirs("uploads", exist_ok=True)
    logger.info("Uploads directory ready")

    from messaging.producer import AgentProducer
    from api.pipeline import set_producer

    producer = AgentProducer()
    app.state.producer = producer
    set_producer(producer)

    if producer.is_connected:
        logger.info("Kafka producer initialized successfully")
    else:
        # To allow running without Kafka, replace `raise` with:
        #     logger.warning("Running without Kafka -- messages will be logged only")
        raise RuntimeError(
            "Kafka is not available. Start Kafka with: docker-compose up -d kafka zookeeper"
        )


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    producer = getattr(app.state, "producer", None)
    if producer is not None:
        producer.close()
        logger.info("Kafka producer closed")
