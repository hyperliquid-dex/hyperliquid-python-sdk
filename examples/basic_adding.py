import json
import logging
import threading
import time

import example_utils

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.signing import get_timestamp_ms
from hyperliquid.utils.types import (
    SIDES,
    Dict,
    L2BookMsg,
    L2BookSubscription,
    Literal,
    Optional,
    Side,
    TypedDict,
    Union,
    UserEventsMsg,
    UserEventsSubscription,
)

# --------------------------- CONFIGURATION ---------------------------
DEPTH = 0.003                    # Depth from the best bid/offer to place orders
ALLOWABLE_DEVIATION = 0.5        # Deviation allowed before replacing the order
MAX_POSITION = 1.0               # Maximum position to hold in units of the coin
COIN = "ETH"                     # Coin to add liquidity on
POLL_INTERVAL = 10               # Interval for polling in seconds
ORDER_TIMEOUT = 10000            # Timeout for in-flight orders in milliseconds
CANCEL_CLEANUP_TIME = 30000      # Cleanup time for cancelled orders in milliseconds

# --------------------------- TYPE DEFINITIONS ---------------------------
InFlightOrder = TypedDict("InFlightOrder", {"type": Literal["in_flight_order"], "time": int})
Resting = TypedDict("Resting", {"type": Literal["resting"], "px": float, "oid": int})
Cancelled = TypedDict("Cancelled", {"type": Literal["cancelled"]})
ProvideState = Union[InFlightOrder, Resting, Cancelled]


def side_to_int(side: Side) -> int:
    return 1 if side == "A" else -1


def side_to_uint(side: Side) -> int:
    return 1 if side == "A" else 0


class BasicAdder:
    def __init__(self, address: str, info: Info, exchange: Exchange):
        self.info = info
        self.exchange = exchange
        self.address = address
        self.position: Optional[float] = None
        self.provide_state: Dict[Side, ProvideState] = {
            "A": {"type": "cancelled"},
            "B": {"type": "cancelled"},
        }
        self.recently_cancelled_oid_to_time: Dict[int, int] = {}

        self.subscribe_to_updates()
        self.start_poller()

    def subscribe_to_updates(self) -> None:
        """Subscribe to order book and user event updates."""
        l2_book_subscription: L2BookSubscription = {"type": "l2Book", "coin": COIN}
        self.info.subscribe(l2_book_subscription, self.on_book_update)

        user_events_subscription: UserEventsSubscription = {"type": "userEvents", "user": self.address}
        self.info.subscribe(user_events_subscription, self.on_user_events)

    def start_poller(self) -> None:
        """Start the polling thread for checking open orders and positions."""
        self.poller = threading.Thread(target=self.poll, daemon=True)
        self.poller.start()

    def on_book_update(self, book_msg: L2BookMsg) -> None:
        """Callback for order book updates."""
        logging.debug(f"Received book message: {book_msg}")
        book_data = book_msg["data"]

        if book_data["coin"] != COIN:
            logging.warning("Unexpected book message, skipping.")
            return

        for side in SIDES:
            self.handle_order_placement(side, book_data)

    def handle_order_placement(self, side: Side, book_data: Dict) -> None:
        """Handle the placement and cancellation of orders."""
        book_price = float(book_data["levels"][side_to_uint(side)][0]["px"])
        ideal_distance = book_price * DEPTH
        ideal_price = book_price + (ideal_distance * side_to_int(side))

        provide_state = self.provide_state[side]

        if provide_state["type"] == "resting":
            self.maybe_cancel_order(side, provide_state, ideal_price, ideal_distance)
        elif provide_state["type"] == "in_flight_order":
            self.check_in_flight_order(side, provide_state)

        if provide_state["type"] == "cancelled":
            self.place_new_order(side, ideal_price)

    def maybe_cancel_order(self, side: Side, provide_state: Resting, ideal_price: float, ideal_distance: float) -> None:
        """Cancel the order if it deviates beyond the allowable limit."""
        distance = abs(ideal_price - provide_state["px"])
        if distance > ALLOWABLE_DEVIATION * ideal_distance:
            oid = provide_state["oid"]
            response = self.exchange.cancel(COIN, oid)
            if response["status"] == "ok":
                self.recently_cancelled_oid_to_time[oid] = get_timestamp_ms()
                self.provide_state[side] = {"type": "cancelled"}
            else:
                logging.error(f"Failed to cancel order {oid} for side {side}: {response}")

    def check_in_flight_order(self, side: Side, provide_state: InFlightOrder) -> None:
        """Check if the in-flight order has timed out."""
        if get_timestamp_ms() - provide_state["time"] > ORDER_TIMEOUT:
            logging.warning(f"Order still in flight after {ORDER_TIMEOUT // 1000}s, treating as cancelled.")
            self.provide_state[side] = {"type": "cancelled"}

    def place_new_order(self, side: Side, ideal_price: float) -> None:
        """Place a new order if conditions are met."""
        if self.position is None:
            logging.debug("Waiting for position refresh before placing order.")
            return

        size = MAX_POSITION + self.position * side_to_int(side)
        if size * ideal_price < 10:
            logging.debug("Order size too small, not placing order.")
            return

        px = float(f"{ideal_price:.5g}")
        response = self.exchange.order(COIN, side == "B", size, px, {"limit": {"tif": "Alo"}})
        if response["status"] == "ok":
            status = response["response"]["data"]["statuses"][0]
            if "resting" in status:
                self.provide_state[side] = {"type": "resting", "px": px, "oid": status["resting"]["oid"]}
        else:
            logging.error(f"Failed to place order: {response}")

    def on_user_events(self, user_events: UserEventsMsg) -> None:
        """Callback for user events (fills)."""
        if "fills" in user_events["data"]:
            with open("fills", "a+") as f:
                f.write(json.dumps(user_events["data"]["fills"]) + "\n")
        self.position = None

    def poll(self) -> None:
        """Poll open orders and user positions periodically."""
        while True:
            open_orders = self.info.open_orders(self.address)
            current_time = get_timestamp_ms()
            self.cleanup_recently_cancelled(current_time)
            self.refresh_position()
            time.sleep(POLL_INTERVAL)

    def cleanup_recently_cancelled(self, current_time: int) -> None:
        """Clean up recently cancelled orders."""
        self.recently_cancelled_oid_to_time = {
            oid: timestamp for oid, timestamp in self.recently_cancelled_oid_to_time.items()
            if current_time - timestamp < CANCEL_CLEANUP_TIME
        }

    def refresh_position(self) -> None:
        """Refresh the user’s current position."""
        user_state = self.info.user_state(self.address)
        for position in user_state.get("assetPositions", []):
            if position["position"]["coin"] == COIN:
                self.position = float(position["position"]["szi"])
                return
        self.position = 0.0


def main():
    logging.basicConfig(level=logging.INFO)
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL)
    BasicAdder(address, info, exchange)


if __name__ == "__main__":
    main()
