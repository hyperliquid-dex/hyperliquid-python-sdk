import example_utils

from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to perform internal transfers")

    # Transfer 1 PURR token to the zero address for demonstration purposes
    transfer_result = exchange.spot_transfer(
        1, "0x0000000000000000000000000000000000000000", "PURR:0xc4bf3f870c0e9465323c0b6ed28096c2"
    )
    print(transfer_result)


if __name__ == "__main__":
    main()
