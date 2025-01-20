"""
This example demonstrates how to round numbers when placing orders.
Both Price (px) and Size (sz) have a maximum number of decimals that are accepted.
Prices can have up to 5 significant figures, but no more than MAX_DECIMALS - szDecimals decimal places where MAX_DECIMALS is 6 for perps and 8 for spot.
For example, for perps, 1234.5 is valid but 1234.56 is not (too many significant figures).
0.001234 is valid, but 0.0012345 is not (more than 6 decimal places).
For spot, 0.0001234 is valid if szDecimals is 0 or 1, but not if szDecimals is greater than 2 (more than 8-2 decimal places).
Integer prices are always allowed, regardless of the number of significant figures. E.g. 123456.0 is a valid price even though 12345.6 is not.
Prices are precise to the lesser of 5 significant figures or 6 decimals.
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
    max_decimals = 6  # change to 8 for spot

    # If you use these directly, the exchange will return an error, so we round them.
    # First we check if price is greater than 100k in which case we just need to round to an integer
    if px > 100_000:
        px = round(px)
    # If not we round px to 5 significant figures and max_decimals - szDecimals decimals
    else:
        px = round(float(f"{px:.5g}"), max_decimals - sz_decimals[coin])

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
