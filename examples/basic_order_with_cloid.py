from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    cloid = Cloid.from_str("0x00000000000000000000000000000001")
    # Users can also generate a cloid from an int
    # cloid = Cloid.from_int(1)
    # Place an order that should rest by setting the price very low
    order_result = exchange.order("ETH", True, 0.2, 1100, {"limit": {"tif": "Gtc"}}, cloid=cloid)
    print(order_result)

    # Query the order status by cloid
    order_status = info.query_order_by_cloid(address, cloid)
    print("Order status by cloid:", order_status)

    # Non-existent cloid example
    invalid_cloid = Cloid.from_int(2)
    order_status = info.query_order_by_cloid(address, invalid_cloid)
    print("Order status by cloid:", order_status)

    # Cancel the order by cloid
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel_by_cloid("ETH", cloid)
            print(cancel_result)


if __name__ == "__main__":
    main()
