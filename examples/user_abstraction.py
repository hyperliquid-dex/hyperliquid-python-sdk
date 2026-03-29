import example_utils

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

# set sub-account user address here
SUB_ACCOUNT_USER = "0x0000000000000000000000000000000000000000"


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # set abstraction for user via agent
    # Note: the account must be in "default" mode to succeed
    user = exchange.account_address
    print("current user abstraction state:", info.query_user_abstraction_state(user))
    agent_set_abstraction_result = exchange.agent_set_abstraction("u")
    print(agent_set_abstraction_result)

    if user == exchange.wallet.address:
        # set abstraction for user back to disabled
        user_set_abstraction_result = exchange.user_set_abstraction(user, "unifiedAccount")
        print(user_set_abstraction_result)
        print("current user abstraction state:", info.query_user_abstraction_state(user))

        # set dex abstraction for sub-account of user
        print("setting abstraction for", SUB_ACCOUNT_USER)

        # set abstraction for user via agent by setting the vault_address to SUB_ACCOUNT_USER
        exchange_with_sub_account = Exchange(exchange.wallet, exchange.base_url, vault_address=SUB_ACCOUNT_USER)
        agent_set_abstraction_result = exchange_with_sub_account.agent_set_abstraction("u")
        print("sub-account agent_set_abstraction result:", agent_set_abstraction_result)

        for abstraction in ["disabled", "portfolioMargin"]:
            user_set_abstraction_result = exchange.user_set_abstraction(SUB_ACCOUNT_USER, abstraction)
            print(user_set_abstraction_result)
            print(
                "current sub-account user abstraction state:",
                info.query_user_abstraction_state(SUB_ACCOUNT_USER),
            )

    else:
        print("not performing user set abstraction because not user", exchange.account_address, exchange.wallet.address)


if __name__ == "__main__":
    main()
