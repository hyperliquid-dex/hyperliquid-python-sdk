import pytest

from hyperliquid.api import API
from hyperliquid.utils.error import ClientError, ServerError


class FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text
        self.headers = {}


def test_handle_exception_json_without_code_or_msg_raises_client_error():
    # https://github.com/hyperliquid-dex/hyperliquid-python-sdk/issues/342
    # A 4xx JSON body without "code"/"msg" used to raise KeyError("code")
    # instead of the documented ClientError.
    with pytest.raises(ClientError) as exc_info:
        API()._handle_exception(FakeResponse(400, '{"error": "something"}'))
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code is None
    assert exc_info.value.error_message == '{"error": "something"}'


def test_handle_exception_json_with_only_code_raises_client_error():
    with pytest.raises(ClientError) as exc_info:
        API()._handle_exception(FakeResponse(400, '{"code": 123}'))
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == 123
    assert exc_info.value.error_message == '{"code": 123}'


def test_handle_exception_json_with_only_msg_raises_client_error():
    with pytest.raises(ClientError) as exc_info:
        API()._handle_exception(FakeResponse(400, '{"msg": "bad request"}'))
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code is None
    assert exc_info.value.error_message == "bad request"


def test_handle_exception_json_with_code_msg_and_data():
    with pytest.raises(ClientError) as exc_info:
        API()._handle_exception(FakeResponse(400, '{"code": 123, "msg": "bad request", "data": {"x": 1}}'))
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == 123
    assert exc_info.value.error_message == "bad request"
    assert exc_info.value.error_data == {"x": 1}


def test_handle_exception_non_dict_json_body_raises_client_error():
    # A JSON body that is not an object (e.g. an array or a string) used to
    # raise AttributeError from err.get("data").
    for text in ('["not", "a", "dict"]', '"just a string"', "42"):
        with pytest.raises(ClientError) as exc_info:
            API()._handle_exception(FakeResponse(400, text))
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_message == text


def test_handle_exception_null_json_body_raises_client_error():
    with pytest.raises(ClientError) as exc_info:
        API()._handle_exception(FakeResponse(400, "null"))
    assert exc_info.value.status_code == 400
    assert exc_info.value.error_message == "null"


def test_handle_exception_non_json_body_raises_client_error():
    with pytest.raises(ClientError) as exc_info:
        API()._handle_exception(FakeResponse(422, "plain text body"))
    assert exc_info.value.status_code == 422
    assert exc_info.value.error_code is None
    assert exc_info.value.error_message == "plain text body"


def test_handle_exception_success_status_does_not_raise():
    API()._handle_exception(FakeResponse(200, '{"ok": true}'))


def test_handle_exception_server_error():
    with pytest.raises(ServerError) as exc_info:
        API()._handle_exception(FakeResponse(500, "boom"))
    assert exc_info.value.status_code == 500
