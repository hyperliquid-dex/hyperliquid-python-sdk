import argparse

import example_utils

from hyperliquid.utils import constants
from hyperliquid.utils.signing import OrderRequest


def main():
    parser = argparse.ArgumentParser(description="basic_tpsl")
    parser.add_argument("--is_buy", action="store_true")
    args = parser.parse_args()

    address, info, exchange = example_utils.setup(constants.MAINNET_API_URL, skip_ws=True)

    market = "SOL"
    position_is_long = args.is_buy
    quantity = 1
    px = 184.80
    tp = px * 1.05  # take profit at +4%
    sl = px * 0.95  # stop loss at -4%

    orders: list[OrderRequest] = [
        {
            "coin": market,
            "is_buy": position_is_long,
            "sz": quantity,
            "limit_px": px,
            # "order_type": {"limit": {"tif": "Gtc"}},
            "order_type": {"limit": {"tif": "Ioc"}},
            "reduce_only": False,
        },
        {
            "coin": market,
            "is_buy": not position_is_long,
            "sz": quantity,
            "limit_px": tp,
            "order_type": {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": tp,
                    "tpsl": "tp",
                }
            },
            "reduce_only": True,
        },
        {
            "coin": market,
            "is_buy": not position_is_long,
            "sz": quantity,
            "limit_px": sl,
            "order_type": {
                "trigger": {
                    "isMarket": True,
                    "triggerPx": sl,
                    "tpsl": "sl",
                }
            },
            "reduce_only": True,
        },
    ]
    resp = exchange.bulk_orders(orders, grouping="normalTpsl")

    if resp["status"] == "ok":
        for status in resp["response"]["data"]["statuses"]:
            try:
                filled = status["filled"]
                print(f"{position_is_long} Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}")
            except KeyError:
                print(f'Error: {status["error"]}')


if __name__ == "__main__":
    main()
