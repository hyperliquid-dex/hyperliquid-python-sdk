import json
import logging
from collections import defaultdict
from unittest.mock import MagicMock

import pytest

from hyperliquid.websocket_manager import WebsocketManager, ws_msg_to_identifier

ERROR_MESSAGE = json.dumps({"channel": "error", "data": {"error": "Invalid subscription: unknown coin"}})


def make_manager():
    manager = object.__new__(WebsocketManager)
    manager.active_subscriptions = defaultdict(list)
    return manager


def test_ws_msg_to_identifier_error_channel():
    ws_msg = {"channel": "error", "data": {"error": "Invalid subscription: unknown coin"}}
    assert ws_msg_to_identifier(ws_msg) == "error"


def test_error_channel_message_logs_warning(caplog):
    manager = make_manager()
    with caplog.at_level(logging.WARNING):
        manager.on_message(None, ERROR_MESSAGE)
    warnings = [record for record in caplog.records if record.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "Invalid subscription" in warnings[0].getMessage()


def test_error_channel_message_not_routed_to_subscriptions(capsys):
    manager = make_manager()
    callback = MagicMock()
    manager.active_subscriptions["allMids"].append(callback)
    manager.on_message(None, ERROR_MESSAGE)
    callback.assert_not_called()
    assert "unexpected subscription" not in capsys.readouterr().out
