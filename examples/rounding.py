"""
This example demonstrates how to round numbers when placing orders.
Both Price (px) and Size (sz) have a maximum number of decimals that are accepted.
Prices are precise to the lesser of 5 significant figures or 6 decimals.
For example, 1234.5 is valid but 1234.56 is not. 0.001234 is valid, but 0.0012345 is not.
Sizes are rounded to the szDecimals of that asset.
For example, if szDecimals = 3 then 1.001 is a valid size but 1.0001 is not.
You can find the szDecimals for an asset by making a meta request to the info endpoint
"""
import json

import example_utils

from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Get the exchange's metadata and print it out
    meta = info.meta()
    print(json.dumps(meta, indent=2))

    # create a szDecimals map
    sz_decimals = {}
    for asset_info in meta["universe"]:
        sz_decimals[asset_info["name"]] = asset_info["szDecimals"]

    # For demonstration purposes we'll start with a price and size that have too many digits
    sz = 12.345678
    px = 1.2345678
    coin = "OP"

    # If you use these directly, the exchange will return an error, so we round them.
    # First we round px to 5 significant figures and 6 decimals
    px = round(float(f"{px:.5g}"), 6)

    # Next we round sz based on the sz_decimals map we created
    sz = round(sz, sz_decimals[coin])

    print(f"placing order with px {px} and sz {sz}")
    order_result = exchange.order(coin, True, sz, px, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel(coin, status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
