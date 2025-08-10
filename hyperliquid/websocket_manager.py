import json
import logging
import threading
from collections import defaultdict

import websocket

from hyperliquid.utils.types import Any, Callable, Dict, List, NamedTuple, Optional, Subscription, Tuple, WsMsg

ActiveSubscription = NamedTuple("ActiveSubscription", [("callback", Callable[[Any], None]), ("subscription_id", int)])


def subscription_to_identifier(subscription: Subscription) -> str:
    if subscription["type"] == "allMids":
        return "allMids"
    elif subscription["type"] == "l2Book":
        return f'l2Book:{subscription["coin"].lower()}'
    elif subscription["type"] == "trades":
        return f'trades:{subscription["coin"].lower()}'
    elif subscription["type"] == "userEvents":
        return "userEvents"
    elif subscription["type"] == "userFills":
        return f'userFills:{subscription["user"].lower()}'
    elif subscription["type"] == "candle":
        return f'candle:{subscription["coin"].lower()},{subscription["interval"]}'
    elif subscription["type"] == "orderUpdates":
        return "orderUpdates"
    elif subscription["type"] == "userFundings":
        return f'userFundings:{subscription["user"].lower()}'
    elif subscription["type"] == "userNonFundingLedgerUpdates":
        return f'userNonFundingLedgerUpdates:{subscription["user"].lower()}'
    elif subscription["type"] == "webData2":
        return f'webData2:{subscription["user"].lower()}'
    elif subscription["type"] == "bbo":
        return f'bbo:{subscription["coin"].lower()}'
    elif subscription["type"] == "activeAssetCtx":
        return f'activeAssetCtx:{subscription["coin"].lower()}'
    elif subscription["type"] == "activeAssetData":
        return f'activeAssetData:{subscription["coin"].lower()},{subscription["user"].lower()}'


def ws_msg_to_identifier(ws_msg: WsMsg) -> Optional[str]:
    if ws_msg["channel"] == "pong":
        return "pong"
    elif ws_msg["channel"] == "allMids":
        return "allMids"
    elif ws_msg["channel"] == "l2Book":
        return f'l2Book:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "trades":
        trades = ws_msg["data"]
        if len(trades) == 0:
            return None
        else:
            return f'trades:{trades[0]["coin"].lower()}'
    elif ws_msg["channel"] == "user":
        return "userEvents"
    elif ws_msg["channel"] == "userFills":
        return f'userFills:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "candle":
        return f'candle:{ws_msg["data"]["s"].lower()},{ws_msg["data"]["i"]}'
    elif ws_msg["channel"] == "orderUpdates":
        return "orderUpdates"
    elif ws_msg["channel"] == "userFundings":
        return f'userFundings:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "userNonFundingLedgerUpdates":
        return f'userNonFundingLedgerUpdates:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "webData2":
        return f'webData2:{ws_msg["data"]["user"].lower()}'
    elif ws_msg["channel"] == "bbo":
        return f'bbo:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "activeAssetCtx" or ws_msg["channel"] == "activeSpotAssetCtx":
        return f'activeAssetCtx:{ws_msg["data"]["coin"].lower()}'
    elif ws_msg["channel"] == "activeAssetData":
        return f'activeAssetData:{ws_msg["data"]["coin"].lower()},{ws_msg["data"]["user"].lower()}'


