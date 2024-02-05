import json

from hyperliquid.utils import constants
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Get the user state and print out leverage information for ETH
    user_state = info.user_state(address)
    for asset_position in user_state["assetPositions"]:
        if asset_position["position"]["coin"] == "ETH":
            print("Current leverage for ETH:", json.dumps(asset_position["position"]["leverage"], indent=2))

    # Set the ETH leverage to 21x (cross margin)
    print(exchange.update_leverage(21, "ETH"))

    # Set the ETH leverage to 22x (isolated margin)
    print(exchange.update_leverage(21, "ETH", False))

    # Add 1 dollar of extra margin to the ETH position
    print(exchange.update_isolated_margin(1, "ETH"))

    # Get the user state and print out the final leverage information after our changes
    user_state = info.user_state(address)
    for asset_position in user_state["assetPositions"]:
        if asset_position["position"]["coin"] == "ETH":
            print("Current leverage for ETH:", json.dumps(asset_position["position"]["leverage"], indent=2))


if __name__ == "__main__":
    main()
