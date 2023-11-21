import eth_account
import utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    config = utils.get_config()
    account: LocalAccount = eth_account.Account.from_key(config["secret_key"])
    print("Running with account address:", account.address)
    exchange = Exchange(account, constants.TESTNET_API_URL)

    # Create an agent that can place trades on behalf of the account. The agent does not have permission to transfer
    # or withdraw funds.
    # You can run this part on a separate machine or change the code to connect the agent via a wallet app instead of
    # using your private key directly in python
    approve_result, agent_key = exchange.approve_agent()
    if approve_result["status"] != "ok":
        print("approving agent failed", approve_result)
        return

    # Place an order that should rest by setting the price very low
    agent_account: LocalAccount = eth_account.Account.from_key(agent_key)
    print("Running with agent address:", agent_account.address)
    exchange = Exchange(agent_account, constants.TESTNET_API_URL)
    order_result = exchange.order("ETH", True, 0.2, 1000, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)

    # Create an extra named agent
    exchange = Exchange(account, constants.TESTNET_API_URL)
    approve_result, extra_agent_key = exchange.approve_agent("persist")
    if approve_result["status"] != "ok":
        print("approving extra agent failed", approve_result)
        return

    extra_agent_account: LocalAccount = eth_account.Account.from_key(extra_agent_key)
    print("Running with extra agent address:", extra_agent_account.address)

    print("Placing order with original agent")
    order_result = exchange.order("ETH", True, 0.2, 1000, {"limit": {"tif": "Gtc"}})
    print(order_result)

    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            print("Canceling order with extra agent")
            exchange = Exchange(extra_agent_account, constants.TESTNET_API_URL)
            cancel_result = exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
