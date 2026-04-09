"""
Deterministic graders for all 3 tasks.
Each grader returns a float in [0.0, 1.0].
"""
from typing import List


def grade_easy(action: str, ground_truth_service: str) -> float:
    """
    Easy task: agent must identify the single affected service.
    Action format: identify:<service_name>
    Returns 1.0 for correct, 0.0 for wrong.
    """
    action = action.strip().lower()
    expected = f"identify:{ground_truth_service.lower()}"
    return 1.0 if action == expected else 0.0


def grade_medium(action: str, ground_truth_cause: str) -> float:
    """
    Medium task: agent must diagnose the root cause from 3 correlated alerts.
    Action format: diagnose:<root_cause>
    Returns 1.0 for correct, 0.0 for wrong.
    """
    action = action.strip().lower()
    expected = f"diagnose:{ground_truth_cause.lower()}"
    return 1.0 if action == expected else 0.0


def grade_hard(action: str, ground_truth_resolution: List[str]) -> float:
    """
    Hard task: agent must provide the correct ordered resolution sequence.
    Action format: resolve:<svc1>:<act1>,resolve:<svc2>:<act2>,...

    Scoring:
    - 1.0  : perfect order, all 4 steps correct
    - 0.75 : 3 of 4 steps correct in position
    - 0.5  : 2 of 4 steps correct in position
    - 0.25 : 1 of 4 steps correct in position, OR all steps present but wrong order
    - 0.1  : all 4 steps present but completely wrong order
    - 0.0  : fewer than 2 correct steps
    """
    action = action.strip().lower()
    expected = [s.lower() for s in ground_truth_resolution]

    # Parse submitted steps
    submitted = [s.strip() for s in action.split(",") if s.strip()]

    if not submitted:
        return 0.0

    # Count positional matches
    positional_correct = sum(
        1 for i, step in enumerate(submitted)
        if i < len(expected) and step == expected[i]
    )

    # Check if all correct steps are present (regardless of order)
    submitted_set = set(submitted)
    expected_set = set(expected)
    all_present = expected_set.issubset(submitted_set)

    if positional_correct == 4:
        return 1.0
    elif positional_correct == 3:
        return 0.75
    elif positional_correct == 2:
        return 0.5
    elif positional_correct == 1:
        return 0.25
    elif all_present:
        # Has all right steps but wrong order
        return 0.1
    else:
        return 0.0


def grade_action(task: str, action: str, incident: dict) -> float:
    """Unified grader dispatcher."""
    if task == "easy":
        return grade_easy(action, incident["ground_truth_service"])
    elif task == "medium":
        return grade_medium(action, incident["ground_truth_cause"])
    elif task == "hard":
        return grade_hard(action, incident["ground_truth_resolution"])
    else:
        raise ValueError(f"Unknown task: {task}")
