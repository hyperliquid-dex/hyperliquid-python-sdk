# This example shows how to place and query orders for a builder-deployed perp dex
import json

import example_utils

from hyperliquid.utils import constants

DUMMY_DEX = "test"
COIN = f"{DUMMY_DEX}:ABC"


def main():
    # Supply the builder-deployed perps dex as an argument
    address, info, exchange = example_utils.setup(
        base_url=constants.TESTNET_API_URL, skip_ws=True, perp_dexs=[DUMMY_DEX]
    )

    # Get the user state and print out position information
    user_state = info.user_state(address)
    positions = []
    for position in user_state["assetPositions"]:
        positions.append(position["position"])
    if len(positions) > 0:
        print("positions:")
        for position in positions:
            print(json.dumps(position, indent=2))
    else:
        print("no open positions")

    # Print the meta for DUMMY_DEX
    print("dummy dex meta:", info.meta(dex=DUMMY_DEX))

    # Place an order that should rest by setting the price very low
    order_result = exchange.order(COIN, True, 20, 1, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Query the order status by oid
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            order_status = info.query_order_by_oid(address, status["resting"]["oid"])
            print("Order status by oid:", order_status)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel(COIN, status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
