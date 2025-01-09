from hyperliquid.utils import constants
from hyperliquid.utils.signing import get_timestamp_ms, sign_multi_sig_l1_action_payload
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    multi_sig_wallets = example_utils.setup_multi_sig_wallets()

    # The outer signer is required to be an authorized user or an agent of the authorized user of the multi-sig user.

    # Address of the multi-sig user that the action will be executed for
    # Executing the action requires at least the specified threshold of signatures
    # required for that multi-sig user
    multi_sig_user = "0x0000000000000000000000000000000000000005"

    timestamp = get_timestamp_ms()

    # Define the multi-sig inner action
    action = {
        "type": "order",
        "orders": [{"a": 4, "b": True, "p": "1100", "s": "0.2", "r": False, "t": {"limit": {"tif": "Gtc"}}}],
        "grouping": "na",
    }

    timestamp = get_timestamp_ms()
    signatures = []

    # Collect signatures from each wallet in multi_sig_wallets. Each wallet must belong to a user.
    for wallet in multi_sig_wallets:
        # Sign the action with each wallet
        signature = sign_multi_sig_l1_action_payload(
            wallet,
            action,
            exchange.base_url == constants.MAINNET_API_URL,
            None,
            timestamp,
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
