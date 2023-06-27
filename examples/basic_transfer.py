import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)

    # Transfer 1 usd to the zero address for demonstration purposes
    exchange = Exchange(account, constants.TESTNET_API_URL)
    transfer_result = exchange.usd_tranfer(1, "0x0000000000000000000000000000000000000000")
    print(transfer_result)


if __name__ == "__main__":
    main()
