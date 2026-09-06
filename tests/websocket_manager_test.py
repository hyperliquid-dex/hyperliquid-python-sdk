import json
import threading
import time
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
    ws_manager.lock = threading.RLock()
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


class PausingQueue(list):
    """A queue whose first armed iteration blocks until released.

    on_open hands the queue off and then iterates it, so pausing in __iter__ parks the
    websocket thread in the window after the handoff and before the first replayed
    subscription registers anything. Arming is explicit because subscribe() also walks
    the queue for its duplicate check.
    """

    def __init__(self, entered, release):
        super().__init__()
        self.entered = entered
        self.release = release
        self.armed = False

    def __iter__(self):
        if self.armed:
            self.armed = False
            self.entered.set()
            assert self.release.wait(5), "replay was never released"
        return super().__iter__()


def test_subscribe_racing_on_open_does_not_drop_the_replay():
    # A caller reaching subscribe() between on_open's queue handoff and the replay saw an
    # empty queue and an empty active map, so it claimed userEvents. The replay then raised
    # out of on_open, aborting it and dropping every subscription queued behind userEvents.
    ws_manager, _ = make_manager(ws_ready=False)
    entered, release = threading.Event(), threading.Event()
    queue = PausingQueue(entered, release)
    ws_manager.queued_subscriptions = queue

    ws_manager.subscribe({"type": "userEvents"}, callback)
    ws_manager.subscribe({"type": "l2Book", "coin": "ETH"}, callback)
    queue.armed = True

    opener: dict = {}
    caller: dict = {}

    def run_on_open():
        try:
            ws_manager.on_open(None)
        except Exception as exc:  # noqa: BLE001 - recorded so the assert can report it
            opener["error"] = exc

    def run_caller():
        try:
            ws_manager.subscribe({"type": "userEvents"}, callback)
        except NotImplementedError as exc:
            caller["error"] = exc

    opener_thread = threading.Thread(target=run_on_open)
    caller_thread = threading.Thread(target=run_caller)
    opener_thread.start()
    try:
        assert entered.wait(5), "on_open never reached the replay"
        caller_thread.start()
        # Let the caller reach subscribe. With the lock held across the handoff it parks
        # there; without it, it claims userEvents and the replay below dies.
        time.sleep(0.1)
    finally:
        release.set()
        opener_thread.join(5)
        caller_thread.join(5)

    assert "error" not in opener, f"on_open raised {opener.get('error')!r}"
    assert "error" in caller, "the racing caller should still see the duplicate"
    assert len(ws_manager.active_subscriptions["userEvents"]) == 1
    assert len(ws_manager.active_subscriptions["l2Book:eth"]) == 1
