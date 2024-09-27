from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Change this address to a vault that you lead or a subaccount that you own
    vault = "0x1719884eb866cb12b2287399b15f7db5e7d775ea"

    # Place an order that should rest by setting the price very low
    exchange = Exchange(exchange.wallet, exchange.base_url, vault_address=vault)
    order_result = exchange.order("ETH", True, 0.2, 1100, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
