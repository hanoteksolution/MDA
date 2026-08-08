from core.responses.api_response import error_response, success_response


def test_error_response_includes_code_and_details():
    response = error_response(
        message="Membership has expired.",
        code="MEMBERSHIP_EXPIRED",
        details={"member_id": "x"},
        status=403,
    )
    assert response.status_code == 403
    assert response.data["success"] is False
    assert response.data["code"] == "MEMBERSHIP_EXPIRED"
    assert response.data["message"] == "Membership has expired."
    assert response.data["details"]["member_id"] == "x"


def test_success_response_shape():
    response = success_response(data={"ok": True}, message="Done")
    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["data"]["ok"] is True
