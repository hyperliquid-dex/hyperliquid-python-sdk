import example_utils

from hyperliquid.utils import constants


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    testnet_HLP_vault = "0xa15099a30bbf2e68942d6f4c43d70d04faeab0a0"

    # Transfer 5 usd to the HLP Vault for demonstration purposes
    transfer_result = exchange.vault_usd_transfer(testnet_HLP_vault, True, 5_000_000)
    print(transfer_result)


if __name__ == "__main__":
    main()
