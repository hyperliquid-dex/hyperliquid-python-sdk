import argparse
import json

import example_utils

from hyperliquid.utils import constants


def round_to_wireable_price(px):
    return float(f"{px:.5g}")


def resting_oids(order_result):
    if order_result["status"] != "ok":
        return []
    return [
        status["resting"]["oid"]
        for status in order_result["response"]["data"]["statuses"]
        if "resting" in status
    ]


def main():
    parser = argparse.ArgumentParser(description="basic_grouped_tpsl")
    parser.add_argument("--coin", default="ETH")
    parser.add_argument("--is_buy", action="store_true")
    parser.add_argument("--sz", type=float, default=0.02)
    parser.add_argument("--keep-open", action="store_true")
    args = parser.parse_args()

    _, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    coin = args.coin
    is_buy = args.is_buy
    sz = args.sz
    mid = float(info.all_mids()[coin])

    if is_buy:
        entry_px = round_to_wireable_price(mid * 0.95)
        tp_trigger_px = round_to_wireable_price(mid * 1.05)
        tp_limit_px = round_to_wireable_price(tp_trigger_px * 0.99)
        sl_trigger_px = round_to_wireable_price(mid * 0.90)
        sl_limit_px = round_to_wireable_price(sl_trigger_px * 0.99)
    else:
        entry_px = round_to_wireable_price(mid * 1.05)
        tp_trigger_px = round_to_wireable_price(mid * 0.95)
        tp_limit_px = round_to_wireable_price(tp_trigger_px * 1.01)
        sl_trigger_px = round_to_wireable_price(mid * 1.10)
        sl_limit_px = round_to_wireable_price(sl_trigger_px * 1.01)

    close_is_buy = not is_buy
    orders = [
        {
            "coin": coin,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": entry_px,
            "order_type": {"limit": {"tif": "Gtc"}},
            "reduce_only": False,
        },
        {
            "coin": coin,
            "is_buy": close_is_buy,
            "sz": sz,
            "limit_px": tp_limit_px,
            "order_type": {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": tp_trigger_px,
                    "tpsl": "tp",
                }
            },
            "reduce_only": True,
        },
        {
            "coin": coin,
            "is_buy": close_is_buy,
            "sz": sz,
            "limit_px": sl_limit_px,
            "order_type": {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": sl_trigger_px,
                    "tpsl": "sl",
                }
            },
            "reduce_only": True,
        },
    ]

    print("submitting grouped TP/SL orders:")
    print(json.dumps(orders, indent=2))
    order_result = exchange.bulk_orders(orders, grouping="normalTpsl")
    print(order_result)

    if not args.keep_open:
        for oid in resting_oids(order_result):
            cancel_result = exchange.cancel(coin, oid)
            print("cancel result:", cancel_result)


if __name__ == "__main__":
    main()
