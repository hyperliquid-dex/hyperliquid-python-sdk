# Example script to for deploying a perp dex
#
# IMPORTANT: Replace any arguments for the exchange calls below to match your deployment requirements.

import example_utils

from hyperliquid.utils import constants

# Set to True to register a new perp dex.
REGISTER_PERP_DEX = False

DUMMY_DEX = "test"


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Step 1: Registering a Perp Dex and Assets
    #
    # Takes part in the perp deploy auction and if successful, registers asset "TEST0".
    # The max gas is $1M USDC and represents the max amount to be paid for the perp deploy auction.
    # Registering an asset can be done multiple times.
    perp_dex_schema_input = None
    if REGISTER_PERP_DEX:
        perp_dex_schema_input = {
            "fullName": "test dex",
            "collateralToken": 0,
            "oracleUpdater": address,
        }
    register_asset_result = exchange.perp_deploy_register_asset(
        dex=DUMMY_DEX,
        max_gas=1000000000000,
        coin="TEST0",
        sz_decimals=2,
        oracle_px="10.0",
        margin_table_id=10,
        only_isolated=False,
        schema=perp_dex_schema_input,
    )
    print("register asset result:", register_asset_result)
    # If registration is successful, the "dex" that was used can serve as the index into this clearinghouse for later asset
    # registrations and oracle updates.

    # Step 2: Set the Oracle Prices
    #
    # Oracle updates can be sent multiple times
    set_oracle_result = exchange.perp_deploy_set_oracle(
        DUMMY_DEX,
        {
            "TEST0": "12.0",
            "TEST1": "1.0",
        },
        {
            "TEST1": "3.0",
            "TEST0": "14.0",
        },
    )
    print("set oracle result:", set_oracle_result)

    # get DUMMY_DEX meta
    print("dummy dex meta:", info.meta(dex=DUMMY_DEX))


if __name__ == "__main__":
    main()
