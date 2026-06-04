import example_utils

from hyperliquid.utils import constants
from hyperliquid.utils.signing import (
    USER_SET_ABSTRACTION_SIGN_TYPES,
    get_timestamp_ms,
    sign_multi_sig_user_signed_action_payload,
)


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    multi_sig_wallets = example_utils.setup_multi_sig_wallets()

    # The outer signer is required to be an authorized user or an agent of an authorized user of the multi-sig user.

    # Address of the multi-sig user that the action will be executed for.
    # Executing the action requires at least the specified threshold of signatures for that multi-sig user.
    multi_sig_user = "0x0000000000000000000000000000000000000005"

    # userSetAbstraction may target the multi-sig user itself or a sub-account user controlled by the multi-sig user.
    target_user = multi_sig_user
    abstraction = "disabled"
    timestamp = get_timestamp_ms()

    # Must use the human abstraction string here. Exchange.multi_sig canonicalizes this action to the wire enum value
    # when it builds and signs the outer multi-sig payload. It is expected that the different signatures need different
    # versions of this value.
    action = {
        "type": "userSetAbstraction",
        "signatureChainId": "0x66eee",
        "hyperliquidChain": "Testnet",
        "user": target_user.lower(),
        "abstraction": abstraction,
        "nonce": timestamp,
    }
    signatures = []

    # Collect signatures from each wallet in multi_sig_wallets. Each wallet must belong to a user.
    for wallet in multi_sig_wallets:
        signature = sign_multi_sig_user_signed_action_payload(
            wallet,
            action,
            exchange.base_url == constants.MAINNET_API_URL,
            USER_SET_ABSTRACTION_SIGN_TYPES,
            "HyperliquidTransaction:UserSetAbstraction",
            multi_sig_user,
            address,
        )
        signatures.append(signature)

    print("current user abstraction state:", info.query_user_abstraction_state(target_user))
    multi_sig_result = exchange.multi_sig(multi_sig_user, action, signatures, timestamp)
    print("multi-sig userSetAbstraction result:", multi_sig_result)
    print("updated user abstraction state:", info.query_user_abstraction_state(target_user))


if __name__ == "__main__":
    main()