def identifier_to_subscription(identifier: str) -> dict:
    if identifier == "allMids":
        return {"type": "allMids"}
    elif identifier == "userEvents":
        return {"type": "userEvents"}
    elif identifier == "orderUpdates":
        return {"type": "orderUpdates"}

    if identifier.startswith("l2Book:"):
        coin = identifier[len("l2Book:") :]
        return {"type": "l2Book", "coin": coin}
    elif identifier.startswith("trades:"):
        coin = identifier[len("trades:") :]
        return {"type": "trades", "coin": coin}
    elif identifier.startswith("userFills:"):
        user = identifier[len("userFills:") :]
        return {"type": "userFills", "user": user}
    elif identifier.startswith("candle:"):
        data = identifier[len("candle:") :]
        coin, interval = data.split(",", 1)
        return {"type": "candle", "coin": coin, "interval": interval}
    elif identifier.startswith("userFundings:"):
        user = identifier[len("userFundings:") :]
        return {"type": "userFundings", "user": user}
    elif identifier.startswith("userNonFundingLedgerUpdates:"):
        user = identifier[len("userNonFundingLedgerUpdates:") :]
        return {"type": "userNonFundingLedgerUpdates", "user": user}
    elif identifier.startswith("webData2:"):
        user = identifier[len("webData2:") :]
        return {"type": "webData2", "user": user}
    elif identifier.startswith("bbo:"):
        coin = identifier[len("bbo:") :]
        return {"type": "bbo", "coin": coin}
    elif identifier.startswith("activeAssetCtx:"):
        coin = identifier[len("activeAssetCtx:") :]
        return {"type": "activeAssetCtx", "coin": coin}
    elif identifier.startswith("activeAssetData:"):
        data = identifier[len("activeAssetData:") :]
        coin, user = data.split(",", 1)
        return {"type": "activeAssetData", "coin": coin, "user": user}

    raise ValueError(f"Unknown subscription identifier: {identifier}")


class WebsocketManager(threading.Thread):
    def __init__(self, base_url):
        super().__init__()
        self.subscription_id_counter = 0
        self.ws_ready = False
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        ws_url = "ws" + base_url[len("http") :] + "/ws"
        self.ws = websocket.WebSocketApp(ws_url, on_message=self.on_message, on_open=self.on_open)
        self.ping_sender = threading.Thread(target=self.send_ping)
        self.stop_event = threading.Event()

    def run(self):
        self.ping_sender.start()
        self.ws.run_forever()

    def stop(self):
        self.stop_event.set()
        self.ws.close()
        if self.ping_sender.is_alive():
            self.ping_sender.join()

    def on_message(self, _ws, message):
        if message == "Websocket connection established.":
            logging.debug(message)
            return
        logging.debug(f"on_message {message}")
        ws_msg: WsMsg = json.loads(message)
        identifier = ws_msg_to_identifier(ws_msg)
        if identifier == "pong":
            logging.debug("Websocket received pong")
            return
        if identifier is None:
            logging.debug("Websocket not handling empty message")
            return
        active_subscriptions = self.active_subscriptions[identifier]
        if len(active_subscriptions) == 0:
            print("Websocket message from an unexpected subscription:", message, identifier)
        else:
            for active_subscription in active_subscriptions:
                active_subscription.callback(ws_msg)

    def on_open(self, _ws):
        logging.debug("on_open")
        self.ws_ready = True
        for subscription, active_subscription in self.queued_subscriptions:
            self.subscribe(subscription, active_subscription.callback, active_subscription.subscription_id)

    def subscribe(
        self, subscription: Subscription, callback: Callable[[Any], None], subscription_id: Optional[int] = None
    ) -> int:
        if subscription_id is None:
            self.subscription_id_counter += 1
            subscription_id = self.subscription_id_counter
        if not self.ws_ready:
            logging.debug("enqueueing subscription")
            self.queued_subscriptions.append((subscription, ActiveSubscription(callback, subscription_id)))
        else:
            logging.debug("subscribing")
            identifier = subscription_to_identifier(subscription)
            if identifier == "userEvents" or identifier == "orderUpdates":
                # TODO: ideally the userEvent and orderUpdates messages would include the user so that we can multiplex
                if len(self.active_subscriptions[identifier]) != 0:
                    raise NotImplementedError(f"Cannot subscribe to {identifier} multiple times")
            self.active_subscriptions[identifier].append(ActiveSubscription(callback, subscription_id))
            self.ws.send(json.dumps({"method": "subscribe", "subscription": subscription}))
        return subscription_id

    def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        if not self.ws_ready:
            raise NotImplementedError("Can't unsubscribe before websocket connected")
        identifier = subscription_to_identifier(subscription)
        active_subscriptions = self.active_subscriptions[identifier]
        new_active_subscriptions = [x for x in active_subscriptions if x.subscription_id != subscription_id]
        if len(new_active_subscriptions) == 0:
            self.ws.send(json.dumps({"method": "unsubscribe", "subscription": subscription}))
        self.active_subscriptions[identifier] = new_active_subscriptions
        return len(active_subscriptions) != len(new_active_subscriptions)


