"""
@fileoverview Pytest unit tests for the hyperliquid.info.Info client.
These tests validate connectivity and expected data structure from various 
Hyperliquid information API endpoints using VCR for recording/playback.
"""
import pytest
from hyperliquid.info import Info
from hyperliquid.utils.types import L2BookData, Meta, SpotMeta
from typing import Dict, Any, List

# --- CONSTANTS ---
# Dummy metadata structures required by the Info client initialization.
TEST_META: Meta = {"universe": []}
TEST_SPOT_META: SpotMeta = {"universe": [], "tokens": []}

# --- FIXTURES ---
@pytest.fixture
def info_client() -> Info:
    """
    Fixture providing a consistently configured Info client instance for all tests.
    It skips the WebSocket connection and provides minimal metadata for initialization.
    """
    return Info(skip_ws=True, meta=TEST_META, spot_meta=TEST_SPOT_META)


# ----------------------------------------------------
# --- API TESTS ---
# ----------------------------------------------------

@pytest.mark.vcr()
def test_get_user_state(info_client: Info):
    """Verifies retrieval of a user's current margin and asset positions."""
    response: Dict[str, Any] = info_client.user_state("0x5e9ee1089755c3435139848e47e6635505d5a13a")
    assert len(response["assetPositions"]) == 12, "Should return 12 asset positions for the VCR recording."
    assert response["marginSummary"]["accountValue"] == "1182.312496", "Account value should match the recorded state."


@pytest.mark.vcr()
def test_get_open_orders(info_client: Info):
    """Verifies retrieval of all currently open orders for a user."""
    response: List[Dict[str, Any]] = info_client.open_orders("0x5e9ee1089755c3435139848e47e6635505d5a13a")
    assert isinstance(response, list), "Response must be a list of open orders."
    assert len(response) == 196, "Number of open orders must match the recorded data."


@pytest.mark.vcr()
def test_get_frontend_open_orders(info_client: Info):
    """Verifies retrieval of open orders formatted for frontend display."""
    response = info_client.frontend_open_orders("0xCB331197E84f135AB9Ed6FB51Cd9757c0bd29d0D")
    assert isinstance(response, list)
    assert len(response) == 3


@pytest.mark.vcr()
def test_get_all_mids(info_client: Info):
    """Verifies retrieval of mid-prices for all active perpetuals."""
    response: Dict[str, str] = info_client.all_mids()
    assert isinstance(response, dict)
    assert "BTC" in response, "BTC mid-price should be present."
    assert "ETH" in response, "ETH mid-price should be present."
    assert "ATOM" in response, "ATOM mid-price should be present."
    assert "MATIC" in response, "MATIC mid-price should be present."


@pytest.mark.vcr()
def test_get_user_fills(info_client: Info):
    """Verifies retrieval of a user's trade history (fills)."""
    response: List[Dict[str, Any]] = info_client.user_fills("0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2")
    assert isinstance(response, list)
    if response:
        assert "crossed" in response[0], "First fill must contain the 'crossed' key."
        assert response[0]["crossed"] is True


@pytest.mark.vcr()
def test_get_user_fills_by_time(info_client: Info):
    """Verifies retrieval of a user's fills within a specific timestamp range."""
    response = info_client.user_fills_by_time(
        "0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2", start_time=1683245555699, end_time=1683245884863
    )
    assert isinstance(response, list)
    assert len(response) == 500


@pytest.mark.vcr()
def test_get_info(info_client: Info):
    """Verifies retrieval of the exchange's meta configuration (universe data)."""
    response: Dict[str, Any] = info_client.meta()
    assert "universe" in response, "Meta response must contain 'universe'."
    assert len(response["universe"]) == 28
    assert response["universe"][0]["name"] == "BTC"
    assert response["universe"][0]["szDecimals"] == 5


