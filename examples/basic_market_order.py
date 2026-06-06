import time
from typing import Dict, Any, List

# Assuming these are available locally or installed
import example_utils
from hyperliquid.utils import constants

# --- HELPER FUNCTIONS ---

def process_order_statuses(order_result: Dict[str, Any], action: str):
    """
    Processes and prints the status of an exchange order operation (open/close).
    This function adheres to the DRY principle by consolidating repeated logic.
    
    Args:
        order_result: The raw dictionary response from the exchange API call.
        action: A string describing the action for printing purposes (e.g., "Open", "Close").
    """
    if order_result["status"] != "ok":
        print(f"FATAL ERROR during {action} operation: API status was not 'ok'.")
        # Print the full response for debugging
        print(order_result)
        return

    # Check for errors in the individual order statuses
    statuses: List[Dict[str, Any]] = order_result["response"]["data"]["statuses"]
    
    for status in statuses:
        try:
            # Successfully filled order
            filled = status["filled"]
            print(f'Order #{filled["oid"]} {action} filled {filled["totalSz"]} @ {filled["avgPx"]}')
        except KeyError:
            # Handle status containing an explicit error key
            if "error" in status:
                print(f'Error during {action} operation: {status["error"]}')
            else:
                # Catch unexpected status format
                print(f"Error: Unknown status format received for {action} operation.")
                print(status)
        except Exception as e:
            # Catch other potential parsing errors
            print(f"Critical Parsing Exception during {action}: {e}")
            print(status)


# --- MAIN LOGIC ---

def main():
    # Setup the exchange connection, ignoring unused 'address' and 'info'
    _, _, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Configuration Parameters
    COIN = "ETH"
    IS_BUY = False  # False means Market Sell
    SIZE = 0.05
    # For market orders, limit_px should typically be None. 
    # SLIPPAGE: Maximum price deviation (e.g., 0.5% slippage tolerance).
    # NOTE: The Hyperliquid SDK often uses the 'limit_px' parameter positionally. 
    # Check documentation to ensure the final parameter is indeed the slippage tolerance.
    MAX_SLIPPAGE = 0.01 

    print(f"Attempting to Market {'Buy' if IS_BUY else 'Sell'} {SIZE} {COIN}.")
    
    # Open the position
    try:
        order_result = exchange.market_open(
            COIN, 
            IS_BUY, 
            SIZE, 
            None, # Limit price (None for market order)
            MAX_SLIPPAGE # Slippage tolerance or margin (needs verification)
        )
        process_order_statuses(order_result, "Open")

    except Exception as e:
        print(f"FATAL ERROR: Could not submit market open order: {e}")
        return

    # Delay before closing
    print("Waiting for 2 seconds before closing position...")
    time.sleep(2)

    # Close the position
    print(f"Attempting to Market Close all position for {COIN}.")
    try:
        close_result = exchange.market_close(COIN)
        process_order_statuses(close_result, "Close")
        
    except Exception as e:
        print(f"FATAL ERROR: Could not submit market close order: {e}")
        # In a real bot, log this failure and implement a retry/kill switch


if __name__ == "__main__":
    main()
