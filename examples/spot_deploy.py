# deploy_hip_assets.py - Optimized script to deploy HIP-1 and HIP-2 assets
#
# This script orchestrates the full asset deployment workflow on Hyperliquid.
# IMPORTANT: All deployment arguments (amounts, addresses) must be verified 
# to match the final production requirements before execution.

import sys
import logging
from typing import List, Tuple

import example_utils
from hyperliquid.utils import constants

# --- Configuration Flags ---

# Enables the deployer to freeze/unfreeze users after genesis.
ENABLE_FREEZE_PRIVILEGE = False
# Enables setting a deployer trading fee share (default is 100%).
SET_DEPLOYER_TRADING_FEE_SHARE = False
# Enables the token to be used as a quote asset.
ENABLE_QUOTE_TOKEN = False

# Constants
DUMMY_USER = "0x0000000000000000000000000000000000000001"
# Hyperliquid's official address for hyperliquidity
HYPERLIQUIDITY_ADDRESS = "0xffffffffffffffffffffffffffffffffffffffff"
# Total supply for the genesis block (300 Trillion wei in the original example)
TOTAL_GENESIS_SUPPLY = "300_000_000_000_000" 

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Core Deployment Functions ---

def register_token_and_get_index(exchange) -> int | None:
    """Step 1: Registers the token and retrieves the token index."""
    logging.info("Step 1: Registering token 'TEST0'...")
    try:
        # sz_decimals=2, wei_decimals=8. Max gas for auction is 10,000 HYPE (10^12 wei).
        register_token_result = exchange.spot_deploy_register_token(
            "TEST0", 
            2, 
            8, 
            1_000_000_000_000, # Use underscores for better readability
            "Test token example"
        )
        
        # Check for 'ok' status, otherwise raise an exception.
        if register_token_result.get("status") != "ok":
             raise ValueError(f"Registration failed: {register_token_result.get('error')}")

        token_index = register_token_result["response"]["data"]
        logging.info(f"Token registration successful. Index: {token_index}")
        return token_index
    except Exception as e:
        logging.error(f"Failed to register token: {e}")
        return None


def execute_user_genesis(exchange, token_index: int):
    """Step 2: Associates initial balances with specific users and holders."""
    logging.info("Step 2: Executing user genesis...")
    
    # Balance allocations for specific addresses (address, amount_in_wei)
    initial_balances: List[Tuple[str, str]] = [
        (DUMMY_USER, "100_000_000_000_000"), 
        (HYPERLIQUIDITY_ADDRESS, "100_000_000_000_000"),
    ]
    
    # Weighted distribution to existing holders of another token (index 1)
    weighted_allocations: List[Tuple[int, str]] = [
        (1, "100_000_000_000_000")
    ]
    
    # OPTIMIZATION: Combine all non-empty genesis allocations into a single, clean call.
    try:
        user_genesis_result = exchange.spot_deploy_user_genesis(
            token_index,
            initial_balances,
            weighted_allocations,
        )
        if user_genesis_result.get("status") != "ok":
             raise ValueError(f"User genesis failed: {user_genesis_result.get('error')}")
             
        logging.info("User genesis executed successfully.")
    except Exception as e:
        logging.error(f"Failed during user genesis: {e}")
        raise # Re-raise to halt deployment if this step is crucial


def handle_freeze_privilege(exchange, token_index: int):
    """Step 2-a: Handles enabling and testing the freeze privilege."""
    if not ENABLE_FREEZE_PRIVILEGE:
        return
        
    logging.info("Step 2-a: Enabling and testing freeze privilege...")
    try:
        exchange.spot_deploy_enable_freeze_privilege(token_index)
        logging.info("Freeze privilege enabled.")
        
        # Freeze and Unfreeze the dummy user for testing the privilege
        exchange.spot_deploy_freeze_user(token_index, DUMMY_USER, True)
        logging.info(f"User {DUMMY_USER} frozen.")
        exchange.spot_deploy_freeze_user(token_index, DUMMY_USER, False)
        logging.info(f"User {DUMMY_USER} unfrozen.")
    except Exception as e:
        logging.error(f"Failed to handle freeze privilege: {e}")


def finalize_genesis(exchange, token_index: int):
    """Step 3: Finalizes the token genesis."""
    logging.info("Step 3: Finalizing genesis...")
    # 'noHyperliquidity=False' means Hyperliquidity is enabled and must have received an allocation in Step 2.
    try:
        genesis_result = exchange.spot_deploy_genesis(token_index, TOTAL_GENESIS_SUPPLY, False)
        if genesis_result.get("status") != "ok":
             raise ValueError(f"Genesis finalization failed: {genesis_result.get('error')}")
        logging.info("Genesis finalized successfully.")
    except Exception as e:
        logging.error(f"Failed to finalize genesis: {e}")
        raise


