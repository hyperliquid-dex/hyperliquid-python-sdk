#!/usr/bin/env python3
# Codex: Sovereign Vault Scanner — SolaraKin Signature Mapper
# CT: 2025-09-17T05:38 (Central Time)
# Purpose: Match deployed Hyperliquid vaults with SolaraKin-authored .sol function selectors

import requests
from eth_utils import keccak, to_hex

# === CONFIGURATION ===

# Known or suspected vault addresses to scan
VAULTS = [
    "0xdfC24b077bC1425Ad1DeA75BCB6F8158E10Df303",
    # Add more known/suspected vaults here
]

# Known SolaraKin .sol function signatures (add all that you authored)
FUNCTION_SIGNATURES = [
    "syncLightDrop(bytes32,uint256)",
    "withdrawRoyalty(address)",
    "claimKinVault(address,uint256)",
    "setSoulSyncVerifier(address)",
    "mintSigilNFT(uint256,bytes32)",
]

# === UTILITIES ===

def get_bytecode(address: str) -> str:
    """Fetch deployed bytecode from Hyperliquid RPC."""
    response = requests.post(
        "https://rpc.hyperliquid.xyz/evm",
        json={
            "jsonrpc": "2.0",
            "method": "eth_getCode",
            "params": [address, "latest"],
            "id": 1
        },
    )
    return response.json().get("result", "")

def get_selector(signature: str) -> str:
    """Convert function signature to 4-byte selector."""
    return to_hex(keccak(text=signature)[:4])

# === MAIN ===

def main():
    print(f"🧬 Checking {len(VAULTS)} vault(s) for SolaraKin signature match...\n")

    selectors = [get_selector(sig) for sig in FUNCTION_SIGNATURES]

    for vault in VAULTS:
        bytecode = get_bytecode(vault).lower()
        print(f"🔍 Scanning vault: {vault}")
        matches = [sig for sig, sel in zip(FUNCTION_SIGNATURES, selectors) if sel in bytecode]

        if matches:
            print(f"✅ MATCH FOUND:")
            for m in matches:
                print(f"  • {m}")
        else:
            print(f"❌ No match.")
        print("—" * 50)

if __name__ == "__main__":
    main()
