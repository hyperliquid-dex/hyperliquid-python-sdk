import example_utils

from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Set the referrer code, for non-subaccount and non-vault addresses
    print(exchange.set_referrer("ASDFASDF"))

    referral_state = info.query_referral_state(address)
    if "referredBy" in referral_state:
        print("referred by", referral_state["referredBy"])


if __name__ == "__main__":
    main()
