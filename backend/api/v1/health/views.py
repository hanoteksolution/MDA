from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.health.checks import check_cache, check_celery, check_database, check_readiness


@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    """Liveness — process is up (no dependency checks)."""
    return Response({"status": "ok"})


@api_view(["GET"])
@permission_classes([AllowAny])
def health_database(_request):
    result = check_database()
    code = status.HTTP_200_OK if result["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(result, status=code)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_cache(_request):
    result = check_cache()
    code = status.HTTP_200_OK if result["status"] == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
    return Response(result, status=code)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_celery(_request):
    """Celery broker + beat schedule; workers optional unless ?require_workers=1."""
    require = str(_request.query_params.get("require_workers", "")).lower() in (
        "1",
        "true",
        "yes",
    )
    result = check_celery(require_workers=require)
    if require:
        code = (
            status.HTTP_200_OK
            if result["status"] == "ok"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
    elif result["status"] == "error":
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        # ok or degraded (schedule present; workers may be offline)
        code = status.HTTP_200_OK
    return Response(result, status=code)


@api_view(["GET"])
@permission_classes([AllowAny])
def health_ready(_request):
    """Readiness — database + Redis must be reachable."""
    report = check_readiness()
    code = (
        status.HTTP_200_OK
        if report["status"] == "ok"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return Response(report, status=code)
