import json
import logging
import threading
import time
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


class WebsocketManager(threading.Thread):
    def __init__(self, base_url):
        super().__init__()
        self.subscription_id_counter = 0
        self.ws_ready = False
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        self.base_url = base_url
        self.ws = None
        self.reconnect_interval = 5
        self.should_reconnect = True
        self.ping_sender = None

    def start_ping_sender(self):
        if self.ping_sender is None or not self.ping_sender.is_alive():
            self.ping_sender = threading.Thread(target=self.send_ping)
            self.ping_sender.start()

    def connect(self):
        ws_url = "ws" + self.base_url[len("http") :] + "/ws"
        self.ws = websocket.WebSocketApp(
            ws_url, on_message=self.on_message, on_open=self.on_open, on_close=self.on_close, on_error=self.on_error
        )

    def reconnect(self):
        while self.should_reconnect:
            try:
                self.connect()
                self.ws.run_forever()
            except Exception as e:
                logging.error(f"WebSocket connection failed: {e}")

            logging.info(f"Attempting to reconnect in {self.reconnect_interval} seconds...")
            time.sleep(self.reconnect_interval)

            self.start_ping_sender()

    def run(self):
        self.start_ping_sender()
        self.reconnect()

    def send_ping(self):
        while self.should_reconnect:
            time.sleep(50)
            if self.ws and self.ws.sock and self.ws.sock.connected:
                try:
                    logging.debug("Websocket sending ping")
                    self.ws.send(json.dumps({"method": "ping"}))
                except websocket.WebSocketConnectionClosedException:
                    logging.warning("Connection closed while trying to send ping. Triggering reconnect.")
                    self.ws_ready = False
                    break

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

    def on_close(self, _ws, close_status_code, close_msg):
        logging.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self.ws_ready = False

    def on_error(self, _ws, error):
        logging.error(f"WebSocket error: {error}")

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
            if subscription["type"] == "userEvents":
                # TODO: ideally the userEvent messages would include the user so that we can support multiplexing them
                if len(self.active_subscriptions[identifier]) != 0:
                    raise NotImplementedError("Cannot subscribe to UserEvents multiple times")
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

    def close(self):
        self.should_reconnect = False
        if self.ping_sender:
            self.ping_sender.join()
        if self.ws:
            self.ws.close()
