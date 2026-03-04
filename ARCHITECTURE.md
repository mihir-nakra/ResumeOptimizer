# ResumeOptimizer — System Architecture

## Overview

ResumeOptimizer is a multi-agent backend system that optimizes resumes and generates interview questions. Four specialized AI agents — built with LangGraph — communicate through Apache Kafka, orchestrated by a FastAPI REST API. A client uploads a resume and job description, and the system parses the resume, optimizes it for ATS (Applicant Tracking Systems), generates improvement suggestions, and produces tailored interview questions — all in a single pipeline.

---

## End-to-End Client Flow

```
                                    ┌─────────────────────────────────────────────────┐
                                    │              FastAPI Application                 │
                                    │                                                 │
  Client (Postman / Frontend)       │   ┌─────────┐    ┌───────────┐    ┌──────────┐ │
  ─────────────────────────────     │   │ Routes  │───▶│ Pipeline  │───▶│  Agents  │ │
                                    │   └─────────┘    └─────┬─────┘    └────┬─────┘ │
  1. POST /upload                   │                        │               │       │
     (resume + job description)     │                   ┌────▼────┐     ┌────▼────┐  │
     ◀── { request_id }            │                   │  Store  │     │  Kafka  │  │
                                    │                   └─────────┘     └─────────┘  │
  2. GET /status/{request_id}       │                                                 │
     (poll until completed)         └─────────────────────────────────────────────────┘
     ◀── { stages, results }
```

### Step by step

1. **Client uploads a resume** — `POST /api/v1/resume/upload` with the resume file (PDF or DOCX) and a job description as form data.

2. **API saves the file and returns immediately** — The file is saved to `uploads/`, a UUID `request_id` is generated, and the response `{ request_id, status: "processing" }` is returned without waiting for any agents to finish.

3. **Pipeline launches as a background task** — `asyncio.create_task` kicks off `run_pipeline()`, which runs the four agents in sequence and in parallel.

4. **Stage 1 — Resume Parsing (sequential)** — The `ResumeParserAgent` validates the file, extracts raw text, and uses an LLM to structure it into a standardized format (contact info, experience, education, skills, etc.). The result is published to the `resume.parsed` Kafka topic.

5. **Stage 2 — Three agents in parallel** — Once parsing completes, three agents run concurrently via `asyncio.gather`:
   - `ATSOptimizerAgent` → publishes to `resume.ats_optimized`
   - `SuggestionGeneratorAgent` → publishes to `resume.suggestions`
   - `InterviewGeneratorAgent` → publishes to `interview.questions`

6. **Client polls for results** — `GET /api/v1/resume/status/{request_id}` returns the full request state, including per-stage status (`pending` / `running` / `completed` / `failed`) and results. The client polls this endpoint until the overall status is `completed`.

---

## Agent Architecture

Each agent is built on LangGraph's `StateGraph` — a directed graph where nodes are processing steps and edges define the execution flow. Every agent extends `BaseAgent`, which provides:

```python
class BaseAgent:
    def build_graph(self) -> StateGraph   # Override: define nodes and edges
    async def run(self, input_state) -> dict  # Compile graph, run it, return result
```

All agents use **Claude Sonnet 4** via AWS Bedrock (`ChatBedrockConverse`) with structured output — the LLM returns Pydantic models directly, not raw text.

### ResumeParserAgent

Validates, extracts text from, and structures resume files.

```
validate_file ──▶ extract_text ──▶ structure_data ──▶ END
      │                │
      ▼                ▼
   [error] ──▶ END  [error] ──▶ END
```

| Node | What it does |
|---|---|
| `validate_file` | Checks file exists, type is PDF/DOCX, not empty, under 10 MB |
| `extract_text` | PyPDF2 for PDFs, python-docx for DOCX files |
| `structure_data` | LLM extracts contact info, experience, education, skills, projects into a `StructuredResume` |

**State:** `ParserState` — `request_id`, `file_path`, `file_type`, `raw_text`, `structured_data`, `status`, `error`

**LLM config:** Temperature 0.0 (deterministic extraction)

---

### ATSOptimizerAgent

Analyzes keyword coverage against a job description and optimizes the resume to improve ATS match scores.

```
extract_keywords ──▶ analyze_match ──┬──▶ optimize_content ──▶ calculate_score ──▶ END
                                     │
                                     └──▶ calculate_score ──▶ END
                                          (skip if score ≥ 85%)
```

| Node | What it does |
|---|---|
| `extract_keywords` | LLM extracts categorized keywords from the job description (technical skills, soft skills, qualifications, experience requirements) |
| `analyze_match` | **Two-phase matching**: (1) deterministic substring search, then (2) LLM-based matching for uncertain keywords. Produces per-category match scores. |
| `optimize_content` | LLM rewrites resume sections to incorporate missing keywords naturally. Only runs if pre-optimization score is below 85%. |
| `calculate_score` | Weighted score: technical skills 40%, qualifications 25%, experience 20%, soft skills 15%. Output is 0–100. |

