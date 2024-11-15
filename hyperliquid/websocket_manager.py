import json
import logging
import threading
import time
from collections import defaultdict

import websocket
import orjson
import sentry_sdk

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


class WebSocketError(Exception):
    """Base exception for WebSocket errors"""
    pass

class WebSocketConnectionError(WebSocketError):
    """Raised when WebSocket connection is lost or cannot be established"""
    pass

class WebSocketTimeoutError(WebSocketError):
    """Raised when WebSocket times out (no pong received)"""
    pass

class WebsocketManager(threading.Thread):
    def __init__(self, base_url, wallet_label=None, wallet_group=None):
        super().__init__()
        self.subscription_id_counter = 0
        self.ws_ready = False
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        ws_url = "ws" + base_url[len("http") :] + "/ws"
        self.ws = websocket.WebSocketApp(ws_url, on_message=self.on_message, on_open=self.on_open)
        self.ping_sender = threading.Thread(target=self.send_ping)

        # Add new attributes
        self.running = True
        self.main_thread = None
        self._stop_event = threading.Event()
        
        # Setup logger with wallet context
        logger_name = f"wallet.{wallet_group}.{wallet_label}" if wallet_label and wallet_group else __name__
        self.logger = logging.getLogger(logger_name)
        
        # Timing configurations
        self.ping_interval = 4
        self.pong_timeout = 12
        self.health_check_interval = 2.0
        self.health_info_log_interval = 10
        self.thread_shutdown_timeout = 2
        
        # Health check thread
        self.health_checker = threading.Thread(
            target=self._health_check,
            name="WebSocket-HealthChecker",
            daemon=True
        )
        
        self._subscriptions = []
        self._connection_lock = threading.Lock()
        self.last_pong_time = time.time()
        self._request_id = 0
        self._request_callbacks = {}
        self._connection_error = None

    def run(self):
        """Override run to track main thread and start health checker"""
        self.ping_sender.start()
        self.health_checker.start()
        self.main_thread = threading.current_thread()
        self.ws.run_forever()

    def send_ping(self):
        """Modified ping sender with proper timing"""
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.ping_interval):
                self.logger.info("Ping thread received stop signal")
                return
                
            if not self._stop_event.is_set():
                self.logger.debug("Websocket sending ping")
                try:
                    self.ws.send(orjson.dumps({"method": "ping"}))
                except:
                    self.logger.info("Ping thread encountered error, stopping")
                    break

    def _health_check(self):
        """Health check implementation"""
        last_info_log = 0
        
        while not self._stop_event.is_set():
            if self._stop_event.wait(self.health_check_interval):
                self.logger.info("Health check thread received stop signal")
                return

            try:
                current_time = time.time()
                time_since_last_pong = current_time - self.last_pong_time
                
                self.logger.debug(
                    f"Health check - Time since last pong: {time_since_last_pong:.2f}s, "
                    f"Connection status: {'Connected' if self.ws.sock and self.ws.sock.connected else 'Disconnected'}"
                )
                
                if current_time - last_info_log >= self.health_info_log_interval:
                    self.logger.info(
                        f"WebSocket health status - Connected: {bool(self.ws.sock and self.ws.sock.connected)}, "
                        f"Last pong: {time_since_last_pong:.2f}s ago"
                    )
                    last_info_log = current_time

                if time_since_last_pong > self.pong_timeout:
                    self.logger.error(f"No pong received for {time_since_last_pong:.2f} seconds")
                    self._connection_error = WebSocketTimeoutError(
                        f"No pong received for {time_since_last_pong:.2f} seconds"
                    )
                    self.stop()
                    return
                elif not self.ws.sock or not self.ws.sock.connected:
                    self.logger.error("WebSocket connection lost")
                    self._connection_error = WebSocketConnectionError("WebSocket connection lost")
                    self.stop()
                    return
                
            except Exception as e:
                self.logger.error(f"Error in health check: {str(e)}")
                sentry_sdk.capture_exception(e)
                self._connection_error = e
                self.stop()
                return

    def on_message(self, _ws, message):
        if message == "Websocket connection established.":
            self.logger.debug(message)
            return

        self.logger.debug(f"on_message {message}")
        
        try:
            ws_msg: WsMsg = orjson.loads(message)
            identifier = ws_msg_to_identifier(ws_msg)

            # Handle pong (original logic first)
            if identifier == "pong":
                self.last_pong_time = time.time()
                self.logger.debug("Websocket received pong")
                return

            # Handle our new post responses
            if isinstance(ws_msg, dict) and ws_msg.get("channel") == "post":
                data = ws_msg.get("data", {})
                request_id = data.get("id")
                
                if request_id in self._request_callbacks:
                    callback = self._request_callbacks.pop(request_id)
                    response = data.get("response", {})
                    callback(response)
                    self.logger.debug(f"Processed response for request ID {request_id}")
                return

            # Original message handling
            if identifier is None:
                self.logger.debug("Websocket not handling empty message")
                return
            
            active_subscriptions = self.active_subscriptions[identifier]
            if len(active_subscriptions) == 0:
                print("Websocket message from an unexpected subscription:", message, identifier)
            else:
                for active_subscription in active_subscriptions:
                    active_subscription.callback(ws_msg)

        except orjson.JSONDecodeError:
            self.logger.warning("Failed to decode websocket message")
        except Exception as e:
            self.logger.error(f"Error processing websocket message: {str(e)}")
            sentry_sdk.capture_exception(e)

    def send_signed_request(self, action_payload, callback=None):
        """Send signed request implementation"""
        with self._connection_lock:
            try:
                self._request_id += 1
                request = {
                    "method": "post",
                    "id": self._request_id,
                    "request": {
                        "type": "action",
                        "payload": action_payload
                    }
                }
                
                if callback:
                    self._request_callbacks[self._request_id] = callback
                
                self.logger.debug(f"Sending signed request ID {self._request_id}")
                self.ws.send(orjson.dumps(request))
                return self._request_id
            except Exception as e:
                self.logger.error(f"Error sending signed request: {str(e)}")
                raise

    def stop(self):
        """Clean shutdown implementation"""
        self.logger.info("Starting WebSocket manager shutdown...")
        self.running = False
        self._stop_event.set()
        
        if self.ws:
            self.logger.info("Closing WebSocket connection...")
            self.ws.keep_running = False
            self.ws.close()
            self.logger.info("WebSocket connection closed")
        
        current_thread = threading.current_thread()
        
        for thread, name in [
            (self.ping_sender, "ping sender"),
            (self.health_checker, "health checker"),
            (self.main_thread, "main WebSocket")
        ]:
            if thread and current_thread != thread:
                self.logger.info(f"Waiting for {name} thread to finish...")
                thread.join(timeout=self.thread_shutdown_timeout)
                if thread.is_alive():
                    self.logger.warning(f"{name.capitalize()} thread did not shut down cleanly")
        
        self.logger.info("WebSocket manager shutdown complete")

    def is_healthy(self):
        """Health check implementation"""
        return (
            not self._connection_error and 
            hasattr(self, 'ws') and 
            self.ws and 
            self.ws.sock and 
            self.ws.sock.connected
        )

    def get_error(self):
        """Return connection error"""
        return self._connection_error

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
