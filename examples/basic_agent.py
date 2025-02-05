import eth_account
import example_utils
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants


def main():
    """
    Sets up an environment for testing purposes by creating an agent that can place trades on behalf of the account.
    The agent does not have permission to transfer or withdraw funds. You can run this part on a separate machine or 
    change the code to connect the agent via a wallet app instead of using your private key directly in Python. 
    You can also create a named agent using the frontend, which persists the authorization under an agent name.
    
    The main function then proceeds to place a test order with the agent and simulates the process of managing orders
    and ensuring that orders that are no longer needed are cleaned up.
    Finally, it creates an extra agent that persists beyond the current session and places an order with the extra agent.
    """

    # Set up the environment (exchange, account info, etc.) for testing purposes.
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Ensure that the wallet address and agent address are not the same
    # This prevents the risk of accidentally creating an agent using the wallet itself.
    if exchange.account_address != exchange.wallet.address:
        raise Exception("You should not create an agent using an agent")

 
    approve_result, agent_key = exchange.approve_agent()

    # Check if the agent approval was successful. If not, log the error and return.
    # This prevents proceeding with an agent that isn't properly authorized.
    if approve_result["status"] != "ok":
        print("approving agent failed", approve_result)
        return
    
    # Create the agent's local account using the agent's private key.
    # We use `eth_account.Account.from_key()` to securely generate the agent's account from its private key.
    agent_account: LocalAccount = eth_account.Account.from_key(agent_key)
    print("Running with agent address:", agent_account.address)

    # Create a new exchange instance for the agent, providing it with the agent's account information and exchange URL.
    # This exchange object will be used for placing orders and interacting with the Hyperliquid API.
    agent_exchange = Exchange(agent_account, constants.TESTNET_API_URL, account_address=address)

    # Place a test order with the agent (setting a very low price so that it rests in the order book).
    # The order is placed as a "limit" order with the time-in-force set to "Good till Cancelled" (GTC).
    # This allows us to test placing an order without immediately executing it.
    order_result = agent_exchange.order("ETH", True, 0.2, 1000, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # If the order was placed successfully and the status is "resting," we attempt to cancel it.
    # This simulates the process of managing orders and ensuring that orders are no longer needed are cleaned up.
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            cancel_result = agent_exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)

    # Create an extra agent that persists beyond the current session.
    # The "persist" argument ensures that the agent remains available for future interactions and doesn't require re-approval each time.    

    approve_result, extra_agent_key = exchange.approve_agent("persist")
    
    # Check if the extra agent was successfully approved.
    if approve_result["status"] != "ok":
        print("approving extra agent failed", approve_result)
        return

    # Create the extra agent account using its private key and the same process as above.
    extra_agent_account: LocalAccount = eth_account.Account.from_key(extra_agent_key)
    extra_agent_exchange = Exchange(extra_agent_account, constants.TESTNET_API_URL, account_address=address)
    print("Running with extra agent address:", extra_agent_account.address)

    # Place an order with the extra agent using the same process as the original agent.
    print("Placing order with original agent")
    order_result = agent_exchange.order("ETH", True, 0.2, 1000, {"limit": {"tif": "Gtc"}})
    print(order_result)

    # If the extra agent's order is placed successfully, attempt to cancel it.
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            print("Canceling order with extra agent")
            cancel_result = extra_agent_exchange.cancel("ETH", status["resting"]["oid"])
            print(cancel_result)


if __name__ == "__main__":
    main()
