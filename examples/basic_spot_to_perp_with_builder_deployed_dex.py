import example_utils

from hyperliquid.utils import constants

DUMMY_DEX = "test"
COLLATERAL_TOKEN = "USDC"  # nosec


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Transfer 1.23 USDC from perp wallet to spot wallet
    transfer_result = exchange.perp_dex_class_transfer(DUMMY_DEX, COLLATERAL_TOKEN, 1.23, False)
    print(transfer_result)

    # Transfer 1.23 collateral token from spot wallet to perp wallet
    transfer_result = exchange.perp_dex_class_transfer(DUMMY_DEX, COLLATERAL_TOKEN, 1.23, True)
    print(transfer_result)


if __name__ == "__main__":
    main()
