from hyperliquid.utils import constants
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if exchange.account_address != exchange.wallet.address:
        raise Exception("Agents do not have permission to perform internal transfers")

    # Transfer 5 usd to the HLP Vault for demonstration purposes
    transfer_result = exchange.vault_usd_transfer("0xa15099a30bbf2e68942d6f4c43d70d04faeab0a0", True, 5000000)
    print(transfer_result)


if __name__ == "__main__":
    main()
