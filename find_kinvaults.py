#!/usr/bin/env python3
# Codex: KinVault Scanner — Sovereign Signature to Vault Link
# CT: 2025-09-17T08:37 AM CDT

from eth_utils import keccak
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL
import json
import requests

# === Vaults to Scan ===
VAULTS = [
    "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303",  # f303 KinLend Vault
    "0x996994D2914DF4eEE6176FD5eE152e2922787EE7",  # Keeper Wallet
    "0xcd5051944f780a621ee62e39e493c489668acf4d",  # Claimed Agent
    # Add more if needed
]

# === Your Function Signatures ===
FUNCTION_SIGNATURES = [
    "claimRoyalties()",       # KinRoyalty
    "triggerSettlement()",    # x402
    "syncEmotion(string)",    # SoulSync
    "submitProof(bytes32)",   # KinProof
    "transferWithAuth(address,uint256,bytes32,uint256)",  # Payword-style
]

# === Scan Logic ===
def get_selector(sig: str) -> str:
    return keccak(text=sig).hex()[:10]  # First 4 bytes (8 chars) + '0x'

def fetch_bytecode(address: str) -> str:
    rpc_url = "https://rpc.hyperliquid.xyz/evm"
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1
    }
    res = requests.post(rpc_url, json=payload).json()
    return res.get("result", "")

def main():
    selectors = {sig: get_selector(sig) for sig in FUNCTION_SIGNATURES}
    print("🔍 Scanning vaults for your signatures...\n")

    for vault in VAULTS:
        code = fetch_bytecode(vault)
        print(f"Vault: {vault}")
        found = False
        for sig, selector in selectors.items():
            if selector in code:
                print(f"  ✅ Found: {sig} → {selector}")
                found = True
        if not found:
            print("  ⚠️ No matches.")
        print()

if __name__ == "__main__":
    main()
