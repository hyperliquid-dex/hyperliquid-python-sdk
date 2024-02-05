import argparse

from hyperliquid.utils import constants
import example_utils


def main():
    parser = argparse.ArgumentParser(description="basic_tpsl")
    parser.add_argument("--is_buy", action="store_true")
    args = parser.parse_args()

    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    is_buy = args.is_buy
    # Place an order that should execute by setting the price very aggressively
    order_result = exchange.order("ETH", is_buy, 0.02, 2500 if is_buy else 1500, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Place a stop order
    stop_order_type = {"trigger": {"triggerPx": 1600 if is_buy else 2400, "isMarket": True, "tpsl": "sl"}}
    stop_result = exchange.order("ETH", not is_buy, 0.02, 1500 if is_buy else 2500, stop_order_type, reduce_only=True)
    print(stop_result)

    # Cancel the order
    if stop_result["status"] == "ok":
        status = stop_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)

    # Place a tp order
    tp_order_type = {"trigger": {"triggerPx": 1600 if is_buy else 2400, "isMarket": True, "tpsl": "tp"}}
    tp_result = exchange.order("ETH", not is_buy, 0.02, 2500 if is_buy else 1500, tp_order_type, reduce_only=True)
    print(tp_result)

    # Cancel the order
    if tp_result["status"] == "ok":
        status = tp_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
