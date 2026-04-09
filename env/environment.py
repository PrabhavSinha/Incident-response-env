"""
Core OpenEnv environment class for IncidentResponseEnv.
Implements step() / reset() / state() per OpenEnv spec.
"""
from typing import Optional, Dict, Any
from .models import (
    IncidentObservation,
    IncidentAction,
    StepResult,
    ResetResult,
)
from .dataset import get_incident
from .graders import grade_action
from .reward import compute_reward, is_valid_action


# Max steps per task
MAX_STEPS: Dict[str, int] = {
    "easy":   3,
    "medium": 5,
    "hard":   8,
}


class IncidentResponseEnv:
    """
    IncidentResponseEnv — OpenEnv-compliant environment.

    The agent receives a stream of production alerts and must:
    - Easy:   identify the single affected service
    - Medium: diagnose the root cause from 3 correlated alerts
    - Hard:   provide the correct ordered resolution for a cascading failure
    """

    def __init__(self, task: str = "easy", incident_index: int = 0):
        if task not in ("easy", "medium", "hard"):
            raise ValueError(f"task must be 'easy', 'medium', or 'hard', got: {task!r}")
        self.task = task
        self.incident_index = incident_index
        self._incident: Optional[Dict[str, Any]] = None
        self._step_count: int = 0
        self._done: bool = False
        self._best_grade: float = 0.0
        self._last_action_result: Optional[str] = None
        self._last_action_error: Optional[str] = None
        self._final_score: float = 0.0

    # ------------------------------------------------------------------
    # reset() — start a new episode
    # ------------------------------------------------------------------
    def reset(self) -> ResetResult:
        self._incident = get_incident(self.task, self.incident_index)
        self._step_count = 0
        self._done = False
        self._best_grade = 0.0
        self._last_action_result = None
        self._last_action_error = None
        self._final_score = 0.0

        obs = self._build_observation()
        return ResetResult(observation=obs, done=False, info={"incident_id": self._incident["id"]})

    # ------------------------------------------------------------------
    # step() — agent takes an action
    # ------------------------------------------------------------------
    def step(self, action: IncidentAction) -> StepResult:
        if self._incident is None:
            raise RuntimeError("Call reset() before step()")
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        self._step_count += 1
        max_steps = MAX_STEPS[self.task]
        action_str = action.action.strip()

        # Validate action
        valid = is_valid_action(action_str, self._incident["available_actions"])
        if not valid:
            self._last_action_error = f"Invalid action: {action_str!r}. Must be one of: {self._incident['available_actions']}"
            self._last_action_result = None
            reward = compute_reward(
                task=self.task,
                step=self._step_count,
                max_steps=max_steps,
                grade=0.0,
                done=False,
                action_valid=False,
                previous_best_grade=self._best_grade,
            )
            done = self._step_count >= max_steps
            self._done = done
            return StepResult(
                observation=self._build_observation(),
                reward=reward,
                done=done,
                info={"error": self._last_action_error, "grade": 0.0},
            )

        self._last_action_error = None

        # Grade the action
        grade = grade_action(self.task, action_str, self._incident)

        # Compute shaped reward
        reward = compute_reward(
            task=self.task,
            step=self._step_count,
            max_steps=max_steps,
            grade=grade,
            done=grade >= 1.0 or self._step_count >= max_steps,
            action_valid=True,
            previous_best_grade=self._best_grade,
        )

        # Update best grade
        if grade > self._best_grade:
            self._best_grade = grade

        # Build result message
        if grade == 1.0:
            self._last_action_result = "Correct! Incident resolved successfully."
            self._done = True
        elif grade >= 0.75:
            self._last_action_result = f"Mostly correct (score: {grade:.2f}). Close but not perfect."
            self._done = True  # accept near-perfect on hard task
        elif grade >= 0.5:
            self._last_action_result = f"Partial credit (score: {grade:.2f}). Some steps correct."
            self._done = True
        elif grade > 0.0:
            self._last_action_result = f"Partial credit (score: {grade:.2f}). Keep reasoning."
            self._done = self._step_count >= max_steps
        else:
            self._last_action_result = "Incorrect. Review the alerts and try again."
            self._done = self._step_count >= max_steps

        self._final_score = self._best_grade

        return StepResult(
            observation=self._build_observation(),
            reward=reward,
            done=self._done,
            info={
                "grade": grade,
                "best_grade": self._best_grade,
                "incident_id": self._incident["id"],
            },
        )

    # ------------------------------------------------------------------
    # state() — return current environment state
    # ------------------------------------------------------------------
    def state(self) -> Dict[str, Any]:
        if self._incident is None:
            return {"status": "not_started", "task": self.task}
        return {
            "task": self.task,
            "incident_id": self._incident["id"],
            "step": self._step_count,
            "max_steps": MAX_STEPS[self.task],
            "done": self._done,
            "best_grade": self._best_grade,
            "final_score": self._final_score,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _build_observation(self) -> IncidentObservation:
        assert self._incident is not None
        return IncidentObservation(
            task=self.task,
            step=self._step_count,
            max_steps=MAX_STEPS[self.task],
            alerts=self._incident["alerts"],
            available_actions=self._incident["available_actions"],
            context=self._incident["context"],
            last_action_result=self._last_action_result,
            last_action_error=self._last_action_error,
        )
