# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ResumeOptimizer is a multi-agent backend system that optimizes resumes and generates interview questions using LangGraph. Four specialized agents communicate via Kafka to parse resumes, optimize for ATS scoring, generate improvement suggestions, and create interview questions.

## Development Commands

```bash
# Install dependencies
poetry install

# Run all tests
poetry run pytest

# Run a single test file
poetry run pytest tests/agents/test_resume_parser.py

# Run a single test by name
poetry run pytest tests/agents/test_resume_parser.py -k "test_validate_file_success"

# Run tests with coverage
poetry run pytest --cov=agents --cov=api --cov=messaging

# Format, lint, type-check
poetry run black .
poetry run ruff check .
poetry run mypy agents/ api/ messaging/

# Start Kafka infrastructure (required for full pipeline)
docker-compose up -d kafka zookeeper

# Run API server
poetry run uvicorn api.main:app --reload --port 8000
```

## Architecture

### Agent System

All agents extend `BaseAgent` (`agents/base.py`) which provides:
- A `StateGraph` instance and abstract `build_graph()` method
- An async `run(input_state)` method that compiles and invokes the graph

Each agent defines its own `TypedDict` state class and implements a multi-node LangGraph pipeline with conditional edges for error handling (nodes check for prior errors via `_check_error` and short-circuit to `END`).

**Agents and their graph nodes:**
- **ResumeParserAgent**: validate_file → extract_text → structure_data
- **ATSOptimizerAgent**: extract_keywords → analyze_match → optimize_content → calculate_score
- **SuggestionGeneratorAgent**: analyze_gaps → generate_suggestions → prioritize
- **InterviewGeneratorAgent**: extract_requirements → generate_technical → generate_behavioral → customize_to_resume

### Pipeline Orchestration (`api/pipeline.py`)

The pipeline runs parsing first (sequential), then launches ATS optimization, suggestion generation, and interview generation **in parallel** via `asyncio.gather()`. Results are published to Kafka topics and tracked per-stage in `RequestStore` (`api/store.py`), which maintains in-memory state with stages: pending → running → completed/failed.

### Key Implementation Patterns

**Structured LLM output**: All agents use `llm.with_structured_output(PydanticModel)` to get type-safe responses. No manual JSON parsing — Pydantic models define the expected schema.

**LLM configuration**: All agents use AWS Bedrock Claude Sonnet 4 (`langchain-aws`). Temperature varies by agent purpose: 0.0 (parser, deterministic) → 0.1 (ATS) → 0.3 (suggestions) → 0.4 (interview, most creative).

**Two-phase keyword matching** (ATS optimizer): Phase 1 does deterministic substring matching; Phase 2 uses LLM for ambiguous keywords (synonyms, implied skills).

**Async throughout**: All agent nodes are `async def`, all LLM calls use `.ainvoke()`.

**Kafka graceful degradation**: `messaging/producer.py` and `messaging/consumer.py` fail silently when Kafka is unavailable — messages are logged but pipeline continues.

**Configuration**: `api/config.py` uses `pydantic-settings` to load from environment variables / `.env` file. Access via the `settings` singleton.

### Testing Patterns

Tests use `pytest-asyncio` with `@pytest.mark.asyncio`. Agent tests call individual node methods directly (e.g., `agent.validate_file(state)`) rather than running the full graph. Shared fixtures in `tests/conftest.py` provide a FastAPI `TestClient`, sample resume text, and sample job description. Manual integration test scripts (`test_*_manual.py`) exist in the project root.
