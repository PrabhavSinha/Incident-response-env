"""
Reward shaping logic for IncidentResponseEnv.
Provides dense, partial-progress signals over the full trajectory.
"""
from typing import Optional


def compute_reward(
    task: str,
    step: int,
    max_steps: int,
    grade: float,
    done: bool,
    action_valid: bool,
    previous_best_grade: float = 0.0,
) -> float:
    """
    Compute shaped reward for a single step.

    Reward components:
    1. Grade signal       — primary signal from the grader (0.0–1.0)
    2. Step efficiency    — bonus for solving early, penalty for wasting steps
    3. Invalid action     — small penalty for submitting an invalid action
    4. Improvement bonus  — small bonus for improving over previous best grade

    Final reward is clamped to [0.0, 1.0].
    """
    if not action_valid:
        # Penalize invalid actions to discourage random guessing
        return max(0.0, 0.0 - 0.05)

    reward = grade

    # Improvement bonus: reward partial progress toward the answer
    if grade > previous_best_grade:
        improvement = grade - previous_best_grade
        reward += improvement * 0.1  # small bonus for getting closer

    # Step efficiency: bonus for solving quickly, no penalty for using all steps
    # (we don't want to penalize careful reasoning)
    if done and grade >= 0.9:
        efficiency_bonus = (max_steps - step) / max_steps * 0.1
        reward += efficiency_bonus

    # Clamp to [0.0, 1.0]
    return min(1.0, max(0.0, reward))


def is_valid_action(action: str, available_actions: list) -> bool:
    """Check if the submitted action is in the available actions list."""
    action_lower = action.strip().lower()

    # For hard task, the action is a comma-separated sequence
    # We validate each component is in available_actions
    if "," in action_lower:
        parts = [p.strip() for p in action_lower.split(",")]
        available_lower = [a.lower() for a in available_actions]
        return all(p in available_lower for p in parts)

    return action_lower in [a.lower() for a in available_actions]
