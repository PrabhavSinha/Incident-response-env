"""
Synthetic incident catalog for IncidentResponseEnv.
All incidents are deterministic — fixed ground truth for reproducible grading.
"""
from typing import List, Dict, Any
from .models import Alert
import time

# ---------------------------------------------------------------------------
# Base timestamp (fixed for reproducibility)
# ---------------------------------------------------------------------------
_T = 1700000000.0


def _alert(service: str, alert_type: str, severity: str, message: str, offset: float = 0.0) -> Alert:
    return Alert(
        service=service,
        alert_type=alert_type,
        severity=severity,
        message=message,
        timestamp=_T + offset,
    )


# ---------------------------------------------------------------------------
# EASY INCIDENTS — single signal, identify the affected service
# ---------------------------------------------------------------------------
EASY_INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "easy_001",
        "alerts": [
            _alert("payment-service", "http_500", "critical", "Payment service returning 500 errors on /charge endpoint", 0),
        ],
        "ground_truth_service": "payment-service",
        "available_actions": [
            "identify:payment-service",
            "identify:auth-service",
            "identify:api-gateway",
            "identify:database",
        ],
        "context": "A single alert has fired. Identify which service is affected.",
    },
    {
        "id": "easy_002",
        "alerts": [
            _alert("auth-service", "cpu_spike", "high", "Auth service CPU at 98% for last 5 minutes", 0),
        ],
        "ground_truth_service": "auth-service",
        "available_actions": [
            "identify:auth-service",
            "identify:payment-service",
            "identify:notification-service",
            "identify:cache",
        ],
        "context": "A single alert has fired. Identify which service is affected.",
    },
    {
        "id": "easy_003",
        "alerts": [
            _alert("user-db", "db_timeout", "critical", "user-db query timeout after 30s on SELECT queries", 0),
        ],
        "ground_truth_service": "user-db",
        "available_actions": [
            "identify:user-db",
            "identify:order-service",
            "identify:cache",
            "identify:api-gateway",
        ],
        "context": "A single alert has fired. Identify which service is affected.",
    },
    {
        "id": "easy_004",
        "alerts": [
            _alert("notification-service", "memory_leak", "high", "Notification service heap usage at 94%, OOM imminent", 0),
        ],
        "ground_truth_service": "notification-service",
        "available_actions": [
            "identify:notification-service",
            "identify:payment-service",
            "identify:user-db",
            "identify:api-gateway",
        ],
        "context": "A single alert has fired. Identify which service is affected.",
    },
]


# ---------------------------------------------------------------------------
# MEDIUM INCIDENTS — 3 correlated alerts, identify root cause
# ---------------------------------------------------------------------------
MEDIUM_INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "medium_001",
        "alerts": [
            _alert("api-gateway",     "http_500",    "critical", "API gateway returning 503 on all /api/v1/orders routes", 0),
            _alert("order-service",   "http_500",    "critical", "Order service returning 500 on POST /orders", 10),
            _alert("user-db",         "db_timeout",  "critical", "user-db connection pool exhausted, all queries timing out", 20),
        ],
        "ground_truth_cause": "user-db",
        "available_actions": [
            "diagnose:user-db",
            "diagnose:order-service",
            "diagnose:api-gateway",
            "diagnose:network-partition",
        ],
        "context": (
            "Three alerts fired in sequence. The API gateway and order service are both failing. "
            "Identify the single root cause driving all three alerts."
        ),
    },
    {
        "id": "medium_002",
        "alerts": [
            _alert("cache",           "latency_high", "high",     "Redis cache latency spiked to 2000ms (normal: 5ms)", 0),
            _alert("auth-service",    "latency_high", "high",     "Auth service p99 latency 8000ms, token validation slow", 15),
            _alert("api-gateway",     "http_500",     "critical", "API gateway timing out waiting for auth tokens", 30),
        ],
        "ground_truth_cause": "cache",
        "available_actions": [
            "diagnose:cache",
            "diagnose:auth-service",
            "diagnose:api-gateway",
            "diagnose:upstream-provider",
        ],
        "context": (
            "Three alerts fired in sequence. Auth is slow and the gateway is timing out. "
            "Identify the single root cause driving all three alerts."
        ),
    },
    {
        "id": "medium_003",
        "alerts": [
            _alert("payment-service", "cpu_spike",   "critical", "Payment service CPU at 100%, processing queue backed up", 0),
            _alert("payment-service", "http_500",    "critical", "Payment service /charge returning 500 due to queue overflow", 5),
            _alert("notification-service", "http_500", "high",   "Notification service failing to send payment confirmations", 25),
        ],
        "ground_truth_cause": "payment-service",
        "available_actions": [
            "diagnose:payment-service",
            "diagnose:notification-service",
            "diagnose:message-queue",
            "diagnose:user-db",
        ],
        "context": (
            "Three alerts fired. Payment processing is degraded and notifications are failing. "
            "Identify the single root cause driving all three alerts."
        ),
    },
]


