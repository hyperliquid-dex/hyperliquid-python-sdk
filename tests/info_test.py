import pytest

from hyperliquid.info import Info


@pytest.mark.vcr()
def test_get_user_state():
    info = Info(skip_ws=True)
    response = info.user_state("0x5e9ee1089755c3435139848e47e6635505d5a13a")
    assert len(response["assetPositions"]) == 12
    assert response["marginSummary"]["accountValue"] == "1182.312496"


@pytest.mark.vcr()
def test_get_open_orders():
    info = Info(skip_ws=True)
    response = info.open_orders("0x5e9ee1089755c3435139848e47e6635505d5a13a")
    assert len(response) == 196


@pytest.mark.vcr()
def test_get_all_mids():
    info = Info(skip_ws=True)
    response = info.all_mids()
    assert "BTC" in response
    assert "ETH" in response
    assert "ATOM" in response
    assert "MATIC" in response


@pytest.mark.vcr()
def test_get_user_fills():
    info = Info(skip_ws=True)
    response = info.user_fills("0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2")
    assert isinstance(response, list)
    assert response[0]["crossed"] is True


@pytest.mark.vcr()
def test_get_info():
    info = Info(skip_ws=True)
    response = info.meta()
    assert len(response["universe"]) == 12
    assert response["universe"][0]["name"] == "BTC"
    assert response["universe"][0]["szDecimals"] == 5
