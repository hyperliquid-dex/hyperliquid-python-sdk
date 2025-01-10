import eth_account
import example_utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("You should not create an agent using an agent")

    # Create an agent that can place trades on behalf of the account. The agent does not have permission to transfer
    # or withdraw funds.
    # You can run this part on a separate machine or change the code to connect the agent via a wallet app instead of
    # using your private key directly in python.
    # You can also create a named agent using the frontend, which persists the authorization under an agent name.
    approve_result, agent_key = exchange.approve_agent()
    if approve_result["status"] != "ok":
        print("approving agent failed", approve_result)
        return

    agent_account: LocalAccount = eth_account.Account.from_key(agent_key)
    print("Running with agent address:", agent_account.address)
    agent_exchange = Exchange(agent_account, constants.TESTNET_API_URL, account_address=address)
    # Place an order that should rest by setting the price very low
    order_result = agent_exchange.order("ETH", True, 0.2, 1000, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # Cancel the order
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = agent_exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)

    # Create an extra named agent
    approve_result, extra_agent_key = exchange.approve_agent("persist")
    if approve_result["status"] != "ok":
        print("approving extra agent failed", approve_result)
        return

    extra_agent_account: LocalAccount = eth_account.Account.from_key(extra_agent_key)
    extra_agent_exchange = Exchange(extra_agent_account, constants.TESTNET_API_URL, account_address=address)
    print("Running with extra agent address:", extra_agent_account.address)

    print("Placing order with original agent")
    order_result = agent_exchange.order("ETH", True, 0.2, 1000, {"limit": {"tif": "Gtc"}})
    print(order_result)

    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            print("Canceling order with extra agent")
            cancel_result = extra_agent_exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
