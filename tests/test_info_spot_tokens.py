"""Regression test for Info.__init__ bounds check on spot_meta tokens.

Background: when the HL API briefly returns a universe pair whose token
index is not in `spot_meta["tokens"]`, Info.__init__ raises (KeyError after
the dict-based refactor; IndexError before it) and every client crashes at
startup. The fix skips such pairs so Info() can initialize for all valid
pairs and stays useful until HL repairs the response.
"""

from hyperliquid.info import Info
from hyperliquid.utils.types import Meta, SpotMeta

EMPTY_META: Meta = {"universe": []}


def test_info_init_skips_universe_pair_with_unknown_token_index():
    # Tokens carry indices 0 and 1.
    # Universe has one valid pair (BTC/USDC) and one malformed pair pointing at
    # token index 5, which does not exist. Pre-patch this raised at startup.
    spot_meta: SpotMeta = {
        "tokens": [
            {"name": "BTC", "szDecimals": 5, "weiDecimals": 8, "index": 0,
             "tokenId": "0x" + "00" * 16, "isCanonical": True,
             "evmContract": None, "fullName": None, "deployerTradingFeeShare": "0.0"},
            {"name": "USDC", "szDecimals": 8, "weiDecimals": 8, "index": 1,
             "tokenId": "0x" + "11" * 16, "isCanonical": True,
             "evmContract": None, "fullName": None, "deployerTradingFeeShare": "0.0"},
        ],
        "universe": [
            {"name": "BTC_USDC", "tokens": [0, 1], "index": 0, "isCanonical": True},
            {"name": "@367", "tokens": [5, 1], "index": 1, "isCanonical": False},
        ],
    }

    # Should not raise. Valid pair is registered; malformed pair is skipped.
    info = Info(skip_ws=True, meta=EMPTY_META, spot_meta=spot_meta)
    assert info.coin_to_asset["BTC_USDC"] == 10000
    # Only valid pairs contribute to asset_to_sz_decimals.
    assert info.asset_to_sz_decimals[10000] == 5
    assert 10001 not in info.asset_to_sz_decimals
