import argparse

import example_utils

from hyperliquid.utils import constants


def main():
    parser = argparse.ArgumentParser(description="basic_tpsl")
    parser.add_argument("--is_buy", action="store_true")
    args = parser.parse_args()

    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    coin = "SOL"
    position_is_long = args.is_buy
    quantity = 1
    px = 184.80
    tpsl_percent = 0.05  # 5%

    tp = px * (1 + (tpsl_percent * (1 if position_is_long else -1)))
    sl = px * (1 - (tpsl_percent * (1 if position_is_long else -1)))

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

    resp = exchange.bulk_orders(orders, grouping="normalTpsl")
    print(resp)


if __name__ == "__main__":
    main()