class ReconnectableWebsocketManager(WebsocketManager):
    def __init__(self, base_url: str, *args, **kwargs):
        # Store base_url for reuse during reconnection
        self.base_url = base_url
        super().__init__(base_url, *args, **kwargs)
        # Override close and error handlers to trigger reconnection
        self.ws.on_close = self.on_close
        self.ws.on_error = self.on_error
        # Lock to protect shared state (queued_subscriptions, active_subscriptions)

    def send_ping(self):
        interval = 50
        while not self.stop_event.wait(interval):
            try:
                ws = getattr(self, "ws", None)
                # 연결 미준비/끊김이면 전송 스킵 (스레드는 계속 유지)
                if not ws or not getattr(ws, "keep_running", False) or not self.ws_ready:
                    continue
                logging.debug("Websocket sending app-level ping")
                ws.send(json.dumps({"method": "ping"}))
            except Exception:
                # 재연결 중 교체 등으로 생길 수 있는 예외는 조용히 스킵
                logging.debug("App-level ping skipped due to connection state", exc_info=True)
        logging.debug("Websocket ping sender stopped")

    def on_open(self, _ws):
        logging.debug("on_open")
        self.ws_ready = True
        # Process queued subscriptions and move them to active_subscriptions
        for subscription, active_subscription in self.queued_subscriptions:
            self.subscribe(
                subscription,
                active_subscription.callback,
                active_subscription.subscription_id,
            )
        self.queued_subscriptions.clear()

    def _reconnect(self):
        # Mark connection as not ready
        self.ws_ready = False
        # Move all active subscriptions back into the subscription queue
        for identifier, active_subscriptions in self.active_subscriptions.items():
            subscription = identifier_to_subscription(identifier)
            for active_subscription in active_subscriptions:
                self.subscribe(
                    subscription,
                    active_subscription.callback,
                    active_subscription.subscription_id,
                )
        self.active_subscriptions.clear()

    def _start_ping_sender(self):
        if not self.ping_sender.is_alive():
            self.ping_sender = threading.Thread(target=self.send_ping, daemon=True)
            self.ping_sender.start()

    def on_close(self, ws, close_status_code, close_msg):
        logging.debug(f"ReconnectableWebsocketManager on_close: {close_status_code} - {close_msg}")
        # If stop_event is set, skip reconnection
        if self.stop_event.is_set():
            return
        self._reconnect()

    def on_error(self, ws, error):
        logging.debug(f"ReconnectableWebsocketManager on_error: {error}")
        # If stop_event is set, skip reconnection
        if self.stop_event.is_set():
            return
        self._reconnect()

    def run(self, *, ping_timeout=15, ping_interval=30, reconnect_interval=5):
        # Start the ping sender thread (keeps connection alive)
        self._start_ping_sender()
        # Main loop to maintain the connection and handle reconnections
        while not self.stop_event.is_set():
            logging.debug("ReconnectableWebsocketManager connecting...")
            self.ws.run_forever(ping_timeout=ping_timeout, ping_interval=ping_interval)
            logging.debug(
                f"ReconnectableWebsocketManager disconnected. Reconnecting in {reconnect_interval} seconds..."
            )
            # Wait for the reconnection interval or break if stop_event is set
            if self.stop_event.wait(reconnect_interval):
                break
            # Create a new WebSocketApp instance for reconnection
            ws_url = "ws" + self.base_url[len("http") :] + "/ws"
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_message,
                on_open=self.on_open,
                on_close=self.on_close,
                on_error=self.on_error,
            )
            self._start_ping_sender()
