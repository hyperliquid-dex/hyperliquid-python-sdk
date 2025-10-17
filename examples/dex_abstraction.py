# See https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint#enable-hip-3-dex-abstraction for more details
import example_utils

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

SUB_ACCOUNT_NAME = "One"


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # enable dex abstraction for user via agent
    agent_enable_dex_abstraction_result = exchange.agent_enable_dex_abstraction()
    print(agent_enable_dex_abstraction_result)

    user = exchange.account_address
    if user == exchange.wallet.address:
        # disable dex abstraction for user
        user_dex_abstraction_result = exchange.user_dex_abstraction(user, False)
        print(user_dex_abstraction_result)
        print("current user dex abstraction state:", info.query_user_dex_abstraction_state(user))

        # enable and disable dex abstraction for sub-account of user
        sub_accounts = info.query_sub_accounts(user)
        sub_account_user = None
        for sub_account in sub_accounts:
            if sub_account["name"] == SUB_ACCOUNT_NAME:
                sub_account_user = sub_account["subAccountUser"]
                print("found sub-account, enabling and disabling dex abstraction for", sub_account_user)

                # enable dex abstraction for user via agent by setting the vault_address to the sub_account_user
                exchange_with_sub_account = Exchange(exchange.wallet, exchange.base_url, vault_address=sub_account_user)
                agent_enable_dex_abstraction_result = exchange_with_sub_account.agent_enable_dex_abstraction()
                print("sub-account agent_enable_dex_abstraction result:", agent_enable_dex_abstraction_result)

                for enabled in [True, False]:
                    user_dex_abstraction_result = exchange.user_dex_abstraction(sub_account_user, enabled)
                    print(user_dex_abstraction_result)
                    print(
                        "current sub-account user dex abstraction state:",
                        info.query_user_dex_abstraction_state(sub_account_user),
                    )

                break

    else:
        print("not performing user dex abstraction because not user", exchange.account_address, exchange.wallet.address)


if __name__ == "__main__":
    main()
