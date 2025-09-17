#!/usr/bin/env python3
# Codex: KinVault Scanner — Sovereign Signature to Vault Link
# Dropped by Keeper into Codex env
# CT: 2025-09-17T08:44 AM CDT

import requests
from eth_utils import keccak

# === Config ===
VAULTS = [
    "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303",  # KinLend Agent f303
    "0x996994D2914DF4eEE6176FD5eE152e2922787EE7",  # Codex Vault
    "0xcd5051944f780a621ee62e39e493c489668acf4d",  # Hyperliquid Agent
]

FUNCTION_SIGNATURES = [
    "claimRoyalties()",  # KinRoyalty
    "triggerSettlement()",  # x402 payout
    "syncEmotion(string)",  # SoulSync signal
    "submitProof(bytes32)",  # SoulSyncProof
    "transferWithAuth(address,uint256,bytes32,uint256)",  # PayWord
]

RPC_URL = "https://rpc.hyperliquid.xyz/evm"


# === Helpers ===
def sig_to_selector(sig: str) -> str:
    return keccak(text=sig).hex()[:10]  # first 4 bytes as hex selector


def fetch_bytecode(address: str) -> str:
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1,
    }
    response = requests.post(RPC_URL, json=payload).json()
    return response.get("result", "")


# === Main ===
def main():
    print("🔍 Scanning vaults for authored function selectors...\n")
    selectors = {sig: sig_to_selector(sig) for sig in FUNCTION_SIGNATURES}

    for vault in VAULTS:
        print(f"Vault: {vault}")
        bytecode = fetch_bytecode(vault)

        matches = []
        for sig, selector in selectors.items():
            if selector in bytecode:
                matches.append((sig, selector))

        if matches:
            for sig, selector in matches:
                print(f"  ✅ {sig} → {selector}")
        else:
            print("  ⚠️ No match found.")

        print()


if __name__ == "__main__":
    main(
