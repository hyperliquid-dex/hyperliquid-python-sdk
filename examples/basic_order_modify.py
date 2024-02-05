from hyperliquid.utils import constants
import example_utils


def main():
    address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True)

    # Place an order that should rest by setting the price very low
    order_result = exchange.order("ETH", True, 0.2, 1100, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Modify the order by oid
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            oid = status["resting"]["oid"]
            order_status = info.query_order_by_oid(address, oid)
            print("Order status by oid:", order_status)

            modify_result = exchange.modify_order(oid, "ETH", True, 0.1, 1105, {"limit": {"tif": "Gtc"}})
            print("modify result:", modify_result)


if __name__ == "__main__":
    main()
