from hyperliquid.utils import constants
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to convert to multi-sig user")

    # authorized users are the users for which one can themselves or agents use as signers
    # for multi-sig actions
    authorized_user_1 = "0x0000000000000000000000000000000000000000"
    authorized_user_2 = "0x0000000000000000000000000000000000000001"
    threshold = 1
    convert_result = exchange.convert_to_multi_sig_user([authorized_user_1, authorized_user_2], threshold)
    print(convert_result)


if __name__ == "__main__":
    main()
