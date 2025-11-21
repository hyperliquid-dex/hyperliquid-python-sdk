import example_utils

from hyperliquid.utils import constants

DUMMY_DEX = "test"
COLLATERAL_TOKEN = "USDC"  # nosec


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Transfer 1.23 USDC from spot wallet to perp wallet
    transfer_result = exchange.send_asset(address, "spot", DUMMY_DEX, COLLATERAL_TOKEN, 1.23)
    print(transfer_result)

    # Transfer 1.23 collateral token from perp wallet back to spot wallet
    transfer_result = exchange.send_asset(address, DUMMY_DEX, "spot", COLLATERAL_TOKEN, 1.23)
    print(transfer_result)


if __name__ == "__main__":
    main()
