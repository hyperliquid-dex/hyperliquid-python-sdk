import argparse

import example_utils

from hyperliquid.utils import constants


def main():
    parser = argparse.ArgumentParser(description="basic_tpsl")
    parser.add_argument("--is_buy", action="store_true")
    args = parser.parse_args()

    _, _, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    is_buy = args.is_buy
    coin = "ETH"
    sz = 0.02
    px = 3500 if is_buy else 2500
    trigger_px = 2600 if is_buy else 3400
    sl_px = 2500 if is_buy else 3500
    # Place an order that should execute by setting the price very aggressively, the above prices were set when ETH was at 3000
    order_result = exchange.order(coin, is_buy, sz, px, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Place a stop order
    stop_order_type = {"trigger": {"triggerPx": trigger_px, "isMarket": True, "tpsl": "sl"}}
    stop_result = exchange.order("ETH", not is_buy, sz, sl_px, stop_order_type, reduce_only=True)
    print(stop_result)

    # Cancel the order
    if stop_result["status"] == "ok":
        status = stop_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)

    # Place a tp order
    tp_order_type = {"trigger": {"triggerPx": px, "isMarket": True, "tpsl": "tp"}}
    tp_result = exchange.order("ETH", not is_buy, sz, px, tp_order_type, reduce_only=True)
    print(tp_result)

    # Cancel the order
    if tp_result["status"] == "ok":
        status = tp_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)

    # Alternatively use grouping to place the parent order and child TP/SL in a single action
    orders = [
        {
            "coin": "ETH",
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": px,
            "order_type": {"limit": {"tif": "Gtc"}},
            "reduce_only": False,
        },
        {
            "coin": "ETH",
            "is_buy": not is_buy,
            "sz": sz,
            "limit_px": px,
            "order_type": {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": px,
                    "tpsl": "tp",
                }
            },
            "reduce_only": True,
        },
        {
            "coin": coin,
            "is_buy": not is_buy,
            "sz": sz,
            "limit_px": sl_px,
            "order_type": {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": trigger_px,
                    "tpsl": "sl",
                }
            },
            "reduce_only": True,
        },
    ]

    resp = exchange.bulk_orders(orders, grouping="normalTpsl")
    print(resp)


if __name__ == "__main__":
    main()