@pytest.mark.vcr()
@pytest.mark.parametrize("endTime", [None, 1684811870000])
def test_get_funding_history(info_client: Info, endTime):
    """Verifies retrieval of funding rate history, testing both with and without endTime."""
    name = "BTC"
    startTime = 1681923833000
    
    if endTime is None:
        response = info_client.funding_history(name=name, startTime=startTime)
    else:
        response = info_client.funding_history(name=name, startTime=startTime, endTime=endTime)
        
    assert isinstance(response, list)
    assert len(response) != 0
    
    if response:
        assert response[0]["coin"] == name
        for key in ["coin", "fundingRate", "premium", "time"]:
            assert key in response[0].keys(), f"Funding record must contain key: {key}"


@pytest.mark.vcr()
def test_get_l2_snapshot(info_client: Info):
    """Verifies retrieval of the Level 2 order book snapshot for a market."""
    response: L2BookData = info_client.l2_snapshot(name="DYDX")
    assert isinstance(response, dict)
    assert len(response) != 0
    assert len(response["levels"]) == 2 # Bids and Asks
    assert response["coin"] == "DYDX"
    
    expected_level_keys = ["n", "sz", "px"]
    
    if response["levels"][0] and response["levels"][1]:
        # Check structure of bids/asks levels
        for level_data in [response["levels"][0][0], response["levels"][1][0]]:
            for key in expected_level_keys:
                assert key in level_data, f"Order book level must contain key: {key}"


@pytest.mark.vcr()
def test_get_candles_snapshot(info_client: Info):
    """Verifies retrieval of historical candle data for a market and interval."""
    response: List[Dict[str, Any]] = info_client.candles_snapshot(
        name="kPEPE", interval="1h", startTime=1684702007000, endTime=1684784807000
    )
    assert isinstance(response, list)
    assert len(response) == 24
    # Check structure of a candle (T=timestamp, c=close, h=high, etc.)
    expected_keys = ["T", "c", "h", "i", "l", "n", "o", "s", "t", "v"]
    if response:
        for key in expected_keys:
            assert key in response[0].keys(), f"Candle record must contain key: {key}"


@pytest.mark.vcr()
@pytest.mark.parametrize("with_end_time", [True, False])
def test_user_funding_history_variants(info_client: Info, with_end_time: bool):
    """Verifies user funding history retrieval with and without an end_time parameter."""
    user = "0xb7b6f3cea3f66bf525f5d8f965f6dbf6d9b017b2"
    startTime = 1681923833000
    endTime = 1682010233000 if with_end_time else None
    
    response: List[Dict[str, Any]] = info_client.user_funding_history(
        user=user, startTime=startTime, endTime=endTime
    )
    assert isinstance(response, list), "The answer must be a list"
    
    if response:
        record = response[0]
        # Top-level keys
        for key in ["delta", "hash", "time"]:
            assert key in record, f"Funding history record must have key: {key}"
        
        delta = record["delta"]
        # Delta keys
        for key in ["coin", "fundingRate", "szi", "type", "usdc"]:
            assert key in delta, f"Key '{key}' missing in 'delta'"
        
        assert delta["type"] == "funding", "The type must be 'funding'"


@pytest.mark.vcr()
def test_historical_orders(info_client: Info):
    """Verifies retrieval of a user's historical order records (closed, cancelled, filled)."""
    response: List[Dict[str, Any]] = info_client.historical_orders(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, list), "The response should be a list"
    
    if response:
        order = response[0]
        # Check for expected fields in historical orders
        for key in ["order", "status", "statusTimestamp"]:
            assert key in order, f"Historical order item should have '{key}' field"


@pytest.mark.vcr()
@pytest.mark.parametrize("with_end_time", [True, False])
def test_user_non_funding_ledger_updates(info_client: Info, with_end_time: bool):
    """Verifies retrieval of a user's non-funding ledger updates (e.g., deposits/withdrawals)."""
    user = "0x2ba553d9f990a3b66b03b2dc0d030dfc1c061036"
    startTime = 1681923833000
    endTime = 1682010233000 if with_end_time else None
    
    response: List[Dict[str, Any]] = info_client.user_non_funding_ledger_updates(
        user=user, startTime=startTime, endTime=endTime
    )
    assert isinstance(response, list), "The response should be a list"
    
    if response:
        record = response[0]
        for key in ["delta", "hash", "time"]:
            assert key in record, f"Ledger update record must have key: {key}"