def register_spot_pair(exchange, token_index: int) -> int | None:
    """Step 4: Registers the spot trading pair (TEST0/USDC)."""
    logging.info("Step 4: Registering spot pair (Base/Quote)...")
    
    # 0 is the fixed index for USDC (Quote Token)
    QUOTE_TOKEN_INDEX = 0 
    
    try:
        register_spot_result = exchange.spot_deploy_register_spot(token_index, QUOTE_TOKEN_INDEX)
        
        if register_spot_result.get("status") != "ok":
             raise ValueError(f"Spot registration failed: {register_spot_result.get('error')}")

        spot_index = register_spot_result["response"]["data"]
        logging.info(f"Spot pair registration successful. Index: {spot_index}")
        return spot_index
    except Exception as e:
        logging.error(f"Failed to register spot pair: {e}")
        return None


def register_hyperliquidity(exchange, spot_index: int):
    """Step 5: Registers initial Hyperliquidity parameters."""
    logging.info("Step 5: Registering hyperliquidity...")
    
    # Example parameters: Starting price $2, order size 4 units, 100 total orders.
    START_PRICE = 2.0
    ORDER_SIZE = 4.0
    N_ORDERS = 100
    
    try:
        register_hyperliquidity_result = exchange.spot_deploy_register_hyperliquidity(
            spot_index, 
            START_PRICE, 
            ORDER_SIZE, 
            N_ORDERS, 
            None # Placeholder for optional third party address
        )
        if register_hyperliquidity_result.get("status") != "ok":
             raise ValueError(f"Hyperliquidity registration failed: {register_hyperliquidity_result.get('error')}")
        
        logging.info("Hyperliquidity registered successfully.")
    except Exception as e:
        logging.error(f"Failed to register hyperliquidity: {e}")
        raise


def handle_trading_fee_share(exchange, token_index: int):
    """Step 6: Optionally sets the deployer's trading fee share."""
    if not SET_DEPLOYER_TRADING_FEE_SHARE:
        return
        
    logging.info("Step 6: Setting deployer trading fee share...")
    try:
        # The default is 100%. Set to the desired percentage string (e.g., "50%").
        set_fee_share_result = exchange.spot_deploy_set_deployer_trading_fee_share(token_index, "100%")
        if set_fee_share_result.get("status") != "ok":
             raise ValueError(f"Fee share setting failed: {set_fee_share_result.get('error')}")
        logging.info("Deployer trading fee share set successfully.")
    except Exception as e:
        logging.error(f"Failed to set deployer trading fee share: {e}")


def handle_enable_quote_token(exchange, token_index: int):
    """Step 7: Optionally enables the token to be used as a quote asset."""
    if not ENABLE_QUOTE_TOKEN:
        return
        
    logging.info("Step 7: Enabling quote token capability...")
    # NOTE: Deployer trading fee share MUST be zero before this step.
    try:
        enable_quote_token_result = exchange.spot_deploy_enable_quote_token(token_index)
        if enable_quote_token_result.get("status") != "ok":
             raise ValueError(f"Enable quote token failed: {enable_quote_token_result.get('error')}")
        logging.info("Quote token capability enabled successfully.")
    except Exception as e:
        logging.error(f"Failed to enable quote token: {e}")


# --- Main Orchestration ---

def main():
    """Orchestrates the entire asset deployment workflow."""
    # Initialization and Connection
    try:
        address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
        logging.info(f"Deployer address set: {address}")
    except Exception as e:
        logging.critical(f"Setup failed: {e}")
        sys.exit(1)

    # 1. Register Token
    token_index = register_token_and_get_index(exchange)
    if token_index is None:
        sys.exit(1)

    # 2. User Genesis
    try:
        execute_user_genesis(exchange, token_index)
    except Exception:
        sys.exit(1)
        
    # 2-a. Freeze Privilege (Optional)
    handle_freeze_privilege(exchange, token_index)

    # 3. Finalize Genesis
    try:
        finalize_genesis(exchange, token_index)
    except Exception:
        sys.exit(1)

    # 4. Register Spot Pair
    spot_index = register_spot_pair(exchange, token_index)
    if spot_index is None:
        sys.exit(1)

    # 5. Register Hyperliquidity
    try:
        register_hyperliquidity(exchange, spot_index)
    except Exception:
        sys.exit(1)

    # 6. Set Trading Fee Share (Optional)
    handle_trading_fee_share(exchange, token_index)

    # 7. Enable Quote Token (Optional)
    handle_enable_quote_token(exchange, token_index)
    
    logging.info("Deployment workflow completed successfully.")


if __name__ == "__main__":
    main()
