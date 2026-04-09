"""
Pydantic models for IncidentResponseEnv.
Defines Observation, Action, and Reward types per OpenEnv spec.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Alert model — a single system alert signal
# ---------------------------------------------------------------------------
class Alert(BaseModel):
    service: str = Field(..., description="Service emitting the alert")
    alert_type: str = Field(..., description="Type: cpu_spike | db_timeout | memory_leak | http_500 | disk_full | latency_high")
    severity: str = Field(..., description="low | medium | high | critical")
    message: str = Field(..., description="Human-readable alert message")
    timestamp: float = Field(..., description="Unix timestamp of the alert")


# ---------------------------------------------------------------------------
# Observation — what the agent sees each step
# ---------------------------------------------------------------------------
class IncidentObservation(BaseModel):
    task: str = Field(..., description="Task name: easy | medium | hard")
    step: int = Field(..., description="Current step number (1-indexed)")
    max_steps: int = Field(..., description="Maximum steps allowed")
    alerts: List[Alert] = Field(..., description="Current stream of alerts")
    available_actions: List[str] = Field(..., description="Valid action strings the agent can take")
    context: str = Field(..., description="Natural language description of the current incident state")
    last_action_result: Optional[str] = Field(None, description="Feedback from the last action taken")
    last_action_error: Optional[str] = Field(None, description="Error message if last action was invalid")


# ---------------------------------------------------------------------------
# Action — what the agent submits
# ---------------------------------------------------------------------------
class IncidentAction(BaseModel):
    action: str = Field(
        ...,
        description=(
            "One of the available_actions strings. "
            "For easy: identify:<service_name>. "
            "For medium: diagnose:<root_cause>. "
            "For hard: resolve:<step1>,<step2>,<step3>,<step4>."
        )
    )


# ---------------------------------------------------------------------------
# Reward — per-step reward signal
# ---------------------------------------------------------------------------
class IncidentReward(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="Reward value in [0, 1]")
    reason: str = Field(..., description="Explanation of why this reward was given")


# ---------------------------------------------------------------------------
# Step result — returned by env.step()
# ---------------------------------------------------------------------------
class StepResult(BaseModel):
    observation: IncidentObservation
    reward: float = Field(..., ge=0.0, le=1.0)
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Reset result — returned by env.reset()
# ---------------------------------------------------------------------------
class ResetResult(BaseModel):
    observation: IncidentObservation
    done: bool = False
    info: Dict[str, Any] = Field(default_factory=dict)
