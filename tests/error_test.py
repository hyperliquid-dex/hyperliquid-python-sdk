from hyperliquid.utils.error import ClientError, ServerError


def test_client_error_string_includes_api_message():
    error = ClientError(400, "BadRequest", "invalid order", {"x-request-id": "abc"}, {"field": "coin"})

    assert str(error) == "(400, BadRequest) invalid order"
    assert error.status_code == 400
    assert error.error_code == "BadRequest"
    assert error.error_message == "invalid order"
    assert error.header == {"x-request-id": "abc"}
    assert error.error_data == {"field": "coin"}


def test_client_error_string_handles_missing_error_code():
    error = ClientError(429, None, "rate limited", {})

    assert str(error) == "(429) rate limited"
    assert error.error_code is None


def test_server_error_string_includes_status_code_and_message():
    error = ServerError(503, "temporarily unavailable")

    assert str(error) == "(503) temporarily unavailable"
    assert error.status_code == 503
    assert error.message == "temporarily unavailable"
