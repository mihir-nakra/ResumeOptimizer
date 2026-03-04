# ResumeOptimizer

A multi-agent backend system to optimize resumes and generate interview questions using LangGraph, with Kafka-based orchestration and comprehensive monitoring.

## Overview

ResumeOptimizer uses a multi-agent architecture where specialized agents handle different aspects of resume optimization:
- **Resume Parser**: Extracts content from PDF/DOCX files
- **ATS Optimizer**: Optimizes resumes for Applicant Tracking Systems
- **Suggestion Generator**: Provides AI-powered improvement suggestions
- **Interview Generator**: Creates interview questions based on job descriptions

## Architecture

- **LangGraph Agents**: Individual agents with specific responsibilities
- **Kafka**: Message broker for inter-agent communication
- **OpenTelemetry**: Distributed tracing and metrics collection
- **Grafana**: Monitoring dashboards and visualization
- **Docker**: Containerization for consistent deployment
- **AWS EC2**: Production deployment environment

## Quick Start

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- Poetry (for dependency management)

### Installation

```bash
# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Development

```bash
# Run individual agent tests
poetry run pytest tests/agents/test_resume_parser.py
poetry run pytest tests/agents/test_ats_optimizer.py
poetry run pytest tests/agents/test_suggestion_generator.py
poetry run pytest tests/agents/test_interview_generator.py

# Run all tests
poetry run pytest

# Start local Kafka (for integration testing)
docker-compose up -d kafka zookeeper

# Run the API server
poetry run uvicorn api.main:app --reload --port 8000

# Start monitoring stack
docker-compose up -d grafana prometheus
```

## Project Status

**Current Phase**: Initial Setup
- [ ] Phase 1: Build and test individual LangGraph agents
- [ ] Phase 2: Set up Kafka for agent communication
- [ ] Phase 3: Integrate OpenTelemetry monitoring
- [ ] Phase 4: Set up Grafana dashboards
- [ ] Phase 5: Containerize with Docker
- [ ] Phase 6: Deploy to AWS EC2

## Goals

- Achieve 30%+ boost in ATS job match scores
- Provide intelligent resume optimization suggestions
- Generate relevant interview questions from job descriptions
