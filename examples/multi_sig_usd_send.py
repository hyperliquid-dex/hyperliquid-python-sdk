import example_utils

from hyperliquid.utils import constants
from hyperliquid.utils.signing import USD_SEND_SIGN_TYPES, get_timestamp_ms, sign_multi_sig_user_signed_action_payload


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    multi_sig_wallets = example_utils.setup_multi_sig_wallets()

    # The outer signer is required to be an authorized user or an agent of the authorized user of the multi-sig user.

    # Address of the multi-sig user that the action will be executed for
    # Executing the action requires at least the specified threshold of signatures
    # required for that multi-sig user
    multi_sig_user = "0x0000000000000000000000000000000000000005"

    timestamp = get_timestamp_ms()

    # Define the multi-sig inner action - in this case, sending USD
    action = {
        "type": "usdSend",
        "signatureChainId": "0x66eee",
        "hyperliquidChain": "Testnet",
        "destination": "0x0000000000000000000000000000000000000000",
        "amount": "100.0",
        "time": timestamp,
    }
    signatures = []

    # Collect signatures from each wallet in multi_sig_wallets. Each wallet must belong to a user.
    for wallet in multi_sig_wallets:
        # Sign the action with each wallet
        signature = sign_multi_sig_user_signed_action_payload(
            wallet,
            action,
            exchange.base_url == constants.MAINNET_API_URL,
            USD_SEND_SIGN_TYPES,
            "HyperliquidTransaction:UsdSend",
            multi_sig_user,
            address,
        )
        signatures.append(signature)

    # Execute the multi-sig action with all collected signatures
    # This will only succeed if enough valid signatures are provided
    multi_sig_result = exchange.multi_sig(multi_sig_user, action, signatures, timestamp)
    print(multi_sig_result)


if __name__ == "__main__":
    main()
