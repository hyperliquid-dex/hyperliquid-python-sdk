import json

import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid


def main():
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)
    info = Info(constants.TESTNET_API_URL, skip_ws=True)

    # Get the user state and print out position information
    user_state = info.user_state(account.address)
    positions = []
    for position in user_state["assetPositions"]:
        if float(position["position"]["szi"]) != 0:
            positions.append(position["position"])
    if len(positions) > 0:
        print("positions:")
        for position in positions:
            print(json.dumps(position, indent=2))
    else:
        print("no open positions")

    cloid = Cloid.from_str("0x00000000000000000000000000000001")
    # Users can also generate a cloid from an int
    # cloid = Cloid.from_int(1)
    # Place an order that should rest by setting the price very low
    exchange = Exchange(account, constants.TESTNET_API_URL)
    order_result = exchange.order("ETH", True, 0.2, 1100, {"limit": {"tif": "Gtc"}}, cloid=cloid)
    print(order_result)

    # Query the order status by cloid
    order_status = info.query_order_by_cloid(account.address, cloid)
    print("Order status by cloid:", order_status)

    # Non-existent cloid example
    invalid_cloid = Cloid.from_int(2)
    order_status = info.query_order_by_cloid(account.address, invalid_cloid)
    print("Order status by cloid:", order_status)

    # Cancel the order by cloid
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel_by_cloid("ETH", cloid)
            print(cancel_result)


if __name__ == "__main__":
    main()
