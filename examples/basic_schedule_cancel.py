import time

from hyperliquid.utils import constants
from hyperliquid.utils.signing import get_timestamp_ms
import example_utils


def main():
    address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True)

    # Place an order that should rest by setting the price very low
    order_result = exchange.order("ETH", True, 0.2, 1100, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Query the order status by oid
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            order_status = info.query_order_by_oid(address, status["resting"]["oid"])
            print("Order status by oid:", order_status)

    # Schedule cancel
    cancel_time = get_timestamp_ms() + 10000  # 10 seconds from now
    print(exchange.schedule_cancel(cancel_time))

    time.sleep(10)
    print("open orders:", info.open_orders(address))


if __name__ == "__main__":
    main()
