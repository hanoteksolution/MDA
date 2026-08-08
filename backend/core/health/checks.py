"""Dependency health probes for ops / monitoring."""

from __future__ import annotations

import time
from typing import Any

from django.conf import settings
from django.db import connection


def _latency_ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def check_database() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:
        return {
            "status": "error",
            "component": "database",
            "latency_ms": _latency_ms(start),
            "detail": str(exc),
        }
    return {
        "status": "ok",
        "component": "database",
        "latency_ms": _latency_ms(start),
    }


def check_cache() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        import redis

        client = redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
    except Exception as exc:
        return {
            "status": "error",
            "component": "cache",
            "latency_ms": _latency_ms(start),
            "detail": str(exc),
        }
    return {
        "status": "ok",
        "component": "cache",
        "latency_ms": _latency_ms(start),
    }


def check_celery(*, require_workers: bool = False) -> dict[str, Any]:
    """Report Celery broker, beat schedule, and optional live workers.

    Schedule registration is always required for ``ok``. Live workers are
    reported but only fail the check when ``require_workers=True`` (ops smoke).
    """
    start = time.perf_counter()
    schedule = getattr(settings, "CELERY_BEAT_SCHEDULE", {}) or {}
    scheduled_tasks = sorted(
        {
            str(entry.get("task") or "")
            for entry in schedule.values()
            if isinstance(entry, dict) and entry.get("task")
        }
    )
    broker = check_cache()
    workers: list[str] = []
    inspect_error = None
    try:
        from config.celery import app as celery_app

        # Keep inspect short so health endpoints stay snappy when workers are down.
        inspector = celery_app.control.inspect(timeout=0.5)
        ping = inspector.ping() if inspector else None
        if isinstance(ping, dict):
            workers = sorted(ping.keys())
    except Exception as exc:
        inspect_error = str(exc)

    status = "ok"
    detail_parts: list[str] = []
    if not scheduled_tasks:
        status = "error"
        detail_parts.append("CELERY_BEAT_SCHEDULE is empty")
    if broker.get("status") != "ok":
        status = "error"
        detail_parts.append(broker.get("detail") or "broker unreachable")
    if require_workers and not workers:
        status = "error"
        detail_parts.append(inspect_error or "no celery workers responded to ping")
    elif not workers and status == "ok":
        status = "degraded"
        detail_parts.append(inspect_error or "no celery workers online")

    return {
        "status": status,
        "component": "celery",
        "latency_ms": _latency_ms(start),
        "broker": broker.get("status"),
        "scheduled_jobs": len(schedule),
        "scheduled_tasks": scheduled_tasks,
        "workers": workers,
        "workers_online": len(workers),
        "detail": "; ".join(detail_parts) if detail_parts else "",
    }


def check_readiness() -> dict[str, Any]:
    database = check_database()
    cache = check_cache()
    components = {"database": database, "cache": cache}
    overall = "ok" if all(c["status"] == "ok" for c in components.values()) else "degraded"
    return {
        "status": overall,
        "components": components,
    }
