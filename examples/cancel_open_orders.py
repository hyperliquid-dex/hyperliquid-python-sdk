from eth_account.signers.local import LocalAccount
import eth_account
import utils

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)
    info = Info(constants.TESTNET_API_URL, skip_ws=True)
    exchange = Exchange(account, constants.TESTNET_API_URL)

    open_orders = info.open_orders(account.address)
    for open_order in open_orders:
        print(f"cancelling order {open_order}")
        exchange.cancel(open_order["coin"], open_order["oid"])


if __name__ == "__main__":
    main()
