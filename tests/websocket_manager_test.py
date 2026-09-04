import json
from collections import defaultdict
from types import SimpleNamespace

import pytest

from hyperliquid.websocket_manager import WebsocketManager


def make_manager(ws_ready: bool):
    """A WebsocketManager with a stub socket, so no connection is opened."""
    ws_manager = WebsocketManager.__new__(WebsocketManager)
    ws_manager.subscription_id_counter = 0
    ws_manager.ws_ready = ws_ready
    ws_manager.queued_subscriptions = []
    ws_manager.active_subscriptions = defaultdict(list)
    sent = []
    ws_manager.ws = SimpleNamespace(send=sent.append)
    return ws_manager, sent


def callback(_msg):
    pass


def test_duplicate_single_subscription_raises_while_queued():
    # userEvents and orderUpdates cannot be multiplexed. Before this was checked on
    # the queued path the duplicate was only caught later, inside on_open.
    ws_manager, _ = make_manager(ws_ready=False)
    ws_manager.subscribe({"type": "userEvents"}, callback)

    with pytest.raises(NotImplementedError):
        ws_manager.subscribe({"type": "userEvents"}, callback)


def test_duplicate_single_subscription_raises_when_connected():
    ws_manager, _ = make_manager(ws_ready=True)
    ws_manager.subscribe({"type": "orderUpdates"}, callback)

    with pytest.raises(NotImplementedError):
        ws_manager.subscribe({"type": "orderUpdates"}, callback)


def test_rejected_duplicate_does_not_drop_later_subscriptions():
    # The duplicate used to surface inside on_open, which aborted the replay and
    # silently dropped every subscription queued behind it.
    ws_manager, sent = make_manager(ws_ready=False)
    ws_manager.subscribe({"type": "userEvents"}, callback)
    with pytest.raises(NotImplementedError):
        ws_manager.subscribe({"type": "userEvents"}, callback)
    ws_manager.subscribe({"type": "l2Book", "coin": "ETH"}, callback)

    ws_manager.on_open(None)

    assert len(ws_manager.active_subscriptions["l2Book:eth"]) == 1
    assert [json.loads(msg)["subscription"]["type"] for msg in sent] == ["userEvents", "l2Book"]


def test_on_open_replays_and_clears_the_queue():
    ws_manager, sent = make_manager(ws_ready=False)
    ws_manager.subscribe({"type": "l2Book", "coin": "BTC"}, callback)
    ws_manager.subscribe({"type": "trades", "coin": "ETH"}, callback)

    ws_manager.on_open(None)

    assert len(sent) == 2
    assert len(ws_manager.active_subscriptions["l2Book:btc"]) == 1
    assert len(ws_manager.active_subscriptions["trades:eth"]) == 1
    assert ws_manager.queued_subscriptions == []


def test_multiplexable_channel_still_accepts_several_callbacks():
    ws_manager, _ = make_manager(ws_ready=True)
    ws_manager.subscribe({"type": "l2Book", "coin": "ETH"}, callback)
    ws_manager.subscribe({"type": "l2Book", "coin": "ETH"}, callback)

    assert len(ws_manager.active_subscriptions["l2Book:eth"]) == 2
