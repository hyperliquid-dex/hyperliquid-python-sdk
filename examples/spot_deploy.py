# Example script to deploy HIP-1 and HIP-2 assets
# See https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/deploying-hip-1-and-hip-2-assets
# for the spec.
#
# IMPORTANT: Replace any arguments for the exchange calls below to match your deployment requirements.

import example_utils

from hyperliquid.utils import constants

# Set to True to enable freeze functionality for the deployed token
# See step 2-a below for more details on freezing.
ENABLE_FREEZE_PRIVILEGE = False
# Set to True to set the deployer trading fee share
# See step 6 below for more details on setting the deployer trading fee share.
SET_DEPLOYER_TRADING_FEE_SHARE = False
DUMMY_USER = "0x0000000000000000000000000000000000000001"


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Step 1: Registering the Token
    #
    # Takes part in the spot deploy auction and if successful, registers token "TEST0"
    # with sz_decimals 2 and wei_decimals 8.
    # The max gas is $1M USDC and represents the max amount to be paid for the spot deploy auction.
    register_token_result = exchange.spot_deploy_register_token("TEST0", 2, 8, 1000000000000, "Test token example")
    print(register_token_result)
    # If registration is successful, a token index will be returned. This token index is required for
    # later steps in the spot deploy process.
    if register_token_result["status"] == "ok":
        token = register_token_result["response"]["data"]
    else:
        return

    # Step 2: User Genesis
    #
    # User genesis can be called multiple times to associate balances to specific users and/or
    # tokens for genesis.
    #
    # Associate 100000000000000 wei with user 0x0000000000000000000000000000000000000001
    # Associate 100000000000000 wei with hyperliquidity
    user_genesis_result = exchange.spot_deploy_user_genesis(
        token,
        [
            (DUMMY_USER, "100000000000000"),
            ("0xffffffffffffffffffffffffffffffffffffffff", "100000000000000"),
        ],
        [],
    )
    print(user_genesis_result)
    # No-op
    user_genesis_result = exchange.spot_deploy_user_genesis(token, [], [])
    print(user_genesis_result)
    # Distribute 100000000000000 wei on a weighted basis to all holders of token with index 1
    user_genesis_result = exchange.spot_deploy_user_genesis(token, [], [(1, "100000000000000")])
    print(user_genesis_result)

    if ENABLE_FREEZE_PRIVILEGE:
        # Step 2-a: Enables the deployer to freeze/unfreeze users. Freezing a user means
        # that user cannot trade, send, or receive this token.
        enable_freeze_privilege_result = exchange.spot_deploy_enable_freeze_privilege(token)
        print(enable_freeze_privilege_result)

        # Freeze user for token
        freeze_user_result = exchange.spot_deploy_freeze_user(token, DUMMY_USER, True)
        print(freeze_user_result)

        # Unfreeze user for token
        unfreeze_user_result = exchange.spot_deploy_freeze_user(token, DUMMY_USER, False)
        print(unfreeze_user_result)

    # Step 3: Genesis
    #
    # Finalize genesis. The max supply of 300000000000000 wei needs to match the total
    # allocation above from user genesis.
    #
    # "noHyperliquidity" can also be set to disable hyperliquidity. In that case, no balance
    # should be associated with hyperliquidity from step 2 (user genesis).
    genesis_result = exchange.spot_deploy_genesis(token, "300000000000000", False)
    print(genesis_result)

    # Step 4: Register Spot
    #
    # Register the spot pair (TEST0/USDC) given base and quote token indices. 0 represents USDC.
    # The base token is the first token in the pair and the quote token is the second token.
    register_spot_result = exchange.spot_deploy_register_spot(token, 0)
    print(register_spot_result)
    # If registration is successful, a spot index will be returned. This spot index is required for
    # registering hyperliquidity.
    if register_token_result["status"] == "ok":
        spot = register_token_result["response"]["data"]
    else:
        return

    # Step 5: Register Hyperliquidity
    #
    # Registers hyperliquidity for the spot pair. In this example, hyperliquidity is registered
    # with a starting price of $2, an order size of 4, and 100 total orders.
    #
    # This step is required even if "noHyperliquidity" was set to True.
    # If "noHyperliquidity" was set to True during step 3 (genesis), then "n_orders" is required to be 0.
    register_hyperliquidity_result = exchange.spot_deploy_register_hyperliquidity(spot, 2.0, 4.0, 100, None)
    print(register_hyperliquidity_result)

    if SET_DEPLOYER_TRADING_FEE_SHARE:
        # Step 6
        #
        # Note that the deployer trading fee share cannot increase.
        # The default is already 100% and the smallest increment is 0.001%.
        set_deployer_trading_fee_share_result = exchange.spot_deploy_set_deployer_trading_fee_share(token, "100%")
        print(set_deployer_trading_fee_share_result)


if __name__ == "__main__":
    main()
