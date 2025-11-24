import json

import example_utils
# Import constants from the hyperliquid library
from hyperliquid.utils import constants

# Define constants for clarity
PURR_COIN = "PURR/USDC"
# Example of using a coin index (e.g., '@8') for spot assets on testnet
OTHER_COIN_INDEX = "@8" 
OTHER_COIN_NAME = "KORILA/USDC" # The name corresponding to the index for demonstration


def main():
    # Setup utility to get addresses, info, and exchange client
    # skip_ws=True means WebSocket connection is not initialized
    address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True)

    print(f"Executing orders from address: {address}")
    
    # --- 1. Query Spot User State ---
    
    # Get the user's current spot balances
    spot_user_state = info.spot_user_state(address)
    if spot_user_state.get("balances"):
        print("\n--- Spot Balances ---")
        for balance in spot_user_state["balances"]:
            print(json.dumps(balance, indent=2))
    else:
        print("\nNo available token balances.")

    # --- 2. Place, Query, and Cancel a PURR/USDC Limit Order ---
    
    print(f"\n--- Placing Order for {PURR_COIN} ---")
    # Place a limit order (long side) with a low price (0.5) to ensure it rests (GTC: Good Till Cancelled)
    order_result = exchange.order(PURR_COIN, True, 24, 0.5, {"limit": {"tif": "Gtc"}})
    print("Order Result:", order_result)

    if order_result["status"] == "ok":
        # Extract the primary status object once for cleaner code
        statuses = order_result["response"]["data"]["statuses"]
        if not statuses:
            print("Warning: Order statuses array is empty.")
            return

        order_status = statuses[0]
        
        if "resting" in order_status:
            oid = order_status["resting"]["oid"]
            print(f"Order resting with OID: {oid}")

            # Query the order status by oid
            queried_status = info.query_order_by_oid(address, oid)
            print("Order status by oid:", queried_status)

            # Cancel the order using the extracted OID
            cancel_result = exchange.cancel(PURR_COIN, oid)
            print("Cancel Result:", cancel_result)
        else:
            print("Order did not rest (e.g., immediately filled or failed).")
            print(json.dumps(order_status, indent=2))
    else:
        print("Order placement failed.")


    # --- 3. Example using Coin Index (@{index}) and Name for another asset ---

    print(f"\n--- Placing Order for Index {OTHER_COIN_INDEX} ({OTHER_COIN_NAME}) ---")
    # Place an order using the coin index (@8)
    order_result_other = exchange.order(OTHER_COIN_INDEX, True, 1, 12, {"limit": {"tif": "Gtc"}})
    print("Order Result (Index):", order_result_other)
    
    if order_result_other["status"] == "ok":
        statuses = order_result_other["response"]["data"]["statuses"]
        if statuses and "resting" in statuses[0]:
            oid = statuses[0]["resting"]["oid"]
            
            # The SDK supports canceling using the coin NAME (KORILA/USDC) or the INDEX (@8).
            cancel_result_other = exchange.cancel(OTHER_COIN_NAME, oid) 
            print("Cancel Result (Name):", cancel_result_other)
        else:
            print("Order placement failed or did not rest for index asset.")


if __name__ == "__main__":
    main()
