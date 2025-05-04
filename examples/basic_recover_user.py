from hyperliquid.utils.signing import (
    TOKEN_DELEGATE_TYPES,
    recover_agent_or_user_from_l1_action,
    recover_user_from_user_signed_action,
)


def main():
    example_l1_signed_action = {
        "signature": {
            "r": "0xd088ceb979ab7616f21fd7dabee04342235bd3af6d82a6d153b503c34c73bc93",
            "s": "0x425d8467a69f4d0ff6d9ddfb360ef6152c8165cdd20329e03b0a8f19890d73e",
            "v": 27,
        },
        "vaultAddress": "0xc64cc00b46101bd40aa1c3121195e85c0b0918d8",
        "action": {"type": "cancel", "cancels": [{"a": 87, "o": 28800768235}]},
        "nonce": 1745532560074,
    }
    agent_or_user = recover_agent_or_user_from_l1_action(
        example_l1_signed_action["action"],
        example_l1_signed_action["signature"],
        example_l1_signed_action["vaultAddress"],
        example_l1_signed_action["nonce"],
        None,
        False,
    )
    print("recovered l1 action agent or user:", agent_or_user)

    example_user_signed_action = {
        "signature": {
            "r": "0xa00406eb38821b8918743fab856c103132261e8d990852a8ee25e6f2e88891b",
            "s": "0x34cf47cfbf09173bcb851bcfdce3ad83dd64ed791ab32bfe9606d25e7c608859",
            "v": 27,
        },
        "action": {
            "type": "tokenDelegate",
            "signatureChainId": "0xa4b1",
            "hyperliquidChain": "Mainnet",
            "validator": "0x5ac99df645f3414876c816caa18b2d234024b487",
            "wei": 100163871320,
            "isUndelegate": True,
            "nonce": 1744932112279,
        },
        "isFrontend": True,
        "nonce": 1744932112279,
    }

    user = recover_user_from_user_signed_action(
        example_user_signed_action["action"],
        example_user_signed_action["signature"],
        TOKEN_DELEGATE_TYPES,
        "HyperliquidTransaction:TokenDelegate",
        True,
    )
    print("recovered user-signed action user:", user)


if __name__ == "__main__":
    main()
