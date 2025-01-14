import pytest
from eth_account import Account
from eth_account.signers.local import LocalAccount
from unittest.mock import Mock, patch

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

@patch('hyperliquid.api.API.post')
def test_post_action(mock_post, exchange):
    """Test _post_action method"""
    # Setup
    mock_post.return_value = {"status": "ok"}
    action = {"type": "someAction", "data": "test"}
    signature = "test_signature"
    nonce = 123456789

    # Test with regular action
    response = exchange._post_action(action, signature, nonce)
    mock_post.assert_called_once_with(
        "/exchange",
        {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": None
        }
    )
    assert response == {"status": "ok"}

    # Test with vault address
    mock_post.reset_mock()
    exchange.vault_address = "0x1234"
    response = exchange._post_action(action, signature, nonce)
    mock_post.assert_called_once_with(
        "/exchange",
        {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": "0x1234"
        }
    )

    # Test with usdClassTransfer action
    mock_post.reset_mock()
    action["type"] = "usdClassTransfer"
    response = exchange._post_action(action, signature, nonce)
    mock_post.assert_called_once_with(
        "/exchange",
        {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": None
        }
    )

@patch('hyperliquid.info.Info.all_mids')
def test_slippage_price_perp(mock_all_mids, exchange):
    """Test _slippage_price method for perpetual contracts"""
    # Setup
    mock_all_mids.return_value = {"ETH": "2000.0"}
    exchange.info.name_to_coin = {"ETH": "ETH"}
    exchange.info.coin_to_asset = {"ETH": 1}  # Asset ID less than 10000 for perp

    # Test buy with default price
    price = exchange._slippage_price("ETH", True, 0.05)  # 5% slippage
    assert price == 2100.0  # 2000 * (1 + 0.05)

    # Test sell with default price
    price = exchange._slippage_price("ETH", False, 0.05)
    assert price == 1900.0  # 2000 * (1 - 0.05)

    # Test with custom price
    price = exchange._slippage_price("ETH", True, 0.05, 1000.0)
    assert price == 1050.0  # 1000 * (1 + 0.05)

@patch('hyperliquid.info.Info.all_mids')
def test_slippage_price_spot(mock_all_mids, exchange):
    """Test _slippage_price method for spot trading"""
    # Setup
    mock_all_mids.return_value = {"BTC/USDC": "40000.0"}
    exchange.info.name_to_coin = {"BTC/USDC": "BTC/USDC"}
    exchange.info.coin_to_asset = {"BTC/USDC": 10001}  # Asset ID >= 10000 for spot

    # Test buy with default price
    price = exchange._slippage_price("BTC/USDC", True, 0.05)
    assert price == 42000.0  # 40000 * (1 + 0.05)

    # Test sell with default price
    price = exchange._slippage_price("BTC/USDC", False, 0.05)
    assert price == 38000.0  # 40000 * (1 - 0.05)

@patch('hyperliquid.info.Info.all_mids')
def test_slippage_price_rounding(mock_all_mids, exchange):
    """Test price rounding in _slippage_price method"""
    # Setup for perp
    mock_all_mids.return_value = {"ETH": "1999.123456789"}
    exchange.info.name_to_coin = {"ETH": "ETH"}
    exchange.info.coin_to_asset = {"ETH": 1}

    # Test perp rounding (6 decimals)
    price = exchange._slippage_price("ETH", True, 0.05)
    assert str(price).count('.') == 0 or len(str(price).split('.')[1]) <= 6

    # Setup for spot
    mock_all_mids.return_value = {"BTC/USDC": "40000.123456789"}
    exchange.info.name_to_coin = {"BTC/USDC": "BTC/USDC"}
    exchange.info.coin_to_asset = {"BTC/USDC": 10001}

    # Test spot rounding (8 decimals)
    price = exchange._slippage_price("BTC/USDC", True, 0.05)
    assert str(price).count('.') == 0 or len(str(price).split('.')[1]) <= 8
