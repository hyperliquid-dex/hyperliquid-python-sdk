import pytest
from eth_account import Account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.types import Meta, SpotMeta

TEST_META: Meta = {"universe": []}
TEST_SPOT_META: SpotMeta = {"universe": [], "tokens": []}

@pytest.fixture
def wallet() -> LocalAccount:
    """Create a test wallet"""
    return Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")

@pytest.fixture
def exchange(wallet):
    """Fixture that provides an Exchange instance"""
    return Exchange(wallet)

def test_initializer(exchange, wallet):
    """Test that the Exchange class initializes with correct default values"""
    assert exchange.base_url == MAINNET_API_URL
    assert exchange.wallet == wallet
    assert exchange.vault_address is None
    assert exchange.account_address is None
    assert exchange.info is not None

def test_initializer_with_custom_values(wallet):
    """Test that the Exchange class can be initialized with custom values"""
    custom_url = "https://custom.api.url"
    vault_address = "0x1234567890123456789012345678901234567890"
    account_address = "0x0987654321098765432109876543210987654321"
    
    exchange = Exchange(
        wallet=wallet,
        base_url=custom_url,
        meta=TEST_META,
        vault_address=vault_address,
        account_address=account_address,
        spot_meta=TEST_SPOT_META
    )
    
    assert exchange.base_url == custom_url
    assert exchange.wallet == wallet
    assert exchange.vault_address == vault_address
    assert exchange.account_address == account_address
    assert exchange.info is not None