# ---------------------------------------------------------------------------
# HARD INCIDENTS — cascading failure across 4 services, ordered resolution
# ---------------------------------------------------------------------------
HARD_INCIDENTS: List[Dict[str, Any]] = [
    {
        "id": "hard_001",
        "alerts": [
            _alert("user-db",          "disk_full",    "critical", "user-db disk at 100%, writes failing",                    0),
            _alert("auth-service",     "http_500",     "critical", "Auth service cannot write sessions to user-db",           5),
            _alert("api-gateway",      "http_500",     "critical", "API gateway rejecting all requests: auth failures",       10),
            _alert("payment-service",  "http_500",     "critical", "Payment service cannot authenticate users, all 500s",     15),
        ],
        "ground_truth_resolution": [
            "resolve:user-db:clear-disk",
            "resolve:auth-service:restart",
            "resolve:api-gateway:clear-cache",
            "resolve:payment-service:verify",
        ],
        "available_actions": [
            "resolve:user-db:clear-disk",
            "resolve:auth-service:restart",
            "resolve:api-gateway:clear-cache",
            "resolve:payment-service:verify",
            "resolve:api-gateway:restart",
            "resolve:user-db:restart",
            "resolve:payment-service:rollback",
            "resolve:auth-service:scale-up",
        ],
        "context": (
            "A cascading failure has hit 4 services. user-db disk is full, causing auth failures, "
            "which cascaded to the API gateway and payment service. "
            "Provide the correct ordered resolution sequence as: "
            "resolve:<svc1>:<action1>,resolve:<svc2>:<action2>,resolve:<svc3>:<action3>,resolve:<svc4>:<action4>"
        ),
    },
    {
        "id": "hard_002",
        "alerts": [
            _alert("cache",            "memory_leak",  "critical", "Redis OOM: cache evicting all keys, hit rate 0%",         0),
            _alert("auth-service",     "latency_high", "critical", "Auth cold-cache: every request hitting user-db",          8),
            _alert("user-db",          "cpu_spike",    "critical", "user-db CPU 100%: overwhelmed by auth queries",           12),
            _alert("api-gateway",      "http_500",     "critical", "Gateway timeouts: auth + db both degraded",               20),
        ],
        "ground_truth_resolution": [
            "resolve:cache:restart",
            "resolve:user-db:scale-up",
            "resolve:auth-service:restart",
            "resolve:api-gateway:verify",
        ],
        "available_actions": [
            "resolve:cache:restart",
            "resolve:user-db:scale-up",
            "resolve:auth-service:restart",
            "resolve:api-gateway:verify",
            "resolve:cache:flush",
            "resolve:user-db:restart",
            "resolve:auth-service:scale-up",
            "resolve:api-gateway:rollback",
        ],
        "context": (
            "A cascading failure across 4 services. Cache OOM caused auth to hammer the DB, "
            "which overwhelmed the DB, which took down the gateway. "
            "Provide the correct ordered resolution sequence as: "
            "resolve:<svc1>:<action1>,resolve:<svc2>:<action2>,resolve:<svc3>:<action3>,resolve:<svc4>:<action4>"
        ),
    },
]


# ---------------------------------------------------------------------------
# Catalog lookup helpers
# ---------------------------------------------------------------------------
CATALOG = {
    "easy":   EASY_INCIDENTS,
    "medium": MEDIUM_INCIDENTS,
    "hard":   HARD_INCIDENTS,
}


def get_incident(task: str, index: int = 0) -> Dict[str, Any]:
    """Return a specific incident by task and index."""
    incidents = CATALOG[task]
    return incidents[index % len(incidents)]


def get_all_incidents(task: str) -> List[Dict[str, Any]]:
    return CATALOG[task]
