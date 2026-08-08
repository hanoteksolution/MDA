from rest_framework.response import Response
from rest_framework.views import exception_handler


def success_response(data=None, message="", status=200, code=None):
    payload = {"success": True, "message": message, "data": data}
    if code:
        payload["code"] = code
    return Response(payload, status=status)


def error_response(message="", errors=None, status=400, code=None, details=None):
    """Standard API error envelope.

    Shape:
      { "success": false, "code": "...", "message": "...", "errors": {}, "details": {} }
    """
    payload = {
        "success": False,
        "message": message or "An error occurred.",
        "errors": errors if errors is not None else {},
    }
    if code:
        payload["code"] = code
    if details is not None:
        payload["details"] = details
    return Response(payload, status=status)


def _infer_error_code(status_code: int, errors) -> str:
    if status_code == 401:
        return "UNAUTHORIZED"
    if status_code == 403:
        return "FORBIDDEN"
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 429:
        return "RATE_LIMITED"
    if status_code >= 500:
        return "SERVER_ERROR"
    if isinstance(errors, dict) and len(errors) == 1 and "detail" in errors:
        return "REQUEST_ERROR"
    return "VALIDATION_ERROR"


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        errors = response.data
        if isinstance(errors, dict) and "detail" in errors:
            message = str(errors["detail"])
            errors = {"detail": [message]}
        elif isinstance(errors, list):
            message = str(errors[0]) if errors else "An error occurred."
            errors = {"detail": errors}
        else:
            message = "Validation failed."
        code = _infer_error_code(response.status_code, errors)
        response.data = {
            "success": False,
            "code": code,
            "message": message,
            "errors": errors,
            "details": {},
        }
    return response
