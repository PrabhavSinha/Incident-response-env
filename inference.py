"""
Baseline inference script for IncidentResponseEnv.
Uses OpenAI client against API_BASE_URL / MODEL_NAME.
Emits [START] / [STEP] / [END] logs per OpenEnv spec.

Required env vars:
  API_BASE_URL   — LLM endpoint
  MODEL_NAME     — model identifier
  HF_TOKEN       — Hugging Face / API key
"""
import os
import json
import textwrap
from typing import List, Optional
from openai import OpenAI

# ---------------------------------------------------------------------------
# Config from environment
# ---------------------------------------------------------------------------
API_KEY      = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")  # optional: for from_docker_image()
BENCHMARK    = "incident-response-env"

# Tasks to run
TASKS = ["easy", "medium", "hard"]

# Max steps per task (must match environment)
MAX_STEPS = {"easy": 3, "medium": 5, "hard": 8}

# Score threshold for success
SUCCESS_THRESHOLD = 0.5

# ---------------------------------------------------------------------------
# Logging helpers — strict format required by OpenEnv
# ---------------------------------------------------------------------------
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Sanitize action: no newlines, truncate if very long
    action_clean = action.replace("\n", " ").replace("\r", "")[:200]
    print(
        f"[STEP] step={step} action={action_clean} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# HTTP client helpers — call the local FastAPI server
# ---------------------------------------------------------------------------
import urllib.request

SERVER_URL = os.getenv("SERVER_URL", "http://localhost:7860")


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{SERVER_URL}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def env_reset(task: str, incident_index: int = 0) -> dict:
    return _post("/reset", {"task": task, "incident_index": incident_index})


def env_step(task: str, action: str, incident_index: int = 0) -> dict:
    return _post("/step", {"task": task, "action": action, "incident_index": incident_index})


def env_state(task: str, incident_index: int = 0) -> dict:
    return _post("/state", {"task": task, "incident_index": incident_index})


# ---------------------------------------------------------------------------
# LLM agent
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = textwrap.dedent("""
You are an expert on-call Site Reliability Engineer (SRE).
You will receive production alerts and must respond with exactly one action string.

Rules:
- Reply with ONLY the action string — no explanation, no markdown, no extra text.
- The action must be exactly one of the available_actions listed in the observation.
- For easy tasks:   identify:<service_name>
- For medium tasks: diagnose:<root_cause>
- For hard tasks:   resolve:<svc1>:<act1>,resolve:<svc2>:<act2>,resolve:<svc3>:<act3>,resolve:<svc4>:<act4>

Think carefully about causality: which service failed first? What caused the cascade?
""").strip()


def build_user_prompt(obs: dict) -> str:
    alerts_text = "\n".join(
        f"  [{a['severity'].upper()}] {a['service']} — {a['alert_type']}: {a['message']}"
        for a in obs["alerts"]
    )
    actions_text = "\n".join(f"  - {a}" for a in obs["available_actions"])
    last_result = obs.get("last_action_result") or ""
    last_error  = obs.get("last_action_error") or ""

    prompt = textwrap.dedent(f"""
        Task: {obs['task']}
        Step: {obs['step']} / {obs['max_steps']}

        ALERTS:
        {alerts_text}

        CONTEXT:
        {obs['context']}

        AVAILABLE ACTIONS:
        {actions_text}
    """).strip()

    if last_result:
        prompt += f"\n\nLast result: {last_result}"
    if last_error:
        prompt += f"\nError: {last_error}"

    prompt += "\n\nYour action:"
    return prompt


def get_agent_action(client: OpenAI, obs: dict, history: List[dict]) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    # Include last 3 turns of history for context
    for turn in history[-3:]:
        messages.append({"role": "user",      "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": build_user_prompt(obs)})

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.0,   # deterministic for reproducibility
            max_tokens=100,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        # Take only the first line in case model adds explanation
        text = text.split("\n")[0].strip()
        return text if text else obs["available_actions"][0]
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return obs["available_actions"][0]


# ---------------------------------------------------------------------------
# Run one task episode
# ---------------------------------------------------------------------------
def run_task(client: OpenAI, task: str, incident_index: int = 0) -> float:
    max_steps = MAX_STEPS[task]
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    history: List[dict] = []

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = env_reset(task, incident_index)
        obs = reset_result["observation"]

        for step in range(1, max_steps + 1):
            if reset_result.get("done", False) and step == 1:
                break

            user_prompt = build_user_prompt(obs)
            action = get_agent_action(client, obs, history)

            step_result = env_step(task, action, incident_index)
            reward = step_result.get("reward", 0.0)
            done   = step_result.get("done", False)
            error  = step_result["observation"].get("last_action_error")

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action, reward=reward, done=done, error=error)

            history.append({"user": user_prompt, "assistant": action})
            obs = step_result["observation"]

            if done:
                break

        # Final score = best grade achieved (from state)
        state = env_state(task, incident_index)
        score = float(state.get("best_grade", max(rewards) if rewards else 0.0))
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Task {task} error: {exc}", flush=True)
        score = 0.0
        success = False

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


# ---------------------------------------------------------------------------
# Main — run all 3 tasks
# ---------------------------------------------------------------------------
def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    scores = {}
    for task in TASKS:
        score = run_task(client, task, incident_index=0)
        scores[task] = score

    # Summary to stderr so it doesn't pollute stdout log format
    import sys
    print(f"\n[SUMMARY] easy={scores['easy']:.3f} medium={scores['medium']:.3f} hard={scores['hard']:.3f}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
