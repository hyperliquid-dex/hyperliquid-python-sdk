"""
This example demonstrates how to round numbers when placing orders.
Both Price (px) and Size (sz) have a maximum number of decimals that are accepted.
For non-integer prices, prices can have up to 5 significant figures, but no more than MAX_DECIMALS - szDecimals decimal places where MAX_DECIMALS is 6 for perps and 8 for spot.
For example, for perps, 1234.5 is valid but 1234.56 is not (too many significant figures).
0.001234 is valid, but 0.0012345 is not (more than 6 decimal places).
For spot, 0.0001234 is valid if szDecimals is 0 or 1, but not if szDecimals is greater than 2 (more than 8-2 decimal places).
Integer prices are always allowed, regardless of the number of significant figures. E.g. 123456 is a valid price.
Non-integer prices are precise to the lesser of 5 significant figures or 6 decimals.
You can find the szDecimals for an asset by making a meta request to the info endpoint
"""
import json

import example_utils

from hyperliquid.utils import constants


def demonstrate_price_rounding(px, coin, sz_decimals, max_decimals=6):
    """Helper function to demonstrate price rounding behavior."""
    original_px = px

    # Apply rounding logic
    if abs(round(px) - px) < 1e-10:
        px = round(px)
    else:
        px = round(float(f"{px:.5g}"), max_decimals - sz_decimals[coin])

    print(f"Original price: {original_px}")
    print(f"Rounded price: {px}")
    print("---")
    return px


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Get the exchange's metadata and print it out
    meta = info.meta()

    # create a szDecimals map
    sz_decimals = {}
    for asset_info in meta["universe"]:
        sz_decimals[asset_info["name"]] = asset_info["szDecimals"]

    coin = "BTC"
    sz = 0.001  # Small size for testing

    print("Testing price rounding behavior:")
    print("\nTest Case 1: Integer price with more than 5 significant figures (now allowed)")
    px1 = 123456  # 6 significant figures, integer
    rounded_px1 = demonstrate_price_rounding(px1, coin, sz_decimals)

    print("\nTest Case 2: Non-integer price with more than 5 significant figures (still not allowed)")
    px2 = 12345.6  # 6 significant figures, non-integer
    rounded_px2 = demonstrate_price_rounding(px2, coin, sz_decimals)

    print("\nTest Case 3: Regular integer price")
    px3 = 12345  # 5 significant figures, integer
    rounded_px3 = demonstrate_price_rounding(px3, coin, sz_decimals)

    # Place orders to verify the behavior
    print("\nPlacing orders to verify behavior:")

    # Place order with large integer price (new behavior allows this)
    print(f"\nPlacing order with large integer price: {rounded_px1}")
    order_result1 = exchange.order(coin, True, sz, rounded_px1, {"limit": {"tif": "Gtc"}})
    print(f"Order result: {order_result1['status']}")

    if order_result1["status"] == "ok":
        status = order_result1["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel(coin, status["resting"]["oid"])
            print(f"Cancel result: {cancel_result['status']}")


if __name__ == "__main__":
    main()
