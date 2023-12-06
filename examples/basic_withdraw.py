import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)

    # Withdraw 1 usd
    exchange = Exchange(account, constants.TESTNET_API_URL)
    withdraw_result = exchange.withdraw_from_bridge(1, account.address)
    print(withdraw_result)


if __name__ == "__main__":
    main()
