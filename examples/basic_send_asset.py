import example_utils

from hyperliquid.utils import constants

SOURCE_DEX = ""
DESTINATION_DEX = "test"


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to perform internal transfers")

    # Transfer 1.23 USDC from SOURCE_DEX to the zero address on DESTINATION_DEX for demonstration purposes
    # Note that the collateral token for SOURCE_DEX and DESTINATION_DEX must match
    transfer_result = exchange.send_asset(
        "0x0000000000000000000000000000000000000000", SOURCE_DEX, DESTINATION_DEX, "USDC", 1.23
    )
    print(transfer_result)


if __name__ == "__main__":
    main()
