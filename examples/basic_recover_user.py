import time
from typing import TypedDict, Optional, Dict, Any, Union

# Import necessary utilities from the Hyperliquid SDK
from hyperliquid.utils.signing import (
    TOKEN_DELEGATE_TYPES,
    recover_agent_or_user_from_l1_action,
    recover_user_from_user_signed_action,
)

# --- Type Definitions for Example Data Clarity ---

class Signature(TypedDict):
    r: str
    s: str
    v: int

class L1SignedActionExample(TypedDict):
    signature: Signature
    vaultAddress: str
    action: Dict[str, Any]
    nonce: int
    expiresAfter: Optional[int] # Explicitly defined if present

class UserSignedActionExample(TypedDict):
    signature: Signature
    action: Dict[str, Any]
    isFrontend: bool
    nonce: int


def main():
    # --- Example 1: L1-Signed Action Recovery (e.g., placing/cancelling orders) ---
    
    # L1 actions are signed using the EIP-712 domain hash including the chain ID and contract address.
    example_l1_signed_action: L1SignedActionExample = {
        "signature": {
            "r": "0xd088ceb979ab7616f21fd7dabee04342235bd3af6d82a6d153b503c34c73bc93",
            "s": "0x425d8467a69f4d0ff6d9ddfb360ef6152c8165cdd20329e03b0a8f19890d73e",
            "v": 27,
        },
        "vaultAddress": "0xc64cc00b46101bd40aa1c3121195e85c0b0918d8",
        "action": {"type": "cancel", "cancels": [{"a": 87, "o": 28800768235}]},
        "nonce": 1745532560074,
        # 'expiresAfter' is not present in this specific example
    }
    
    # Recover the address (either user wallet or approved agent) from the L1 action payload.
    agent_or_user = recover_agent_or_user_from_l1_action(
        example_l1_signed_action["action"],
        example_l1_signed_action["signature"],
        example_l1_signed_action["vaultAddress"],
        example_l1_signed_action["nonce"],
        # OPTIMIZATION: Use keyword arguments for clarity
        expires_after=None, 
        is_mainnet=False, # Assuming this is a Testnet/Arbitrum Chain ID (not 0x66eee)
    )
    print(f"Recovered L1 action signer (Agent or User): {agent_or_user}")

    # --- Example 2: User-Signed Action Recovery (e.g., transfers, delegation) ---

    # User-signed actions use a different EIP-712 domain type that may include 
    # the chain ID, specific to the action type (e.g., TokenDelegate).
    example_user_signed_action: UserSignedActionExample = {
        "signature": {
            "r": "0xa00406eb38821b8918743fab856c103132261e8d990852a8ee25e6f2e88891b",
            "s": "0x34cf47cfbf09173bcb851bcfdce3ad83dd64ed791ab32bfe9606d25e7c608859",
            "v": 27,
        },
        "action": {
            "type": "tokenDelegate",
            "signatureChainId": "0xa4b1", # Arbitrum Chain ID
            "hyperliquidChain": "Mainnet", # Hyperliquid internal chain name
            "validator": "0x5ac99df645f3414876c816caa18b2d234024b487",
            "wei": 100163871320,
            "isUndelegate": True,
            "nonce": 1744932112279,
        },
        "isFrontend": True,
        "nonce": 1744932112279,
    }

    # Recover the user's address from the user-signed action payload.
    user = recover_user_from_user_signed_action(
        example_user_signed_action["action"],
        example_user_signed_action["signature"],
        TOKEN_DELEGATE_TYPES, # Specific EIP-712 types for this action
        "HyperliquidTransaction:TokenDelegate", # EIP-712 primary type
        True, # is_mainnet (determines the EIP-712 domain chain ID used for signing)
    )
    print(f"Recovered User-Signed action user: {user}")


if __name__ == "__main__":
    main()
