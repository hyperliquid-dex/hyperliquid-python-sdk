from hyperliquid.utils import constants
import example_utils


# This example shows how to create, query, and transfer funds to a subaccount.
# To trade as a subaccount set vault_address to the subaccount's address. See basic_vault.py for an example.
def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    name = "example123"
    print(exchange.create_sub_account(name))

    sub_accounts = info.query_sub_accounts(address)
    for sub_account in sub_accounts:
        if sub_account["name"] == name:
            sub_account_user = sub_account["subAccountUser"]

    print(exchange.sub_account_transfer(sub_account_user, True, 10))


if __name__ == "__main__":
    main()
