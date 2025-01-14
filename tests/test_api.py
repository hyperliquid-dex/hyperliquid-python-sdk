import pytest
import requests
from unittest.mock import Mock, patch

from hyperliquid.api import API
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError

@pytest.fixture
def api():
    """Fixture that provides an API instance"""
    return API()

def test_initializer(api):
    """Test that the API class initializes with correct default values"""
    assert api.base_url == MAINNET_API_URL
    assert isinstance(api.session, requests.Session)
    assert api.session.headers["Content-Type"] == "application/json"
    assert api._logger is not None

def test_initializer_with_custom_url():
    """Test that the API class can be initialized with a custom URL"""
    custom_url = "https://custom.api.url"
    api = API(custom_url)
    assert api.base_url == custom_url

@patch('requests.Session.post')
def test_post_success(mock_post, api):
    """Test successful POST request"""
    expected_response = {"data": "test"}
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = expected_response
    mock_post.return_value = mock_response

    response = api.post("/test", {"key": "value"})
    
    assert response == expected_response
    mock_post.assert_called_once_with(
        f"{MAINNET_API_URL}/test",
        json={"key": "value"}
    )

@patch('requests.Session.post')
def test_post_client_error(mock_post, api):
    """Test POST request with client error (4xx)"""
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = '{"code": "error_code", "msg": "error_message", "data": "error_data"}'
    mock_response.headers = {"header": "value"}
    mock_post.return_value = mock_response

    with pytest.raises(ClientError) as exc_info:
        api.post("/test")
    
    error = exc_info.value
    assert error.status_code == 400
    assert error.error_code == "error_code"
    assert error.error_message == "error_message"
    assert error.error_data == "error_data"
    assert error.header == {"header": "value"}

@patch('requests.Session.post')
def test_post_server_error(mock_post, api):
    """Test POST request with server error (5xx)"""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    with pytest.raises(ServerError) as exc_info:
        api.post("/test")
    
    error = exc_info.value
    assert error.status_code == 500
    assert error.message == "Internal Server Error"

@patch('requests.Session.post')
def test_post_invalid_json_response(mock_post, api):
    """Test POST request with invalid JSON response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "Invalid JSON"
    mock_response.json.side_effect = ValueError
    mock_post.return_value = mock_response

    response = api.post("/test")
    assert response == {"error": "Could not parse JSON: Invalid JSON"}