**State:** `ATSState` — `resume_data`, `job_description`, `keyword_set`, `match_analysis`, `optimized_sections`, `optimized_resume`, `ats_score`, `score_breakdown`, ...

**LLM config:** Temperature 0.1

---

### SuggestionGeneratorAgent

Identifies gaps between the resume and job requirements, then generates prioritized improvement suggestions.

```
analyze_gaps ──▶ generate_suggestions ──▶ prioritize ──▶ END
      │                  │
      ▼                  ▼
   [error] ──▶ END    [error] ──▶ END
```

| Node | What it does |
|---|---|
| `analyze_gaps` | LLM compares resume vs. job description, identifies gaps (missing skills, weak experience, missing qualifications, formatting issues, content quality) and strengths |
| `generate_suggestions` | For each gap, generates a concrete, actionable suggestion with an example. Never fabricates experience — focuses on rephrasing existing content and adding metrics. |
| `prioritize` | LLM reorders suggestions by impact (critical requirements first, quick wins second, polish last) and identifies top 3–5 priority areas |

**State:** `SuggestionState` — `resume_data`, `job_description`, `gap_analysis`, `suggestions`, `priority_areas`, ...

**LLM config:** Temperature 0.3

---

### InterviewGeneratorAgent

Generates targeted interview questions customized to both the job description and the candidate's resume.

```
extract_requirements ──▶ generate_technical ──▶ generate_behavioral ──▶ customize_to_resume ──▶ END
         │                       │                       │
         ▼                       ▼                       ▼
      [error] ──▶ END         [error] ──▶ END         [error] ──▶ END
```

| Node | What it does |
|---|---|
| `extract_requirements` | LLM parses job description into structured requirements: role title, skills, experience areas, responsibilities, seniority level |
| `generate_technical` | Generates 8–12 technical questions across difficulty levels. Includes system design questions for senior/lead roles. |
| `generate_behavioral` | Generates 5–8 behavioral/situational questions in STAR format. Leadership questions for senior/lead. |
| `customize_to_resume` | Adjusts questions to the specific candidate — reorders by comfort areas first, adds targeted follow-ups for resume claims/gaps, computes difficulty distribution |

**State:** `InterviewState` — `job_description`, `resume_data`, `requirements`, `technical_questions`, `behavioral_questions`, `questions`, `difficulty_levels`, ...

**LLM config:** Temperature 0.4

---

## Kafka Integration

Kafka serves as the communication backbone between agents. Each agent publishes its output to a dedicated topic after completing its work.

```
                          Kafka Cluster (localhost:9092)
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   resume.parsed          resume.ats_optimized                   │
│   ┌──────────┐           ┌───────────────────┐                  │
│   │ Parser   │           │ ATS Optimizer     │                  │
│   │ output   │           │ output            │                  │
│   └──────────┘           └───────────────────┘                  │
│                                                                 │
│   resume.suggestions     interview.questions                    │
│   ┌──────────────────┐   ┌───────────────────┐                  │
│   │ Suggestion       │   │ Interview         │                  │
│   │ output           │   │ output            │                  │
│   └──────────────────┘   └───────────────────┘                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Topics

| Topic | Producer | Content |
|---|---|---|
| `resume.parsed` | ResumeParserAgent | `{ request_id, structured_data }` |
| `resume.ats_optimized` | ATSOptimizerAgent | `{ request_id, ats_score, score_breakdown, optimized_resume, optimized_sections }` |
| `resume.suggestions` | SuggestionGeneratorAgent | `{ request_id, suggestions, priority_areas }` |
| `interview.questions` | InterviewGeneratorAgent | `{ request_id, questions, difficulty_levels, candidate_strengths_to_probe, potential_gaps_to_assess }` |

### Why Kafka?

- **Decoupled agents** — Each agent produces to and consumes from topics independently. Adding a new agent (e.g., a cover letter generator) means adding a new consumer on `resume.parsed` without modifying existing agents.
- **Event log** — Every intermediate result is persisted in Kafka. Useful for debugging, replaying pipelines, and auditing.
- **Horizontal scaling** — Multiple instances of the same agent can consume from a topic as a consumer group, distributing load across workers.
- **Resilience** — If a downstream agent is temporarily unavailable, messages wait in the topic until it comes back.

### Producer/Consumer Implementation

The `AgentProducer` (`messaging/producer.py`) wraps `kafka-python`'s `KafkaProducer`:

- Serializes messages as JSON
- `send_message(topic, message)` publishes and flushes
- Has graceful degradation code (currently disabled — Kafka is required on startup via `api/main.py`)

The `AgentConsumer` (`messaging/consumer.py`) wraps `kafka-python`'s `KafkaConsumer`:

- Deserializes JSON messages
- `consume(handler)` loops over messages and calls an async handler
- Available for future use cases (e.g., standalone consumer workers)

---

## Request Lifecycle

The `RequestStore` (`api/store.py`) is an in-memory dictionary that tracks the full state of each request across all pipeline stages.

```
Request created          Parsing          Parallel agents           Done
     │                     │                    │                    │
     ▼                     ▼                    ▼                    ▼
