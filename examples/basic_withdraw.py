import example_utils

from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to perform withdrawals")

    # Withdraw 2 usd (note the amount received will be reduced by the fee)
    withdraw_result = exchange.withdraw_from_bridge(2, address)
    print(withdraw_result)


if __name__ == "__main__":
    main()
