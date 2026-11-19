import json

import pytest
import websocket

from hyperliquid.websocket_manager import RECONNECT_DELAY_SECONDS, WebsocketManager


class FakeWebSocketApp:
    """Stub for websocket.WebSocketApp: records sends, never connects."""

    def __init__(self, url, on_message=None, on_open=None, on_close=None, on_error=None):
        self.url = url
        self.on_message = on_message
        self.on_open = on_open
        self.on_close = on_close
        self.on_error = on_error
        self.sent = []
        self.keep_running = True
        self.fail_send = False
        self.run_forever_kwargs = None

    def send(self, data):
        if self.fail_send or not self.keep_running:
            raise websocket.WebSocketConnectionClosedException("Connection is already closed.")
        self.sent.append(data)

    def close(self):
        self.keep_running = False

    def run_forever(self, **kwargs):
        self.run_forever_kwargs = kwargs
        return False


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setattr("hyperliquid.websocket_manager.websocket.WebSocketApp", FakeWebSocketApp)
    return WebsocketManager("http://test")


def subscribe_frames(ws):
    return [s for s in ws.sent if '"subscribe"' in s]


def test_reconnect_replays_active_subscriptions_once(manager):
    manager.subscribe({"type": "allMids"}, lambda m: None)
    manager.ws.on_open(manager.ws)
    assert manager.ws_ready
    assert subscribe_frames(manager.ws) == ['{"method": "subscribe", "subscription": {"type": "allMids"}}']
    manager.subscribe({"type": "userEvents"}, lambda m: None)

    sent_before_reconnect = len(manager.ws.sent)
    manager.ws.on_open(manager.ws)  # simulated reconnect

    replayed = subscribe_frames(manager.ws)[sent_before_reconnect:]
    assert replayed == [
        '{"method": "subscribe", "subscription": {"type": "allMids"}}',
        '{"method": "subscribe", "subscription": {"type": "userEvents"}}',
    ]
    assert manager.queued_subscriptions == []


def test_reconnect_does_not_duplicate_callbacks(manager):
    received = []
    manager.subscribe({"type": "allMids"}, lambda m: received.append(m))
    manager.ws.on_open(manager.ws)
    manager.ws.on_open(manager.ws)  # simulated reconnect
    manager.ws.on_open(manager.ws)  # second reconnect
    manager.on_message(manager.ws, json.dumps({"channel": "allMids", "data": {"BTC": "1"}}))
    assert len(received) == 1


def test_queued_subscriptions_not_replayed_twice(manager):
    manager.subscribe({"type": "allMids"}, lambda m: None)
    manager.ws.on_open(manager.ws)
    assert manager.queued_subscriptions == []
    manager.ws.on_open(manager.ws)  # simulated reconnect: active replay, not queue replay
    assert subscribe_frames(manager.ws) == [
        '{"method": "subscribe", "subscription": {"type": "allMids"}}',
        '{"method": "subscribe", "subscription": {"type": "allMids"}}',
    ]


def test_on_close_and_on_error_clear_ws_ready(manager):
    manager.subscribe({"type": "allMids"}, lambda m: None)
    manager.ws.on_open(manager.ws)
    assert manager.ws_ready

    manager.ws.on_close(manager.ws, 1006, "")
    assert not manager.ws_ready
    # Subscribing while disconnected queues instead of sending.
    manager.subscribe({"type": "userEvents"}, lambda m: None)
    assert len(subscribe_frames(manager.ws)) == 1
    assert len(manager.queued_subscriptions) == 1

    manager.ws.on_open(manager.ws)
    assert manager.ws_ready
    assert subscribe_frames(manager.ws) == [
        '{"method": "subscribe", "subscription": {"type": "allMids"}}',
        # Reconnect replay of the still-active allMids subscription...
        '{"method": "subscribe", "subscription": {"type": "allMids"}}',
        # ...followed by the queued userEvents subscription.
        '{"method": "subscribe", "subscription": {"type": "userEvents"}}',
    ]

    manager.ws.on_error(manager.ws, Exception("boom"))
    assert not manager.ws_ready


def test_subscribe_while_socket_down_queues_instead_of_raising(manager):
    manager.ws.on_open(manager.ws)
    manager.ws.fail_send = True
    subscription_id = manager.subscribe({"type": "allMids"}, lambda m: None)
    assert isinstance(subscription_id, int)
    assert len(manager.queued_subscriptions) == 1

    manager.ws.fail_send = False
    manager.ws.on_open(manager.ws)
    assert subscribe_frames(manager.ws) == ['{"method": "subscribe", "subscription": {"type": "allMids"}}']


def test_run_passes_reconnect_delay(manager):
    manager.run()
    try:
        assert manager.ws.run_forever_kwargs == {"reconnect": RECONNECT_DELAY_SECONDS}
        assert RECONNECT_DELAY_SECONDS == 5
    finally:
        manager.stop()


def test_ping_thread_survives_send_failure(manager):
    from unittest.mock import MagicMock

    manager.ws.fail_send = True
    manager.stop_event = MagicMock()
    manager.stop_event.wait.side_effect = [False, True]
    # Would raise WebSocketConnectionClosedException without the guard, killing
    # the ping thread mid-reconnect.
    manager.send_ping()
    assert manager.stop_event.wait.call_count == 2