┌─────────┐  ┌──────────────────┐  ┌─────────────────────┐  ┌───────────┐
│processing│─▶│parsing: running  │─▶│ats: running         │─▶│ completed │
│         │  │                  │  │suggestions: running  │  │           │
│         │  │                  │  │interview: running    │  │           │
└─────────┘  └──────────────────┘  └─────────────────────┘  └───────────┘
```

Each stage transitions through: `pending` → `running` → `completed` (or `failed`)

The overall request status is `processing` until all stages finish, then becomes `completed` (or `failed` if any stage failed).

---

## REST API Endpoints

| Method | Path | Description | Response |
|---|---|---|---|
| `POST` | `/api/v1/resume/upload` | Upload resume file + job description. Starts full pipeline. | `{ request_id, status }` |
| `GET` | `/api/v1/resume/status/{id}` | Poll for pipeline progress and results. | Full request state with all stages |
| `POST` | `/api/v1/resume/optimize` | Submit pre-parsed resume data + job description. Skips parsing. | `{ request_id, status }` |
| `POST` | `/api/v1/interview/generate` | Generate interview questions (synchronous). | `{ questions, difficulty_levels, ... }` |
| `GET` | `/health` | Health check. | `{ status: "healthy" }` |
| `GET` | `/ready` | Readiness check. | `{ status: "ready" }` |

---

## Infrastructure

```
docker-compose.yml
├── zookeeper     (port 2181)  — Kafka coordination
├── kafka         (port 9092)  — Message broker
├── prometheus    (port 9090)  — Metrics collection (scrapes :8001)
└── grafana       (port 3000)  — Dashboards (admin/admin)
```

The FastAPI app runs outside Docker (`uvicorn` on port 8000) and connects to Kafka at `localhost:9092`. OpenTelemetry instrumentation exposes metrics on port 8001, which Prometheus scrapes every 15 seconds.

---

## LLM Integration

All four agents use **Claude Sonnet 4** (`us.anthropic.claude-sonnet-4-20250514-v1:0`) via **AWS Bedrock** through LangChain's `ChatBedrockConverse` client.

Each agent uses **structured output** — the LLM is constrained to return data matching a Pydantic model, so responses are always valid, typed, and parseable. No regex or manual JSON parsing needed.

Temperature is tuned per agent based on the task:

| Agent | Temperature | Rationale |
|---|---|---|
| ResumeParser | 0.0 | Deterministic extraction — same input should always produce the same structured output |
| ATSOptimizer | 0.1 | Mostly deterministic keyword matching with slight flexibility for rephrasing |
| SuggestionGenerator | 0.3 | Needs creativity for actionable suggestions while staying grounded |
| InterviewGenerator | 0.4 | Most creative — generating diverse, relevant questions |

---

## Directory Structure

```
ResumeOptimizer/
├── agents/
│   ├── base.py                    # BaseAgent — LangGraph StateGraph runner
│   ├── resume_parser.py           # File validation, text extraction, LLM structuring
│   ├── ats_optimizer.py           # Keyword extraction, matching, optimization, scoring
│   ├── suggestion_generator.py    # Gap analysis, suggestion generation, prioritization
│   └── interview_generator.py     # Requirements extraction, question generation, customization
├── api/
│   ├── config.py                  # Pydantic Settings — env vars, Kafka topics, LLM keys
│   ├── main.py                    # FastAPI app, CORS, OpenTelemetry, Kafka lifecycle
│   ├── store.py                   # In-memory RequestStore — tracks pipeline state
│   ├── pipeline.py                # Orchestrator — chains agents, publishes to Kafka
│   └── routes/
│       ├── health.py              # /health, /ready
│       ├── resume.py              # /upload, /status, /optimize
│       └── interview.py           # /generate
├── messaging/
│   ├── producer.py                # AgentProducer — Kafka JSON publisher
│   └── consumer.py                # AgentConsumer — Kafka JSON subscriber
├── monitoring/
│   └── prometheus.yml             # Prometheus scrape config
├── tests/                         # pytest suite (agents, API)
├── uploads/                       # Saved resume files (created at runtime)
├── docker-compose.yml             # Kafka, Zookeeper, Prometheus, Grafana
├── pyproject.toml                 # Poetry dependencies and tool config
└── .env                           # Environment variables (API keys, Kafka config)
```
