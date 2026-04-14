import example_utils

from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True, perp_dexs=["test"])

    # Place a bid on gossip priority slot 0
    bid_result = exchange.gossip_priority_bid(0, "8.8.8.8", 1)
    print(bid_result)

    # Place an order with priority fee that should be rejected by setting the price very low
    order = {
        "coin": "test:ABC",
        "is_buy": True,
        "sz": 100,
        "limit_px": 0.9,
        "order_type": {"limit": {"tif": "Ioc"}},
        "reduce_only": False,
    }
    order_result = exchange.bulk_orders([order], grouping={"p": 12345})
    print(order_result)


if __name__ == "__main__":
    main()
