"""
Deterministic graders for all 3 tasks.
Each grader returns a float in [0.0, 1.0].
"""
from typing import List


def grade_easy(action: str, ground_truth_service: str) -> float:
    action = action.strip().lower()
    expected = f"identify:{ground_truth_service.lower()}"
    return 0.95 if action == expected else 0.05


def grade_medium(action: str, ground_truth_cause: str) -> float:
    action = action.strip().lower()
    expected = f"diagnose:{ground_truth_cause.lower()}"
    return 0.95 if action == expected else 0.05


def grade_hard(action: str, ground_truth_resolution: List[str]) -> float:
    action = action.strip().lower()
    expected = [s.lower() for s in ground_truth_resolution]
    submitted = [s.strip() for s in action.split(",") if s.strip()]

    if not submitted:
        return 0.05

    positional_correct = sum(
        1 for i, step in enumerate(submitted)
        if i < len(expected) and step == expected[i]
    )

    submitted_set = set(submitted)
    expected_set = set(expected)
    all_present = expected_set.issubset(submitted_set)

    if positional_correct == 4:
        return 0.95
    elif positional_correct == 3:
        return 0.75
    elif positional_correct == 2:
        return 0.5
    elif positional_correct == 1:
        return 0.25
    elif all_present:
        return 0.1
    else:
        return 0.05


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
