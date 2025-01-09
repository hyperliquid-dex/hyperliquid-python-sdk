# This is an end to end example of a very basic adding strategy.
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
    L2BookData,
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

# How far from the best bid and offer this strategy ideally places orders. Currently set to 0.3%.
# i.e., if the best bid is $1000, this strategy will place a resting bid at $997 (1000 - 0.3% of 1000).
DEPTH = 0.003

# How far from the target price a resting order can deviate before the strategy will cancel and replace it.
# i.e., using the same example as above of a best bid of $1000 and targeted depth of 0.3% (a $3 difference).
# Bids within $3 * 0.5 = $1.5 of the ideal price will not be cancelled. Therefore, any bids > $998.5 or < $995.5
# will be cancelled and replaced.
ALLOWABLE_DEVIATION = 0.5

# The maximum absolute position value the strategy can accumulate in units of the coin.
# i.e., the strategy will place orders such that it can long up to 1 ETH or short up to 1 ETH.
MAX_POSITION = 1.0

# The coin to add liquidity on.
COIN = "ETH"

# The interval (in seconds) at which the polling function runs.
POLL_INTERVAL = 10

# The maximum time (in milliseconds) to wait for an in-flight order before treating it as cancelled.
ORDER_TIMEOUT = 10000

# The time (in milliseconds) to keep recently cancelled orders before cleaning them up.
CANCEL_CLEANUP_TIME = 30000

# --------------------------- TYPE DEFINITIONS ---------------------------

InFlightOrder = TypedDict("InFlightOrder", {"type": Literal["in_flight_order"], "time": int})
Resting = TypedDict("Resting", {"type": Literal["resting"], "px": float, "oid": int})
Cancelled = TypedDict("Cancelled", {"type": Literal["cancelled"]})
ProvideState = Union[InFlightOrder, Resting, Cancelled]


def side_to_int(side: Side) -> int:
    """Convert side ('A' for Ask, 'B' for Bid) to an integer multiplier."""
    return 1 if side == "A" else -1


def side_to_uint(side: Side) -> int:
    """Convert side ('A' for Ask, 'B' for Bid) to an unsigned integer (0 or 1)."""
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

        # Subscribe to updates
        self.subscribe_to_updates()

        # Start the polling thread
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

    def handle_order_placement(self, side: Side, book_data: L2BookData) -> None:
        """Handle the placement and cancellation of orders based on the order book update."""
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
            print(f"Cancelling order due to deviation: oid:{oid}, side:{side}, ideal_price:{ideal_price}")
            response = self.exchange.cancel(COIN, oid)
            if response["status"] == "ok":
                self.recently_cancelled_oid_to_time[oid] = get_timestamp_ms()
                self.provide_state[side] = {"type": "cancelled"}
            else:
                logging.error(f"Failed to cancel order {oid} for side {side}: {response}")

    def check_in_flight_order(self, side: Side, provide_state: InFlightOrder) -> None:
        """Check if the in-flight order has timed out."""
        if get_timestamp_ms() - provide_state["time"] > ORDER_TIMEOUT:
            print("Order is still in flight after timeout, treating as cancelled.")
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
        print(f"Placing order: size:{size}, price:{px}, side:{side}")
        response = self.exchange.order(COIN, side == "B", size, px, {"limit": {"tif": "Alo"}})
        if response["status"] == "ok":
            status = response["response"]["data"]["statuses"][0]
            if "resting" in status:
                self.provide_state[side] = {"type": "resting", "px": px, "oid": status["resting"]["oid"]}

    def on_user_events(self, user_events: UserEventsMsg) -> None:
        """Callback for user events (e.g., fills)."""
        print(user_events)
        if "fills" in user_events["data"]:
            with open("fills", "a+") as f:
                f.write(json.dumps(user_events["data"]["fills"]) + "\n")
        # Set the position to None so that we don't place more orders without knowing our position
        # You might want to also update provide_state to account for the fill. This could help avoid sending an
        # unneeded cancel or failing to send a new order to replace the filled order, but we skipped this logic
        # to make the example simpler
        self.position = None

    def poll(self) -> None:
        """Poll open orders and user positions periodically."""
        while True:
            # Fetch open orders
            open_orders = self.info.open_orders(self.exchange.wallet.address)
            print("open_orders", open_orders)

            # Collect valid order IDs (from recently cancelled orders and resting orders)
            ok_oids = set(self.recently_cancelled_oid_to_time.keys())
            for provide_state in self.provide_state.values():
                if provide_state["type"] == "resting":
                    ok_oids.add(provide_state["oid"])

            # Cancel any unknown orders
            for open_order in open_orders:
                if open_order["coin"] == COIN and open_order["oid"] not in ok_oids:
                    print("Cancelling unknown oid", open_order["oid"])
                    self.exchange.cancel(open_order["coin"], open_order["oid"])

            # Clean up recently cancelled orders after a timeout
            current_time = get_timestamp_ms()
            self.recently_cancelled_oid_to_time = {
                oid: timestamp
                for oid, timestamp in self.recently_cancelled_oid_to_time.items()
                if current_time - timestamp <= CANCEL_CLEANUP_TIME
            }
            self.refresh_position()
            time.sleep(POLL_INTERVAL)

    def refresh_position(self) -> None:
        """Refresh the user’s current position."""
        user_state = self.info.user_state(self.address)
        for position in user_state.get("assetPositions", []):
            if position["position"]["coin"] == COIN:
                self.position = float(position["position"]["szi"])
                return
        self.position = 0.0


def main():
    # Setting this to logging.DEBUG can be helpful for debugging websocket callback issues
    logging.basicConfig(level=logging.INFO)
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL)
    BasicAdder(address, info, exchange)


if __name__ == "__main__":
    main()
