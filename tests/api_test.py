import pytest

from hyperliquid.api import API
from hyperliquid.utils.error import ClientError, ServerError


class FakeResponse:
    def __init__(self, status_code, text, headers=None):
        self.status_code = status_code
        self.text = text
        self.headers = {} if headers is None else headers


@pytest.fixture
def api():
    return API()


def test_no_exception_below_400(api):
    assert api._handle_exception(FakeResponse(200, "{}")) is None


def test_well_formed_error_body_is_unpacked(api):
    headers = {"x-ratelimit-remaining": "0"}
    body = '{"code": "SOME_CODE", "msg": "some message", "data": {"detail": "x"}}'
    with pytest.raises(ClientError) as excinfo:
        api._handle_exception(FakeResponse(422, body, headers))
    err = excinfo.value
    assert err.status_code == 422
    assert err.error_code == "SOME_CODE"
    assert err.error_message == "some message"
    assert err.header == headers
    assert err.error_data == {"detail": "x"}


# The live API answers a bad request with a plain-text body, so this is the
# ordinary error path rather than an exotic one.
@pytest.mark.parametrize(
    "body",
    [
        "Failed to deserialize the JSON body into the target type",
        "null",
        '"Unauthorized"',
        '["a", "b"]',
        "429",
        '{"error": "rate limited"}',
        '{"code": "only-code"}',
        '{"msg": "only-msg"}',
    ],
)
def test_unusable_error_body_still_raises_client_error(api, body):
    headers = {"x-ratelimit-remaining": "0"}
    with pytest.raises(ClientError) as excinfo:
        api._handle_exception(FakeResponse(422, body, headers))
    err = excinfo.value
    assert err.status_code == 422
    assert err.error_code is None
    # The raw body is the only description available, so it becomes the message.
    assert err.error_message == body
    # Headers belong in `header`; `error_data` is for the body's "data" field.
    assert err.header == headers
    assert err.error_data is None


def test_5xx_raises_server_error(api):
    with pytest.raises(ServerError) as excinfo:
        api._handle_exception(FakeResponse(503, "upstream unavailable"))
    assert excinfo.value.status_code == 503
    assert excinfo.value.message == "upstream unavailable"
