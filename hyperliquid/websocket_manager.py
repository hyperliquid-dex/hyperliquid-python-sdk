import json
import logging
import threading
from collections import defaultdict
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple

# Assuming these types are defined in hyperliquid.utils.types
# NamedTuple and standard types are explicitly imported from typing/collections for clarity.
Subscription = Dict[str, Any]  # Represents a subscription request payload
WsMsg = Dict[str, Any]  # Represents an incoming WebSocket message payload

# Set up logging for better visibility than print statements
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s')

# NamedTuple for storing active subscription details
ActiveSubscription = NamedTuple(
    "ActiveSubscription", 
    [("callback", Callable[[Any], None]), ("subscription_id", int)]
)


def _get_channel_details(channel_type: str, data: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Helper to extract coin, user, and interval from subscription/message data.
    Returns (coin, user) or (coin, interval) based on the channel type.
    """
    coin = None
    user = None
    interval = None
    
    if data:
        # Normalize keys based on how they appear in the subscription request or data payload
        coin = data.get("coin") or data.get("s")
        user = data.get("user")
        interval = data.get("interval") or data.get("i")

    # Normalize coin and user to lowercase if they exist
    coin = coin.lower() if isinstance(coin, str) else None
    user = user.lower() if isinstance(user, str) else None
    
    return coin, user, interval


def subscription_to_identifier(subscription: Subscription) -> str:
    """
    Generates a unique string identifier for a given subscription request.
    This identifier is used to map incoming messages to the correct callbacks.
    """
    channel_type = subscription["type"]
    coin, user, interval = _get_channel_details(channel_type, subscription)
    
    if channel_type == "allMids":
        return "allMids"
    elif channel_type in ["l2Book", "trades", "bbo", "activeAssetCtx"]:
        # All market data channels keyed by coin
        if not coin:
            raise ValueError(f"Subscription type {channel_type} requires 'coin'")
        return f'{channel_type}:{coin}'
    elif channel_type == "candle":
        if not coin or not interval:
            raise ValueError(f"Subscription type {channel_type} requires 'coin' and 'interval'")
        return f'{channel_type}:{coin},{interval}'
    elif channel_type in ["userFills", "userFundings", "userNonFundingLedgerUpdates", "webData2"]:
        # User-specific channels keyed by user address
        if not user:
            raise ValueError(f"Subscription type {channel_type} requires 'user'")
        return f'{channel_type}:{user}'
    elif channel_type == "activeAssetData":
        if not coin or not user:
            raise ValueError(f"Subscription type {channel_type} requires 'coin' and 'user'")
        return f'{channel_type}:{coin},{user}'
    elif channel_type in ["userEvents", "orderUpdates"]:
        # Channels that currently cannot be multiplexed by user
        return channel_type
        
    raise ValueError(f"Unknown subscription type: {channel_type}")


def ws_msg_to_identifier(ws_msg: WsMsg) -> Optional[str]:
    """
    Generates a unique string identifier from an incoming WebSocket message.
    """
    channel_type = ws_msg.get("channel")
    if not channel_type:
        return None # Message missing channel information
        
    # Handle trades channel edge case where data might be empty
    if channel_type == "trades" and len(ws_msg.get("data", [])) == 0:
        return None

    if channel_type == "pong":
        return "pong"
    
    # Use the unified identifier logic for complex channels
    data = ws_msg.get("data")
    if not data:
        # Handle simple channels like 'user'/'userEvents' and 'orderUpdates'
        if channel_type == "user":
            return "userEvents"
        if channel_type == "orderUpdates":
            return "orderUpdates"
        if channel_type == "allMids":
            return "allMids"
        return None # Message for a complex channel without data

    # Rename 'user' channel to 'userEvents' to match subscription type
    if channel_type == "user":
        channel_type = "userEvents"
        
    # Normalize channel names that map to the same identifier
    if channel_type == "activeSpotAssetCtx":
        channel_type = "activeAssetCtx"

    coin, user, interval = _get_channel_details(channel_type, data)
    
    # Map messages back to the corresponding subscription identifier format
    if channel_type == "allMids":
        return "allMids"
    elif channel_type in ["l2Book", "trades", "bbo", "activeAssetCtx"]:
        return f'{channel_type}:{coin}'
    elif channel_type == "candle":
        return f'{channel_type}:{coin},{interval}'
    elif channel_type in ["userFills", "userFundings", "userNonFundingLedgerUpdates", "webData2", "userEvents"]:
        return f'{channel_type}:{user}'
    elif channel_type == "activeAssetData":
        return f'{channel_type}:{coin},{user}'
    elif channel_type == "orderUpdates":
        return channel_type

    return None # Unknown channel type with data


class WebsocketManager(threading.Thread):
    def __init__(self, base_url: str):
        # Initialize the base class (threading.Thread)
        super().__init__()
        
        # Internal state management
        self.subscription_id_counter = 0
        self.ws_ready = False
        self.queued_subscriptions: List[Tuple[Subscription, ActiveSubscription]] = []
        # Maps identifier string (e.g., 'l2Book:eth') to a list of callbacks
        self.active_subscriptions: Dict[str, List[ActiveSubscription]] = defaultdict(list)
        
        # WebSocket setup
        # Convert http/https to ws/wss and append the WebSocket path
        ws_url = "ws" + base_url[len("http") :] + "/ws"
        self.ws = websocket.WebSocketApp(ws_url, on_message=self.on_message, on_open=self.on_open)
        
        # Ping thread setup
        self.stop_event = threading.Event()
        self.ping_sender = threading.Thread(target=self.send_ping, name="PingSender")

    def run(self) -> None:
        """Starts the WebSocket connection and the ping sender thread."""
        self.ping_sender.start()
        # run_forever handles the main websocket loop and auto-reconnect logic
        self.ws.run_forever()

    def send_ping(self) -> None:
        """Sends a ping message to the server periodically to keep the connection alive."""
        # Ping every 50 seconds (standard practice for many exchanges)
        while not self.stop_event.wait(50):
            # Check if the main WebSocket loop is still running before sending
            if not self.ws.keep_running:
                break
            logging.debug("Websocket sending ping")
            
            try:
                # Use send() with a timeout if needed, but the library manages the connection state
                self.ws.send(json.dumps({"method": "ping"}))
            except websocket.WebSocketConnectionClosedException:
                logging.warning("Ping failed: connection already closed.")
                break
            except Exception as e:
                logging.error(f"Error sending ping: {e}")
                break
        logging.debug("Websocket ping sender stopped")

    def stop(self) -> None:
        """Stops the WebSocket connection and cleans up threads."""
        self.stop_event.set() # Signal the ping sender to stop
        self.ws.close() # Close the main WebSocket connection
        
        # Ensure the ping thread terminates cleanly
        if self.ping_sender.is_alive():
            self.ping_sender.join()
        logging.info("WebsocketManager stopped successfully.")


    def on_message(self, _ws: Any, raw_message: str) -> None:
        """
        Handler for incoming WebSocket messages.
        Parses JSON and routes the message to the correct callback(s).
        """
        if raw_message == "Websocket connection established.":
            logging.debug(raw_message)
            return

        try:
            ws_msg: WsMsg = json.loads(raw_message)
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON message: {raw_message}")
            return
            
        logging.debug(f"Received message: {ws_msg}")
        identifier = ws_msg_to_identifier(ws_msg)
        
        if identifier == "pong":
            logging.debug("Websocket received pong")
            return
        
        if identifier is None:
            # This covers empty trade messages or messages with unhandled channels/data
            logging.debug(f"Websocket skipping message without identifier or data: {ws_msg}")
            return
            
        # Dispatch the message to all registered callbacks for this identifier
        active_subscriptions = self.active_subscriptions[identifier]
        
        if not active_subscriptions:
            # Use logging.warning instead of print for unexpected messages
            logging.warning(f"Message received for an unexpected subscription: {identifier} - {ws_msg}")
        else:
            # OPTIMIZATION: Callbacks should ideally run in a ThreadPoolExecutor 
            # to prevent a slow callback from blocking the main WebSocket thread.
            # For simplicity, we keep it synchronous here, but a production-grade 
            # library should consider non-blocking execution.
            for active_subscription in active_subscriptions:
                try:
                    active_subscription.callback(ws_msg)
                except Exception as e:
                    # Catch and log errors in callbacks to prevent killing the main thread
                    logging.error(f"Error in callback for {identifier} (ID: {active_subscription.subscription_id}): {e}")


    def on_open(self, _ws: Any) -> None:
        """Handler called when the WebSocket connection is established."""
        logging.info("Websocket connection established. Subscribing queued requests.")
        self.ws_ready = True
        
        # Process any subscriptions that were requested before the connection was ready
        while self.queued_subscriptions:
            subscription, active_subscription = self.queued_subscriptions.pop(0)
            # Re-call subscribe, which will now bypass the queue and send the message
            self.subscribe(
                subscription, 
                active_subscription.callback, 
                active_subscription.subscription_id
            )


    def subscribe(
        self, subscription: Subscription, callback: Callable[[Any], None], subscription_id: Optional[int] = None
    ) -> int:
        """Registers a callback for a subscription. Queues if connection is not ready."""
        
        # Assign a new ID if not provided
        if subscription_id is None:
            self.subscription_id_counter += 1
            subscription_id = self.subscription_id_counter
            
        active_sub = ActiveSubscription(callback, subscription_id)
        
        if not self.ws_ready:
            logging.info(f"Enqueueing subscription (ID: {subscription_id})")
            self.queued_subscriptions.append((subscription, active_sub))
            return subscription_id
        
        # Connection is ready, proceed with immediate subscription
        logging.info(f"Subscribing to {subscription['type']} (ID: {subscription_id})")
        identifier = subscription_to_identifier(subscription)
        
        if identifier in ("userEvents", "orderUpdates"):
            # Enforce single subscription for channels that lack user/coin information 
            # in the response message, making multiplexing impossible for now.
            if self.active_subscriptions[identifier]:
                raise NotImplementedError(
                    f"Cannot subscribe to {identifier} multiple times without user-specific response data."
                )
        
        self.active_subscriptions[identifier].append(active_sub)
        
        try:
            self.ws.send(json.dumps({"method": "subscribe", "subscription": subscription}))
        except Exception as e:
            logging.error(f"Failed to send subscribe message for {identifier}: {e}")
            # If sending fails, remove the subscription from active list
            self.active_subscriptions[identifier] = [
                x for x in self.active_subscriptions[identifier] if x.subscription_id != subscription_id
            ]
            raise RuntimeError("Subscription failed to send, check connection.")

        return subscription_id


    def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        """Removes a callback from a subscription. Sends unsubscribe command if it was the last callback."""
        if not self.ws_ready:
            # Note: Unsubscribing a queued item would require checking the queued_subscriptions list as well.
            # The current implementation only supports unsubscribing from active connections.
            raise NotImplementedError("Can't unsubscribe before websocket connected or for queued subscriptions.")
            
        identifier = subscription_to_identifier(subscription)
        active_subscriptions = self.active_subscriptions[identifier]
        
        # Filter out the specific subscription ID
        new_active_subscriptions = [x for x in active_subscriptions if x.subscription_id != subscription_id]
        
        unsubscribed = len(active_subscriptions) != len(new_active_subscriptions)
        
        if unsubscribed:
            # If the list is now empty, send the 'unsubscribe' command to the server
            if not new_active_subscriptions:
                logging.info(f"Unsubscribing from {identifier} (last callback removed)")
                self.ws.send(json.dumps({"method": "unsubscribe", "subscription": subscription}))
            
            # Update the active list regardless of whether the unsubscribe command was sent
            self.active_subscriptions[identifier] = new_active_subscriptions

        return unsubscribed
