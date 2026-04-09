---
title: IncidentResponseEnv
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
tags:
  - openenv
---

# IncidentResponseEnv

An [OpenEnv](https://github.com/openenv) environment where an AI agent acts as an on-call SRE managing a live production outage.

## Environment Description

The agent receives a stream of real-world production alerts — CPU spikes, database timeouts, memory leaks, HTTP 500 errors — and must:

1. Diagnose the root cause
2. Escalate correctly
3. Resolve services in the right order

This simulates one of the most high-stakes real engineering tasks: incident response. Every company with a production system does this. It genuinely challenges frontier models because multi-step causal reasoning is required.

## Action Space

Actions are strings chosen from a provided list of `available_actions`:

| Task   | Format | Example |
|--------|--------|---------|
| easy   | `identify:<service>` | `identify:payment-service` |
| medium | `diagnose:<root_cause>` | `diagnose:user-db` |
| hard   | `resolve:<svc1>:<act1>,resolve:<svc2>:<act2>,...` | `resolve:user-db:clear-disk,resolve:auth-service:restart,...` |

## Observation Space

Each observation contains:

| Field | Type | Description |
|-------|------|-------------|
| `task` | string | `easy`, `medium`, or `hard` |
| `step` | int | Current step number |
| `max_steps` | int | Maximum steps allowed |
| `alerts` | list | Stream of system alerts (service, type, severity, message) |
| `available_actions` | list | Valid action strings |
| `context` | string | Natural language description of the incident |
| `last_action_result` | string | Feedback from previous action |
| `last_action_error` | string | Error if last action was invalid |

## Tasks

### Easy — Single Signal (max 3 steps)
A single alert fires. The agent must identify which service is affected.
- Grader: exact match → 1.0 correct, 0.0 wrong
- Example: CPU spike on `auth-service` → `identify:auth-service`

### Medium — Correlated Alerts (max 5 steps)
Three alerts fire in sequence. The agent must identify the single root cause driving all three.
- Grader: exact match → 1.0 correct, 0.0 wrong
- Example: cache latency → auth slow → gateway 500s → `diagnose:cache`

### Hard — Cascading Failure (max 8 steps)
Four services fail in a cascade. The agent must provide the correct ordered resolution sequence.
- Grader: partial credit by positional match
  - 4/4 correct in order → 1.0
  - 3/4 → 0.75
  - 2/4 → 0.5
  - 1/4 → 0.25
  - All present, wrong order → 0.1
  - Otherwise → 0.0

## Reward Function

Reward is shaped over the full trajectory:
- Primary signal: grader score (0.0–1.0)
- Improvement bonus: small bonus for getting closer to correct answer
- Efficiency bonus: small bonus for solving quickly
- Invalid action penalty: -0.05 for submitting an action not in `available_actions`

## Baseline Scores

| Task | Model | Score |
|------|-------|-------|
| easy | Qwen/Qwen2.5-72B-Instruct | ~1.0 |
| medium | Qwen/Qwen2.5-72B-Instruct | ~0.8 |
| hard | Qwen/Qwen2.5-72B-Instruct | ~0.5 |

## Setup & Usage

### Local

```bash
cd incident-response-env
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t incident-response-env .
docker run -p 7860:7860 incident-response-env
```

### Run Inference

```bash
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export HF_TOKEN="your_token_here"
export SERVER_URL="http://localhost:7860"

python inference.py
```

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/reset` | Start a new episode |
| POST | `/step` | Take an action |
| POST | `/state` | Get current state |
| GET | `/tasks` | List all tasks |
| GET | `/health` | Health check |

#### Example: Reset

```bash
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task": "easy", "incident_index": 0}'
```

#### Example: Step

```bash
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"task": "easy", "action": "identify:payment-service"}'
```

## Project Structure

```
incident-response-env/
├── env/
│   ├── __init__.py
│   ├── environment.py    # Core OpenEnv class
│   ├── models.py         # Pydantic models
│   ├── dataset.py        # Synthetic incident catalog
│   ├── graders.py        # Task 1, 2, 3 graders
│   └── reward.py         # Reward shaping logic
├── app.py                # FastAPI server
├── inference.py          # Baseline LLM agent
├── openenv.yaml          # OpenEnv metadata
├── Dockerfile
├── requirements.txt
└── README.md
```