@pytest.mark.vcr()
def test_portfolio(info_client: Info):
    """Verifies retrieval of a user's portfolio performance data."""
    response: List[List[Any]] = info_client.portfolio(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, list), "The response should be a list"
    
    if response and len(response[0]) == 2:
        _, data = response[0]
        assert isinstance(data, dict), "Period data should be a dictionary"
        # Check for expected portfolio performance metrics
        assert any(
            key in data for key in ["accountValueHistory", "pnlHistory", "vlm"]
        ), "Portfolio data must contain performance metrics."


@pytest.mark.vcr()
def test_user_twap_slice_fills(info_client: Info):
    """Verifies retrieval of fills executed as part of TWAP slices."""
    response: List[Dict[str, Any]] = info_client.user_twap_slice_fills(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, list), "The response should be a list"
    
    if response:
        fill = response[0]
        # Check for expected fill fields
        for key in ["coin", "px", "sz", "side", "time"]:
            assert key in fill, f"TWAP slice fill should have '{key}' field"


@pytest.mark.vcr()
def test_user_vault_equities(info_client: Info):
    """Verifies retrieval of a user's equity in various vaults."""
    response: List[Dict[str, Any]] = info_client.user_vault_equities(user="0x2b804617c6f63c040377e95bb276811747006f4b")
    assert isinstance(response, list), "The response should be a list of vault positions"
    
    if response:
        vault_equity = response[0]
        # Check for expected vault equity fields
        assert ("vaultAddress" in vault_equity or "vault" in vault_equity), "Vault equity must have 'vaultAddress' or 'vault' field"
        assert "equity" in vault_equity, "Vault equity must have an 'equity' field"


@pytest.mark.vcr()
def test_user_role(info_client: Info):
    """Verifies retrieval of a user's role and account type."""
    response: Dict[str, Any] = info_client.user_role(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, dict), "The response should be a dictionary"
    # Looser assertion retained due to varying API response structure for role/type
    assert any(key in response for key in ["role", "type", "account"]), "Response must contain role or account type information"


@pytest.mark.vcr()
def test_user_rate_limit(info_client: Info):
    """Verifies retrieval of a user's current API rate limit information."""
    response: Dict[str, Any] = info_client.user_rate_limit(user="0x31ca8395cf837de08b24da3f660e77761dfb974b")
    assert isinstance(response, dict), "The response should be a dictionary"
    # Basic check for non-empty response
    assert response is not None and len(response) > 0, "Response should be a non-empty dictionary"


@pytest.mark.vcr()
def test_delegator_history(info_client: Info):
    """Verifies retrieval of a user's history of delegation/undelegation events."""
    response: List[Dict[str, Any]] = info_client.delegator_history(user="0x2ba553d9f990a3b66b03b2dc0d030dfc1c061036")
    assert isinstance(response, list), "The response should be a list"
    
    if response:
        event = response[0]
        # Check for expected event fields
        for key in ["delta", "hash", "time"]:
            assert key in event, f"Delegator event must have '{key}' field"


@pytest.mark.vcr()
def test_extra_agents(info_client: Info):
    """Verifies retrieval of agents authorized by the user."""
    response: List[Dict[str, Any]] = info_client.extra_agents(user="0xd42f2bB0e06455eDB652e27b7374FC2bDa8448ee")
    assert isinstance(response, list), "The response should be a list"
    
    if response:
        assert len(response) > 0, "The response should contain at least one agent"
        agent = response[0]
        for key in ["name", "address", "validUntil"]:
            assert key in agent, f"Each agent should have a '{key}' field"
