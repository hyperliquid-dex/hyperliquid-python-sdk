from typing import Dict

from eth_account import Account

from hyperliquid.exchange import Exchange

TEST_META = {"universe": []}
TEST_SPOT_META = {"universe": [], "tokens": {}}


def _make_exchange(monkeypatch):
    wallet = Account.create()
    exchange = Exchange(
        wallet,
        base_url="https://api.hyperliquid.xyz",
        meta=TEST_META,
        spot_meta=TEST_SPOT_META,
    )

    monkeypatch.setattr("hyperliquid.exchange.get_timestamp_ms", lambda: 1)
    monkeypatch.setattr("hyperliquid.exchange.sign_l1_action", lambda *_, **__: "signature")

    captured: Dict[str, Dict[str, object]] = {}

    def fake_post(path: str, payload: Dict[str, object]) -> Dict[str, object]:
        captured["path"] = path
        captured["payload"] = payload
        return {"status": "ok"}

    monkeypatch.setattr(exchange, "post", fake_post)

    return exchange, captured


def test_perp_deploy_set_oracle_without_external_prices(monkeypatch):
    exchange, captured = _make_exchange(monkeypatch)

    exchange.perp_deploy_set_oracle(
        "test-dex",
        {"TEST:ASSET": "1.0"},
        [{"TEST:ASSET": "2.0"}],
    )

    assert captured["path"] == "/exchange"
    action = captured["payload"]["action"]["setOracle"]
    assert action["dex"] == "test-dex"
    assert action["oraclePxs"] == [("TEST:ASSET", "1.0")]
    assert action["markPxs"] == [[("TEST:ASSET", "2.0")]]
    assert "externalPerpPxs" not in action


def test_perp_deploy_set_oracle_with_external_prices(monkeypatch):
    exchange, captured = _make_exchange(monkeypatch)

    exchange.perp_deploy_set_oracle(
        "test-dex",
        {"TEST:ASSET": "1.0"},
        [{"TEST:ASSET": "2.0"}],
        external_perp_pxs={"OTHER:ASSET": "3.0"},
    )

    action = captured["payload"]["action"]["setOracle"]
    assert action["externalPerpPxs"] == [("OTHER:ASSET", "3.0")]
