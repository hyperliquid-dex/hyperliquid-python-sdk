"""
This example demonstrates how to:
1. Create a new account for Hyperliquid testnet 
2. Set up the config.json file with the account details
3. Guide users through requesting Hyperliquid testnet USDC
4. Provide verification functionality to check balance

Note: Automatic fund requesting is not currently supported 
due to Hyperliquid testnet infrastructure limitations.
Users must request testnet USDC manually through the Hyperliquid 
testnet interface.
"""

import json
import time
from pathlib import Path

from eth_account import Account

from hyperliquid.info import Info
from hyperliquid.utils import constants


def create_new_account():
    """Create a new Ethereum account for testing."""
    Account.enable_unaudited_hdwallet_features()
    account = Account.create()
    return {"private_key": account.key.hex(), "address": account.address}


def setup_config(private_key, address):
    """Create or update config.json with the new account details."""
    config = {
        "comments": "Testnet account configuration",
        "secret_key": private_key,
        "account_address": address,
        "multi_sig": {
            "authorized_users": [
                {"comment": "signer 1", "secret_key": "", "account_address": ""},
                {"comment": "signer 2", "secret_key": "", "account_address": ""},
            ]
        },
    }

    config_path = Path(__file__).parent / "config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=4)
    print(f"\nConfig file created at: {config_path}")


def request_testnet_funds(address):
    """
    TODO: Automatic testnet fund requesting

    Currently, automatic fund requesting is not implemented because:
    1. The testnet infrastructure doesn't provide a direct API endpoint for automated funding
    2. Unlike local networks (e.g., Hardhat), we can't programmatically mint tokens
    3. Users need to manually request funds through the web interface

    For now, users should:
    1. Visit https://app.hyperliquid-testnet.xyz/drip
    2. Connect their wallet
    3. Request funds manually
    """
    message = """
Automatic fund requesting is not available.
Please visit: https://app.hyperliquid-testnet.xyz/drip
Connect your wallet and request funds manually.
"""
    print(message)
    return False


def check_balance(address):
    """Check the account balance on Hyperliquid testnet."""
    info = Info(constants.TESTNET_API_URL)
    try:
        user_state = info.user_state(address)
        if "error" in user_state:
            print("\nAccount has no balance on Hyperliquid testnet")
            return False

        balance = float(user_state["marginSummary"]["accountValue"])
        print(f"\nCurrent balance: {balance} USDC")
        return balance > 0
    except Exception as e:
        print(f"\nError checking balance: {e}")
        return False


def get_address_from_key(private_key):
    """Get Ethereum address from private key."""
    if private_key.startswith("0x"):
        private_key = private_key[2:]
    account = Account.from_key(bytes.fromhex(private_key))
    return account.address


def main():
    print("\nSetting up a new testnet account...")

    # Create new account
    account = create_new_account()
    account_info = f"""
New account created:
Address: {account['address']}
Private Key: {account['private_key']}
"""
    print(account_info)

    # Setup config.json
    setup_config(account["private_key"], account["address"])

    # Inform about manual funding process
    next_steps = """
Next steps
----------
1. Visit Hyperliquid testnet and connect your wallet:
   https://app.hyperliquid-testnet.xyz/drip
2. Request testnet funds manually
3. Run this script again with --verify flag once you have funds
"""
    print(next_steps)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        # Load existing config and verify
        config_path = Path(__file__).parent / "config.json"
        with open(config_path) as f:
            config = json.load(f)

        address = config["account_address"]
        if not address:
            address = get_address_from_key(config["secret_key"])

        print(f"Verifying account: {address}")
        if check_balance(address):
            print("\nSuccess! Account is ready for testing")
        else:
            print("\nAccount still needs to be funded")
            print("Attempting to request funds again...")
            if request_testnet_funds(address):
                time.sleep(10)
                if check_balance(address):
                    print("\nSuccess! Account is now funded and ready for testing")
    else:
        main()
