import json

import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants


def main():
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)
    info = Info(constants.TESTNET_API_URL, skip_ws=True)
    exchange = Exchange(account, constants.TESTNET_API_URL)

    # Get the user state and print out leverage information for ETH
    user_state = info.user_state(account.address)
    print("Current leverage for ETH:")
    print(json.dumps(user_state["assetPositions"][exchange.coin_to_asset["ETH"]]["position"]["leverage"], indent=2))

    # Set the ETH leverage to 21x (cross margin)
    print(exchange.update_leverage(21, "ETH"))

    # Set the ETH leverage to 22x (isolated margin)
    print(exchange.update_leverage(21, "ETH", False))

    # Add 1 dollar of extra margin to the ETH position
    print(exchange.update_isolated_margin(1, "ETH"))

    # Get the user state and print out the final leverage information after our changes
    user_state = info.user_state(account.address)
    print("Current leverage for ETH:")
    print(json.dumps(user_state["assetPositions"][exchange.coin_to_asset["ETH"]]["position"]["leverage"], indent=2))


if __name__ == "__main__":
    main()
