import time

import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange_plus import ExchangePlus
from hyperliquid.utils import constants

def main():

    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)

    exchange = ExchangePlus(account, constants.TESTNET_API_URL)

    coin = "ETH"
    is_buy = True
    sz = 0.05

    print(f"We try to Market {'Buy' if is_buy else 'Sell'} {sz} {coin}.")

    order_result = exchange.market_open("ETH", is_buy, 0.05)
    if order_result["status"] == "ok":
        for status in order_result["response"]["data"]["statuses"]:
            filled = status["filled"]
            print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')
        
        print("We wait for 2s before closing")
        time.sleep(2)

        print(f"We try to Market Close all {coin}.")
        order_result = exchange.market_close(coin)
        if order_result["status"] == "ok":
            for status in order_result["response"]["data"]["statuses"]:
                filled = status["filled"]
                print(f'Order #{filled["oid"]} filled {filled["totalSz"]} @{filled["avgPx"]}')

if __name__ == "__main__":
    main()
