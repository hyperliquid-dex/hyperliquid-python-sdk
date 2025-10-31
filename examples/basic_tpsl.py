import argparse

import example_utils

from hyperliquid.utils import constants
from hyperliquid.utils.signing import OrderRequest


def main():
    parser = argparse.ArgumentParser(description="basic_tpsl")
    parser.add_argument("--is_buy", action="store_true")
    args = parser.parse_args()

    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    coin = "SOL"
    position_is_long = args.is_buy
    quantity = 1
    px = 184.80
    tp = px * 1.05  # take profit at +5%
    sl = px * 0.95  # stop loss at -5%

    orders = [
        {
            "coin": coin,
            "is_buy": position_is_long,
            "sz": quantity,
            "limit_px": px,
            # "order_type": {"limit": {"tif": "Gtc"}},
            "order_type": {"limit": {"tif": "Ioc"}},
            "reduce_only": False,
        },
        {
            "coin": coin,
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
            "coin": coin,
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

    try:
        resp = exchange.bulk_orders(orders, grouping="normalTpsl")
        print(resp)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()
