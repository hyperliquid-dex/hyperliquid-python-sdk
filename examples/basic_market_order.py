import time
import logging
import sys

import example_utils
from hyperliquid.utils import constants

# Set up basic logging configuration
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def handle_order_result(order_result, operation_name):
    """
    Handles the common API response structure for market operations.
    """
    if order_result.get("status") == "ok":
        statuses = order_result["response"]["data"]["statuses"]
        success_count = 0
        
        for status in statuses:
            if "filled" in status:
                filled = status["filled"]
                logger.info(f'{operation_name} successful: Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
                success_count += 1
            elif "error" in status:
                logger.error(f'{operation_name} failed: {status["error"]}')
            else:
                logger.warning(f'{operation_name} returned unexpected status: {status}')
        
        if success_count == 0 and len(statuses) > 0:
            # If the status was 'ok' but no fills occurred and no explicit error was given, 
            # the order might have been cancelled due to max_slippage, or the market was too thin.
            logger.warning(f'{operation_name} completed, but no fills were reported.')

        return success_count > 0
    else:
        logger.error(f'API Call for {operation_name} failed. Status: {order_result.get("status", "unknown")}')
        # Log the full response if possible for debugging
        logger.debug(f'Full response: {order_result}')
        return False


def main():
    # Setup client, address, and exchange object
    address, _, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    logger.info(f"Wallet address: {address}")

    coin = "ETH"
    is_buy = False # Set to False for a Market Sell
    size = 0.05
    
    # max_slippage: max slippage percentage (e.g., 0.01 = 1% slippage allowed)
    # The fifth argument (limit_px) is None for a market order.
    max_slippage_percentage = 0.01 

    logger.info(f"Attempting to Market {'Buy' if is_buy else 'Sell'} {size} {coin}.")
    
    # 

    order_result = exchange.market_open(
        coin=coin, 
        is_buy=is_buy, 
        sz=size, 
        limit_px=None, 
        max_slippage=max_slippage_percentage
    )
    
    # Handle the outcome of the market open order
    if handle_order_result(order_result, "Market Open"):
        # Wait a short period before closing the position
        wait_time = 2 
        logger.info(f"Position opened successfully. Waiting for {wait_time}s before closing...")
        time.sleep(wait_time)

        # --- Close Position ---
        logger.info(f"Attempting to Market Close all positions for {coin}.")
        
        # market_close is designed to liquidate the entire open position for the specified coin.
        order_result = exchange.market_close(coin)
        handle_order_result(order_result, "Market Close")
    else:
        logger.error("Market open failed. Skipping position close.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"A critical error occurred in main execution: {e}", exc_info=True)
