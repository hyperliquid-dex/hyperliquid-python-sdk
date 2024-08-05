import pytest

from hyperliquid.info import Info
from hyperliquid.utils.types import Meta, SpotMeta

TEST_META: Meta = {"universe": []}
TEST_SPOT_META: SpotMeta = {"universe": [], "tokens": []}


@pytest.mark.vcr()
def test_get_user_state():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_state("0x5e9ee1089755c3435139848e47e6635505d5a13a")
    assert len(response["assetPositions"]) == 12
    assert response["marginSummary"]["accountValue"] == "1182.312496"


@pytest.mark.vcr()
def test_get_open_orders():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.open_orders("0x5e9ee1089755c3435139848e47e6635505d5a13a")
    assert len(response) == 196


@pytest.mark.vcr()
def test_get_frontend_open_orders():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.frontend_open_orders("0xCB331197E84f135AB9Ed6FB51Cd9757c0bd29d0D")
    assert len(response) == 3


@pytest.mark.vcr()
def test_get_all_mids():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.all_mids()
    assert "BTC" in response
    assert "ETH" in response
    assert "ATOM" in response
    assert "MATIC" in response


@pytest.mark.vcr()
def test_get_user_fills():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_fills("0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2")
    assert isinstance(response, list)
    assert response[0]["crossed"] is True


@pytest.mark.vcr()
def test_get_info():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.meta()
    assert len(response["universe"]) == 28
    assert response["universe"][0]["name"] == "BTC"
    assert response["universe"][0]["szDecimals"] == 5


@pytest.mark.vcr()
@pytest.mark.parametrize("endTime", [None, 1684811870000])
def test_get_funding_history(endTime):
    info = Info(skip_ws=True, spot_meta=TEST_SPOT_META)
    if endTime is None:
        response = info.funding_history(name="BTC", startTime=1681923833000)
    else:
        response = info.funding_history(name="BTC", startTime=1681923833000, endTime=endTime)
    assert len(response) != 0
    assert response[0]["coin"] == "BTC"
    for key in ["coin", "fundingRate", "premium", "time"]:
        assert key in response[0].keys()


@pytest.mark.vcr()
def test_get_l2_snapshot():
    info = Info(skip_ws=True, spot_meta=TEST_SPOT_META)
    response = info.l2_snapshot(name="DYDX")
    assert len(response) != 0
    assert len(response["levels"]) == 2
    assert response["coin"] == "DYDX"
    for key in ["coin", "time"]:
        assert key in response.keys()
    for key in ["n", "sz", "px"]:
        assert key in response["levels"][0][0].keys()
        assert key in response["levels"][1][0].keys()


@pytest.mark.vcr()
def test_get_candles_snapshot():
    info = Info(skip_ws=True, spot_meta=TEST_SPOT_META)
    response = info.candles_snapshot(name="kPEPE", interval="1h", startTime=1684702007000, endTime=1684784807000)
    assert len(response) == 24
    for key in ["T", "c", "h", "i", "l", "n", "o", "s", "t", "v"]:
        assert key in response[0].keys()


@pytest.mark.vcr()
def test_user_funding_history_with_end_time():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_funding_history(
        user="0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2", startTime=1681923833000, endTime=1682010233000
    )
    assert isinstance(response, list), "The answer should be a list"
    for record in response:
        assert "delta" in record, "There must be a key 'delta'"
        assert "hash" in record, "There must be a key 'hash'"
        assert "time" in record, "There must be a key 'time'"
        delta = record["delta"]
        for key in ["coin", "fundingRate", "szi", "type", "usdc"]:
            assert key in delta, f"В 'delta' There must be a key '{key}'"
        assert delta["type"] == "funding", "The type must be 'funding'"


@pytest.mark.vcr()
def test_user_funding_history_without_end_time():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_funding_history(user="0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2", startTime=1681923833000)
    assert isinstance(response, list), "The answer must be a list"
    for record in response:
        assert "delta" in record, "There must be a key 'delta'"
        assert "hash" in record, "There must be a key 'hash'"
        assert "time" in record, "There must be a key 'time'"
        delta = record["delta"]
        for key in ["coin", "fundingRate", "szi", "type", "usdc"]:
            assert key in delta, f"В 'delta' There must be a '{key}'"
        assert delta["type"] == "funding", "The type must be 'funding'"
