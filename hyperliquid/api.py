import json
import logging
from json import JSONDecodeError

import requests
from requests.exceptions import RequestException

from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError
from hyperliquid.utils.types import Any


class API:
    """
    A base client class for interacting with the Hyperliquid REST API.
    Handles session management, requests, and comprehensive error handling.
    """
    def __init__(self, base_url: str = None, timeout: float = None):
        """
        Initializes the API client.
        :param base_url: The base URL for the API. Defaults to MAINNET_API_URL.
        :param timeout: The request timeout in seconds.
        """
        self.base_url = base_url or MAINNET_API_URL
        self.timeout = timeout
        
        # Initialize the session for connection pooling and header persistence.
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._logger = logging.getLogger(__name__)

    def post(self, url_path: str, payload: Any = None) -> Any:
        """
        Sends a POST request to the specified API endpoint.
        :param url_path: The endpoint path (e.g., '/info').
        :param payload: The JSON payload to send in the request body.
        :return: The parsed JSON response data.
        :raises ClientError: For 4xx HTTP errors.
        :raises ServerError: For 5xx HTTP errors.
        """
        payload = payload or {}
        url = self.base_url + url_path
        
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            
            # Raise exceptions for bad status codes (4xx and 5xx) immediately.
            self._handle_exception(response)
            
            # Attempt to parse the JSON response for successful requests.
            return response.json()
            
        except JSONDecodeError as e:
            # Handle cases where the server returns a successful status (2xx) but non-JSON content.
            self._logger.error(f"Failed to parse JSON response from {url}: {response.text}")
            # Returning a structured error instead of just a raw dictionary for consistency.
            raise ClientError(
                response.status_code, 
                code="JSON_PARSE_ERROR", 
                msg=f"Could not parse JSON: {e}", 
                data=response.text, 
                headers=response.headers
            )
        except RequestException as e:
            # Handle network/connection issues (e.g., DNS failure, timeout).
            self._logger.error(f"Request failed for {url}: {e}")
            raise ClientError(
                503, 
                code="NETWORK_ERROR", 
                msg=f"Request failed due to network issue: {e}", 
                data=None, 
                headers=None
            )

    def _handle_exception(self, response: requests.Response):
        """
        Handles HTTP status codes >= 400 by raising appropriate exceptions.
        :param response: The requests.Response object.
        :raises ClientError: For 4xx errors.
        :raises ServerError: For 5xx errors.
        """
        status_code = response.status_code
        
        if status_code < 400:
            return

        if 400 <= status_code < 500:
            # Handle 4xx Client Errors
            try:
                # Attempt to parse the structured error response from the server.
                err = response.json()
            except JSONDecodeError:
                # If 4xx error is received but the body is not parsable JSON.
                raise ClientError(status_code, code="UNSPECIFIED_4XX", msg=response.text, data=None, headers=response.headers)
            
            # Ensure the parsed error object is not None or empty if response.json() didn't fail.
            if not err or not isinstance(err, dict):
                 raise ClientError(status_code, code="INVALID_ERROR_FORMAT", msg=response.text, data=None, headers=response.headers)

            # Raise the structured ClientError with details from the API response.
            error_data = err.get("data")
            # Using keyword arguments for clarity, assuming the correct ClientError signature.
            raise ClientError(
                status_code, 
                code=err.get("code"), 
                msg=err.get("msg") or "Client error occurred.", 
                data=error_data, 
                headers=response.headers
            )
        
        # Handle 5xx Server Errors
        raise ServerError(status_code, response.text)
