"""
FastAPI server for IncidentResponseEnv.
Exposes /reset, /step, /state endpoints per OpenEnv spec.
The validation script pings POST /reset — must return HTTP 200.
"""
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from env import IncidentResponseEnv, IncidentAction

app = FastAPI(
    title="IncidentResponseEnv",
    description="OpenEnv environment: AI agent manages a live production outage",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Global environment instances — one per task
# ---------------------------------------------------------------------------
_envs: dict = {}


def get_env(task: str = "easy", incident_index: int = 0) -> IncidentResponseEnv:
    key = f"{task}_{incident_index}"
    if key not in _envs:
        _envs[key] = IncidentResponseEnv(task=task, incident_index=incident_index)
    return _envs[key]


# ---------------------------------------------------------------------------
# Request/response schemas for the HTTP layer
# ---------------------------------------------------------------------------
class ResetRequest(BaseModel):
    task: Optional[str] = "easy"
    incident_index: Optional[int] = 0


class StepRequest(BaseModel):
    action: str
    task: Optional[str] = "easy"
    incident_index: Optional[int] = 0


class StateRequest(BaseModel):
    task: Optional[str] = "easy"
    incident_index: Optional[int] = 0


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    return {"status": "ok", "env": "IncidentResponseEnv", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# POST /reset — start a new episode
# ---------------------------------------------------------------------------
@app.post("/reset")
def reset(req: ResetRequest = None):
    if req is None:
        req = ResetRequest()
    task = req.task or "easy"
    idx = req.incident_index or 0
    try:
        env = get_env(task, idx)
        result = env.reset()
        return JSONResponse(content=result.model_dump(), status_code=200)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /step — agent takes an action
# ---------------------------------------------------------------------------
@app.post("/step")
def step(req: StepRequest):
    task = req.task or "easy"
    idx = req.incident_index or 0
    try:
        env = get_env(task, idx)
        action = IncidentAction(action=req.action)
        result = env.step(action)
        return JSONResponse(content=result.model_dump(), status_code=200)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------------------------------------------------------------------
# POST /state — get current environment state
# ---------------------------------------------------------------------------
@app.post("/state")
def state(req: StateRequest = None):
    if req is None:
        req = StateRequest()
    task = req.task or "easy"
    idx = req.incident_index or 0
    env = get_env(task, idx)
    return JSONResponse(content=env.state(), status_code=200)


# ---------------------------------------------------------------------------
# GET /metadata — environment metadata
# ---------------------------------------------------------------------------
@app.get("/metadata")
def metadata():
    return {
        "name": "IncidentResponseEnv",
        "description": (
            "An OpenEnv environment where an AI agent manages a live production outage. "
            "The agent receives system alerts and must diagnose root causes and resolve services."
        ),
        "version": "1.0.0",
        "tags": ["openenv", "incident-response", "sre", "real-world"],
    }


# ---------------------------------------------------------------------------
# GET /schema — action, observation, state schemas
# ---------------------------------------------------------------------------
@app.get("/schema")
def schema():
    return {
        "action": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Action string chosen from available_actions"
                }
            },
            "required": ["action"]
        },
        "observation": {
            "type": "object",
            "properties": {
                "task":                {"type": "string"},
                "step":                {"type": "integer"},
                "max_steps":           {"type": "integer"},
                "alerts":              {"type": "array"},
                "available_actions":   {"type": "array"},
                "context":             {"type": "string"},
                "last_action_result":  {"type": ["string", "null"]},
                "last_action_error":   {"type": ["string", "null"]},
            }
        },
        "state": {
            "type": "object",
            "properties": {
                "task":         {"type": "string"},
                "incident_id":  {"type": "string"},
                "step":         {"type": "integer"},
                "max_steps":    {"type": "integer"},
                "done":         {"type": "boolean"},
                "best_grade":   {"type": "number"},
                "final_score":  {"type": "number"},
            }
        }
    }


# ---------------------------------------------------------------------------
# POST /mcp — JSON-RPC 2.0 endpoint
# ---------------------------------------------------------------------------
@app.post("/mcp")
async def mcp(request: Request):
    """JSON-RPC 2.0 endpoint — accepts any body."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    return {
        "jsonrpc": "2.0",
        "id": body.get("id", 1),
        "result": {
            "method": body.get("method", "ping"),
            "status": "ok",
            "env": "incident-response-env",
        },
    }



@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "name": "easy",
                "description": "Single-signal alert: identify the affected service",
                "difficulty": "easy",
                "max_steps": 3,
                "reward_range": [0.0, 1.0],
            },
            {
                "name": "medium",
                "description": "3 correlated alerts: identify the root cause",
                "difficulty": "medium",
                "max_steps": 5,
                "reward_range": [0.0, 1.0],
            },
            {
                "name": "hard",
                "description": "Cascading failure across 4 services: correct ordered resolution",
                "difficulty": "hard",
                "max_steps": 8,
                "reward_range": [0.0, 1.0],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    import uvicorn
    port = int(os.getenv("PORT", 7860))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
