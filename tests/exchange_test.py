import pytest
import eth_account

from hyperliquid.exchange import Exchange
from hyperliquid.utils.types import Meta, SpotMeta

TEST_META: Meta = {"universe": []}
TEST_SPOT_META: SpotMeta = {"universe": [], "tokens": []}

# Create a test wallet using a deterministic private key
TEST_PRIVATE_KEY = "0x0123456789012345678901234567890123456789012345678901234567890123"
TEST_WALLET = eth_account.Account.from_key(TEST_PRIVATE_KEY)


def test_exchange_default_base_url():
    """Test Exchange with default base URL behavior (backward compatibility)"""
    exchange = Exchange(
        wallet=TEST_WALLET,
        base_url="https://api.hyperliquid.xyz",
        meta=TEST_META,
        spot_meta=TEST_SPOT_META
    )
    
    # All components should use the same base URL
    assert exchange.base_url == "https://api.hyperliquid.xyz"
    assert exchange.info.base_url == "https://api.hyperliquid.xyz"
    # WebSocket URL is constructed by replacing http with ws
    if exchange.info.ws_manager:
        assert "wss://api.hyperliquid.xyz/ws" in exchange.info.ws_manager.ws.url


def test_exchange_separate_base_urls():
    """Test Exchange with separate base URLs for each endpoint"""
    exchange = Exchange(
        wallet=TEST_WALLET,
        base_url="https://api.hyperliquid.xyz",           # Fallback default
        info_base_url="https://info-provider.com",        # For /info
        exchange_base_url="https://exchange-provider.com", # For /exchange
        ws_base_url="wss://ws-provider.com",             # For /ws
        meta=TEST_META,
        spot_meta=TEST_SPOT_META
    )
    
    # Each component should use its specific URL
    assert exchange.base_url == "https://exchange-provider.com"
    assert exchange.info.base_url == "https://info-provider.com"
    if exchange.info.ws_manager:
        assert "wss://ws-provider.com/ws" in exchange.info.ws_manager.ws.url


def test_exchange_partial_url_specification():
    """Test Exchange with partial URL specification (fallback behavior)"""
    exchange = Exchange(
        wallet=TEST_WALLET,
        base_url="https://api.hyperliquid.xyz",
        info_base_url="https://info-provider.com",
        # exchange_base_url not specified - should use base_url
        # ws_base_url not specified - should use info_base_url
        meta=TEST_META,
        spot_meta=TEST_SPOT_META
    )
    
    # Exchange should use base_url (fallback)
    assert exchange.base_url == "https://api.hyperliquid.xyz"
    # Info should use info_base_url
    assert exchange.info.base_url == "https://info-provider.com"
    # WebSocket should use info_base_url (fallback)
    if exchange.info.ws_manager:
        assert "wss://info-provider.com/ws" in exchange.info.ws_manager.ws.url


def test_exchange_only_exchange_url_specified():
    """Test Exchange with only exchange_base_url specified"""
    exchange = Exchange(
        wallet=TEST_WALLET,
        base_url="https://api.hyperliquid.xyz",
        exchange_base_url="https://exchange-provider.com",
        # info_base_url not specified - should use base_url
        # ws_base_url not specified - should use info_base_url (which is base_url)
        meta=TEST_META,
        spot_meta=TEST_SPOT_META
    )
    
    # Exchange should use exchange_base_url
    assert exchange.base_url == "https://exchange-provider.com"
    # Info should use base_url (fallback)
    assert exchange.info.base_url == "https://api.hyperliquid.xyz"
    # WebSocket should use base_url (fallback chain)
    if exchange.info.ws_manager:
        assert "wss://api.hyperliquid.xyz/ws" in exchange.info.ws_manager.ws.url


def test_exchange_only_ws_url_specified():
    """Test Exchange with only ws_base_url specified"""
    exchange = Exchange(
        wallet=TEST_WALLET,
        base_url="https://api.hyperliquid.xyz",
        ws_base_url="wss://ws-provider.com",
        # info_base_url not specified - should use base_url
        # exchange_base_url not specified - should use base_url
        meta=TEST_META,
        spot_meta=TEST_SPOT_META
    )
    
    # Exchange should use base_url (fallback)
    assert exchange.base_url == "https://api.hyperliquid.xyz"
    # Info should use base_url (fallback)
    assert exchange.info.base_url == "https://api.hyperliquid.xyz"
    # WebSocket should use ws_base_url
    if exchange.info.ws_manager:
        assert "wss://ws-provider.com/ws" in exchange.info.ws_manager.ws.url


def test_exchange_skip_websocket():
    """Test Exchange creation with WebSocket disabled"""
    exchange = Exchange(
        wallet=TEST_WALLET,
        base_url="https://api.hyperliquid.xyz",
        info_base_url="https://info-provider.com",
        exchange_base_url="https://exchange-provider.com",
        ws_base_url="wss://ws-provider.com",
        meta=TEST_META,
        spot_meta=TEST_SPOT_META
    )
    
    # Manually create info with skip_ws=True to test the parameter passing
    from hyperliquid.info import Info
    info_no_ws = Info(
        base_url="https://info-provider.com",
        skip_ws=True,
        meta=TEST_META,
        spot_meta=TEST_SPOT_META,
        ws_base_url="wss://ws-provider.com"
    )
    
    assert info_no_ws.base_url == "https://info-provider.com"
    assert info_no_ws.ws_manager is None