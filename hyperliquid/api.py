import json
import logging
from json import JSONDecodeError

import requests

from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.error import ClientError, ServerError
from hyperliquid.utils.types import Any


class API:
    def __init__(self, base_url=None, timeout=None):
        self.base_url = base_url or MAINNET_API_URL
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self._logger = logging.getLogger(__name__)
        self.timeout = timeout

    def post(self, url_path: str, payload: Any = None) -> Any:
        payload = payload or {}
        url = self.base_url + url_path
        response = self.session.post(url, json=payload, timeout=self.timeout)
        self._handle_exception(response)
        try:
            return response.json()
        except ValueError:
            return {"error": f"Could not parse JSON: {response.text}"}

    def _handle_exception(self, response):
        status_code = response.status_code
        if status_code < 400:
            return
        if 400 <= status_code < 500:
            try:
                err = json.loads(response.text)
            except JSONDecodeError:
                raise ClientError(status_code, None, response.text, None, response.headers)
            if err is None:
                raise ClientError(status_code, None, response.text, None, response.headers)
            error_data = err.get("data")
            raise ClientError(status_code, err["code"], err["msg"], response.headers, error_data)
        raise ServerError(status_code, response.text)
