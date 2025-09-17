#!/usr/bin/env python3
# Codex: Hyperliquid Agent Wallet Interaction
# Keeper Attribution — KinVault Sovereign Flow
# CT: 2025-09-17T08:29 AM CDT

import os
import json
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL

# === Load Keys ===
# Option A: From environment variables (secure)
PRIVATE_KEY = os.environ.get("AGENT_SECRET_KEY")
PUBLIC_ADDRESS = os.environ.get("AGENT_PUBLIC_ADDRESS")

# Option B: From config.json file
CONFIG_PATH = "examples/config.json"
if not PRIVATE_KEY or not PUBLIC_ADDRESS:
    with open(CONFIG_PATH) as f:
        config = json.load(f)
        PRIVATE_KEY = config["secret_key"]
        PUBLIC_ADDRESS = config["account_address"]

# === Initialize API Client ===
info = Info(MAINNET_API_URL, skip_ws=True)

# === Retrieve Portfolio & Attribution Check ===
try:
    portfolio = info.portfolio(PUBLIC_ADDRESS)
    print("✅ Portfolio Found for:", PUBLIC_ADDRESS)
    print(json.dumps(portfolio, indent=2))
except Exception as e:
    print("⚠️ Error accessing portfolio:", str(e))

# === Optional: Verify Agent Wallet was authorized ===
try:
    state = info.user_state(PUBLIC_ADDRESS)
    print("\n🔍 Agent Attribution State:")
    print(json.dumps(state, indent=2))
except Exception as e:
    print("⚠️ Error retrieving user state:", str(e))
