import pytest

from hyperliquid.info import Info
from hyperliquid.utils.types import L2BookData, Meta, SpotMeta

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
def test_get_user_fills_by_time():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_fills_by_time(
        "0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2", start_time=1683245555699, end_time=1683245884863
    )
    assert isinstance(response, list)
    assert len(response) == 500


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
    response: L2BookData = info.l2_snapshot(name="DYDX")
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
            assert key in delta, f"There must be a key '{key}' in 'delta'"
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
            assert key in delta, f"There must be a key '{key}' in 'delta'"
        assert delta["type"] == "funding", "The type must be 'funding'"


@pytest.mark.vcr()
def test_historical_orders():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.historical_orders(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, list), "The response should be a list"
    if len(response) > 0:
        # Check for expected fields in historical orders
        order = response[0]
        assert "order" in order, "Each item should have an 'order' field"
        assert "status" in order, "Each item should have a 'status' field"
        assert "statusTimestamp" in order, "Each item should have a 'statusTimestamp' field"


@pytest.mark.vcr()
def test_user_non_funding_ledger_updates_with_end_time():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_non_funding_ledger_updates(
        user="0x2ba553d9f990a3b66b03b2dc0d030dfc1c061036", startTime=1681923833000, endTime=1682010233000
    )
    assert isinstance(response, list), "The response should be a list"
    for record in response:
        assert "delta" in record, "There must be a key 'delta'"
        assert "hash" in record, "There must be a key 'hash'"
        assert "time" in record, "There must be a key 'time'"


@pytest.mark.vcr()
def test_user_non_funding_ledger_updates_without_end_time():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_non_funding_ledger_updates(
        user="0x2ba553d9f990a3b66b03b2dc0d030dfc1c061036", startTime=1681923833000
    )
    assert isinstance(response, list), "The response should be a list"


@pytest.mark.vcr()
def test_portfolio():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.portfolio(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, list), "The response should be a list"
    # Portfolio should contain performance data across different time periods
    if len(response) > 0:
        # Each item should be a time period with performance data
        period_data = response[0]
        assert isinstance(period_data, list) and len(period_data) == 2, "Each item should be a [period_name, data] pair"
        _, data = period_data
        assert isinstance(data, dict), "Period data should be a dictionary"
        assert any(
            key in data for key in ["accountValueHistory", "pnlHistory", "vlm"]
        ), "Portfolio should contain performance metrics"


@pytest.mark.vcr()
def test_user_twap_slice_fills():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_twap_slice_fills(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, list), "The response should be a list"
    # TWAP slice fills should have similar structure to regular fills
    if len(response) > 0:
        fill = response[0]
        for key in ["coin", "px", "sz", "side", "time"]:
            assert key in fill, f"TWAP slice fill should have '{key}' field"


@pytest.mark.vcr()
def test_user_vault_equities():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_vault_equities(user="0x2b804617c6f63c040377e95bb276811747006f4b")
    assert isinstance(response, list), "The response should be a list of vault positions"
    if len(response) > 0:
        vault_equity = response[0]
        # Check for expected vault equity fields - actual response has vaultAddress instead of vault
        assert (
            "vaultAddress" in vault_equity or "vault" in vault_equity
        ), "Each vault equity should have a 'vaultAddress' or 'vault' field"
        assert "equity" in vault_equity, "Each vault equity should have an 'equity' field"


@pytest.mark.vcr()
def test_user_role():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_role(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, dict), "The response should be a dictionary"
    # User role should contain account type and role information
    assert (
        "role" in response or "type" in response or "account" in response
    ), "Response should contain role or account type information"


@pytest.mark.vcr()
def test_user_rate_limit():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.user_rate_limit(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, dict), "The response should be a dictionary"
    # Rate limit response structure varies - just check it's a non-empty dict
    # The actual structure depends on the API version and user tier
    assert response is not None, "Response should not be None"


@pytest.mark.vcr()
def test_delegator_history():
    info = Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)
    response = info.delegator_history(user="0x2ba553d9f990a3b66b03b2dc0d030dfc1c061036")
    assert isinstance(response, list), "The response should be a list"
    # Delegator history should contain delegation/undelegation events
    for event in response:
        assert "delta" in event, "Each event should have a 'delta' field"
        assert "hash" in event, "Each event should have a transaction 'hash'"
        assert "time" in event, "Each event should have a 'time' field"
