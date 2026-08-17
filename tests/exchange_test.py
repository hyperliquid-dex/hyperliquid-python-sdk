import eth_account

from hyperliquid.exchange import Exchange
from hyperliquid.utils.types import Meta, SpotMeta

TEST_META: Meta = {"universe": [{"name": "ABC", "szDecimals": 0}]}
TEST_SPOT_META: SpotMeta = {
    "universe": [{"name": "@1", "tokens": [1, 0], "index": 1, "isCanonical": False}],
    "tokens": [
        {
            "name": "USDC",
            "szDecimals": 8,
            "weiDecimals": 8,
            "index": 0,
            "tokenId": "0x6d1e7cde53ba9467b783cb7c530ce054",
            "isCanonical": True,
            "evmContract": None,
            "fullName": None,
        },
        {
            "name": "PURR",
            "szDecimals": 0,
            "weiDecimals": 5,
            "index": 1,
            "tokenId": "0xc1fb593aeffbeb02f85e0308e9956a90",
            "isCanonical": True,
            "evmContract": None,
            "fullName": None,
        },
    ],
}


def make_exchange() -> Exchange:
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    return Exchange(wallet, meta=TEST_META, spot_meta=TEST_SPOT_META)


def test_slippage_price_perp():
    exchange = make_exchange()
    # 5 significant figures, then at most 6 - szDecimals decimals
    assert exchange._slippage_price("ABC", True, 0.05, 0.0012345678) == 0.001296


def test_slippage_price_spot():
    exchange = make_exchange()
    # spot allows 8 - szDecimals decimals
    assert exchange._slippage_price("@1", True, 0.05, 0.0012345678) == 0.0012963


def test_slippage_price_builder_deployed_perp():
    exchange = make_exchange()
    # builder-deployed perp dex assets start at 110000, above the spot range, but are still perps
    exchange.info.name_to_coin["test:ABC"] = "test:ABC"
    exchange.info.coin_to_asset["test:ABC"] = 110000
    exchange.info.asset_to_sz_decimals[110000] = 0
    assert exchange._slippage_price("test:ABC", True, 0.05, 0.0012345678) == 0.001296
