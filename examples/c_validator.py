# Example script to register a validator
# See https://github.com/hyperliquid-dex/node?tab=readme-ov-file#join-network for spec
#
# IMPORTANT: Replace any arguments for the exchange calls below to match your deployment requirements.

import example_utils

from hyperliquid.utils import constants

# Change to one of "Register", "ChangeProfile", or "Unregister"
ACTION = ""
DUMMY_SIGNER = "0x0000000000000000000000000000000000000001"


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    if ACTION == "Register":
        node_ip = "1.2.3.4"
        name = "..."
        description = "..."
        delegations_disabled = True
        commission_bps = 5
        signer = DUMMY_SIGNER
        unjailed = False
        initial_wei = 100000
        register_result = exchange.c_validator_register(
            node_ip,
            name,
            description,
            delegations_disabled,
            commission_bps,
            signer,
            unjailed,
            initial_wei,
        )
        print("register result", register_result)
    elif ACTION == "ChangeProfile":
        node_ip = None
        name = None
        description = None
        unjailed = False
        disable_delegations = None
        commission_bps = None
        signer = None
        change_profile_result = exchange.c_validator_change_profile(
            node_ip,
            name,
            description,
            unjailed,
            disable_delegations,
            commission_bps,
            signer,
        )
        print("change profile result", change_profile_result)
    elif ACTION == "Unregister":
        unregister_result = exchange.c_validator_unregister()
        print("unregister result", unregister_result)
    else:
        raise ValueError("Invalid action specified")


if __name__ == "__main__":
    main()
