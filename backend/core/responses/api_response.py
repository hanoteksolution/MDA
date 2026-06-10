from rest_framework.response import Response
from rest_framework.views import exception_handler


def success_response(data=None, message="", status=200):
    return Response({"success": True, "message": message, "data": data}, status=status)


def error_response(message="", errors=None, status=400):
    return Response(
        {"success": False, "message": message, "errors": errors or {}},
        status=status,
    )


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
        response.data = {"success": False, "message": message, "errors": errors}
    return response
