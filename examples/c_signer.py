# Example script to run CSigner actions
# See https://github.com/hyperliquid-dex/node?tab=readme-ov-file#begin-validating for spec
#
# IMPORTANT: Replace any arguments for the exchange calls below to match your deployment requirements.

import example_utils

from hyperliquid.utils import constants

# Change to one of "Jail" or "Unjail"
ACTION = ""


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if ACTION == "Jail":
        jail_result = exchange.c_signer_jail_self()
        print("jail result", jail_result)
    elif ACTION == "Unjail":
        unjail_result = exchange.c_signer_unjail_self()
        print("unjail result", unjail_result)
    else:
        raise ValueError("Invalid action specified")


if __name__ == "__main__":
    main()
