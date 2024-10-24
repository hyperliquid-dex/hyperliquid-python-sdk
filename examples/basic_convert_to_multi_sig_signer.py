from hyperliquid.utils import constants
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to convert to multi-sig signer")

    # the user owning this signer (either the user itself or agent's user) should already be registered as authorized user for the multi-sig user
    signer = "0x0000000000000000000000000000000000000000"
    multi_sig_user = "0x0000000000000000000000000000000000000001"
    convert_result = exchange.convert_to_multi_sig_signer(signer, multi_sig_user)
    print(convert_result)


if __name__ == "__main__":
    main()
