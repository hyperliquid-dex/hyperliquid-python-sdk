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

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_bulk_orders(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test bulk_orders method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1  # Mock name_to_asset to return 1 for any input

    # Test single order
    order_requests = [
        {
            "coin": "ETH",
            "is_buy": True,
            "sz": 1.0,
            "limit_px": 2000.0,
            "order_type": {"limit": {"tif": "Gtc"}},
            "reduce_only": False,
        }
    ]

    response = exchange.bulk_orders(order_requests)
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    assert call_args[0] == exchange.wallet  # wallet
    assert call_args[1]["type"] == "order"  # action
    assert call_args[2] == exchange.vault_address  # vault_address
    assert call_args[3] == 1234567890  # timestamp
    assert call_args[4] == (exchange.base_url == MAINNET_API_URL)  # is_mainnet

    # Verify _post_action was called correctly
    mock_post_action.assert_called_once_with(
        mock_sign.call_args[0][1],  # action
        "test_signature",  # signature
        1234567890  # timestamp
    )

    # Test with builder
    mock_sign.reset_mock()
    mock_post_action.reset_mock()
    
    builder = {"b": "TEST_BUILDER", "r": 0.001}  # Using uppercase to test lowercasing
    response = exchange.bulk_orders(order_requests, builder)
    
    assert response == {"status": "ok"}
    
    # Verify builder was included in the action
    call_args = mock_sign.call_args[0]
    action = call_args[1]  # Get the action argument
    assert action["type"] == "order"
    # The builder object should be passed through as is (after lowercase conversion)
    assert action["builder"]["b"] == "test_builder"
    assert action["builder"]["r"] == 0.001

@patch('hyperliquid.exchange.Exchange.bulk_orders')
def test_order(mock_bulk_orders, exchange):
    """Test order method with various scenarios"""
    # Setup
    mock_bulk_orders.return_value = {
        "status": "ok",
        "response": {
            "data": {
                "statuses": [{"resting": {"oid": 123}}]
            }
        }
    }
    exchange.info.name_to_asset = lambda x: 1

    # Test 1: Basic limit order
    response = exchange.order(
        name="ETH",
        is_buy=True,
        sz=1.0,
        limit_px=2000.0,
        order_type={"limit": {"tif": "Gtc"}},
    )
    
    assert response["status"] == "ok"
    assert response["response"]["data"]["statuses"][0]["resting"]["oid"] == 123
    
    mock_bulk_orders.assert_called_once_with(
        [
            {
                "coin": "ETH",
                "is_buy": True,
                "sz": 1.0,
                "limit_px": 2000.0,
                "order_type": {"limit": {"tif": "Gtc"}},
                "reduce_only": False,
            }
        ],
        None
    )

    # Test 2: Order with builder fee
    mock_bulk_orders.reset_mock()
    builder = {"b": "0x8c967E73E7B15087c42A10D344cFf4c96D877f1D", "r": 0.001}
    
    response = exchange.order(
        name="ETH",
        is_buy=True,
        sz=0.05,
        limit_px=2000.0,
        order_type={"limit": {"tif": "Ioc"}},
        builder=builder
    )
    
    assert response["status"] == "ok"
    mock_bulk_orders.assert_called_once()
    call_args = mock_bulk_orders.call_args[0]
    assert call_args[1]["b"].lower() == builder["b"].lower()
    assert call_args[1]["r"] == builder["r"]

    # Test 3: TPSL order
    mock_bulk_orders.reset_mock()
    response = exchange.order(
        name="ETH",
        is_buy=True,
        sz=100,
        limit_px=100,
        order_type={"trigger": {"triggerPx": 103, "isMarket": True, "tpsl": "sl"}},
        reduce_only=True
    )
    
    assert response["status"] == "ok"
    mock_bulk_orders.assert_called_once()
    order_request = mock_bulk_orders.call_args[0][0][0]
    assert order_request["order_type"]["trigger"]["tpsl"] == "sl"
    assert order_request["reduce_only"] is True

    # Test 4: Order with cloid
    mock_bulk_orders.reset_mock()
    cloid = "0x00000000000000000000000000000001"
    
    response = exchange.order(
        name="ETH",
        is_buy=True,
        sz=1.0,
        limit_px=2000.0,
        order_type={"limit": {"tif": "Gtc"}},
        cloid=cloid
    )
    
    assert response["status"] == "ok"
    mock_bulk_orders.assert_called_once()
    order_request = mock_bulk_orders.call_args[0][0][0]
    assert order_request["cloid"] == cloid

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_modify_order(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test modify_order method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    # Test 1: Basic modify order with oid
    oid = 12345
    response = exchange.modify_order(
        oid=oid,
        name="ETH",
        is_buy=True,
        sz=0.1,
        limit_px=1105,
        order_type={"limit": {"tif": "Gtc"}},
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "batchModify"
    assert len(action["modifies"]) == 1
    assert action["modifies"][0]["oid"] == oid
    
    # Test 2: Modify order with cloid
    mock_sign.reset_mock()
    mock_post_action.reset_mock()
    
    from hyperliquid.utils.types import Cloid
    cloid = Cloid.from_str("0x00000000000000000000000000000001")
    new_cloid = Cloid.from_str("0x00000000000000000000000000000002")
    
    response = exchange.modify_order(
        oid=cloid,
        name="ETH",
        is_buy=True,
        sz=0.1,
        limit_px=1105,
        order_type={"limit": {"tif": "Gtc"}},
        reduce_only=True,
        cloid=new_cloid
    )
    
    assert response == {"status": "ok"}
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["modifies"][0]["oid"] == cloid.to_raw()
    assert action["modifies"][0]["order"]["r"] is True  # reduce_only
    assert "c" in action["modifies"][0]["order"]  # cloid in wire format

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_bulk_modify_orders_new(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test bulk_modify_orders_new method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    from hyperliquid.utils.types import Cloid
    cloid1 = Cloid.from_str("0x00000000000000000000000000000001")
    cloid2 = Cloid.from_str("0x00000000000000000000000000000002")

    # Test multiple order modifications
    modify_requests = [
        {
            "oid": 12345,
            "order": {
                "coin": "ETH",
                "is_buy": True,
                "sz": 0.1,
                "limit_px": 1105,
                "order_type": {"limit": {"tif": "Gtc"}},
                "reduce_only": False,
                "cloid": None,
            },
        },
        {
            "oid": cloid1,
            "order": {
                "coin": "BTC",
                "is_buy": False,
                "sz": 1.0,
                "limit_px": 50000,
                "order_type": {"limit": {"tif": "Ioc"}},
                "reduce_only": True,
                "cloid": cloid2,
            },
        },
    ]
    
    response = exchange.bulk_modify_orders_new(modify_requests)
    assert response == {"status": "ok"}
    
    # Verify the action structure
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    
    assert action["type"] == "batchModify"
    assert len(action["modifies"]) == 2
    
    # Verify first modification
    assert action["modifies"][0]["oid"] == 12345
    assert action["modifies"][0]["order"]["s"] == "0.1"  # size as string
    assert action["modifies"][0]["order"]["p"] == "1105"  # price as string
    
    # Verify second modification
    assert action["modifies"][1]["oid"] == cloid1.to_raw()
    assert action["modifies"][1]["order"]["s"] == "1"  # size as string
    assert action["modifies"][1]["order"]["p"] == "50000"  # price as string
    assert action["modifies"][1]["order"]["r"] is True
    assert "c" in action["modifies"][1]["order"]  # cloid in wire format

@patch('hyperliquid.exchange.Exchange.bulk_orders')
def test_market_open(mock_bulk_orders, exchange):
    """Test market_open method"""
    # Setup
    mock_bulk_orders.return_value = {
        "status": "ok",
        "response": {
            "data": {
                "statuses": [{"filled": {"oid": 123, "totalSz": "0.05", "avgPx": "1950.5"}}]
            }
        }
    }
    exchange.info.name_to_asset = lambda x: 1

    # Test 1: Basic market open
    response = exchange.market_open(
        name="ETH",
        is_buy=True,
        sz=0.05,
    )
    
    assert response["status"] == "ok"
    assert response["response"]["data"]["statuses"][0]["filled"]["oid"] == 123
    
    mock_bulk_orders.assert_called_once()
    order_request = mock_bulk_orders.call_args[0][0][0]
    assert order_request["coin"] == "ETH"
    assert order_request["is_buy"] is True
    assert order_request["sz"] == 0.05
    assert order_request["order_type"] == {"limit": {"tif": "Ioc"}}
    assert order_request["reduce_only"] is False
    
    # Test 2: Market open with slippage and builder
    mock_bulk_orders.reset_mock()
    builder = {"b": "0x8c967E73E7B15087c42A10D344cFf4c96D877f1D", "r": 0.001}
    
    response = exchange.market_open(
        name="ETH",
        is_buy=True,
        sz=0.05,
        builder=builder,
        slippage=0.01  # 1% slippage
    )
    
    assert response["status"] == "ok"
    mock_bulk_orders.assert_called_once()
    order_request = mock_bulk_orders.call_args[0][0][0]
    assert order_request["coin"] == "ETH"
    assert order_request["sz"] == 0.05
    assert order_request["order_type"] == {"limit": {"tif": "Ioc"}}
    # Verify builder was passed correctly
    assert mock_bulk_orders.call_args[0][1]["b"].lower() == builder["b"].lower()
    assert mock_bulk_orders.call_args[0][1]["r"] == builder["r"]

@patch('hyperliquid.exchange.Exchange.bulk_orders')
def test_market_close(mock_bulk_orders, exchange):
    """Test market_close method"""
    # Setup
    mock_bulk_orders.return_value = {
        "status": "ok",
        "response": {
            "data": {
                "statuses": [{"filled": {"oid": 123, "totalSz": "0.05", "avgPx": "1950.5"}}]
            }
        }
    }
    exchange.info.name_to_asset = lambda x: 1
    
    # Mock user_state to return a position
    exchange.info.user_state = lambda x: {
        "assetPositions": [
            {
                "position": {
                    "coin": "ETH",
                    "szi": "0.05",
                    "entryPx": "2000",
                    "positionValue": "100"
                }
            }
        ]
    }

    # Test 1: Basic market close
    response = exchange.market_close("ETH")
    
    assert response["status"] == "ok"
    assert response["response"]["data"]["statuses"][0]["filled"]["oid"] == 123
    
    mock_bulk_orders.assert_called_once()
    order_request = mock_bulk_orders.call_args[0][0][0]
    assert order_request["coin"] == "ETH"
    assert order_request["sz"] == 0.05
    assert order_request["order_type"] == {"limit": {"tif": "Ioc"}}
    assert order_request["reduce_only"] is True
    
    # Test 2: Market close with slippage and builder
    mock_bulk_orders.reset_mock()
    builder = {"b": "0x8c967E73E7B15087c42A10D344cFf4c96D877f1D", "r": 0.001}
    
    response = exchange.market_close(
        coin="ETH",
        builder=builder,
        slippage=0.01  # 1% slippage
    )
    
    assert response["status"] == "ok"
    mock_bulk_orders.assert_called_once()
    order_request = mock_bulk_orders.call_args[0][0][0]
    assert order_request["coin"] == "ETH"
    assert order_request["sz"] == 0.05
    assert order_request["order_type"] == {"limit": {"tif": "Ioc"}}
    assert order_request["reduce_only"] is True
    # Verify builder was passed correctly
    assert mock_bulk_orders.call_args[0][1]["b"].lower() == builder["b"].lower()
    assert mock_bulk_orders.call_args[0][1]["r"] == builder["r"]

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_cancel(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test cancel method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    # Test basic cancel
    response = exchange.cancel("ETH", 12345)
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "cancel"
    assert len(action["cancels"]) == 1
    assert action["cancels"][0]["a"] == 1  # asset
    assert action["cancels"][0]["o"] == 12345  # oid

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_cancel_by_cloid(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test cancel_by_cloid method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    from hyperliquid.utils.types import Cloid
    cloid = Cloid.from_str("0x00000000000000000000000000000001")

    # Test cancel by cloid
    response = exchange.cancel_by_cloid("ETH", cloid)
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "cancelByCloid"
    assert len(action["cancels"]) == 1
    assert action["cancels"][0]["asset"] == 1
    assert action["cancels"][0]["cloid"] == cloid.to_raw()

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_bulk_cancel(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test bulk_cancel method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    # Test multiple cancels
    cancel_requests = [
        {"coin": "ETH", "oid": 12345},
        {"coin": "BTC", "oid": 67890}
    ]
    
    response = exchange.bulk_cancel(cancel_requests)
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "cancel"
    assert len(action["cancels"]) == 2
    assert action["cancels"][0]["a"] == 1
    assert action["cancels"][0]["o"] == 12345
    assert action["cancels"][1]["a"] == 1
    assert action["cancels"][1]["o"] == 67890

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_bulk_cancel_by_cloid(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test bulk_cancel_by_cloid method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    from hyperliquid.utils.types import Cloid
    cloid1 = Cloid.from_str("0x00000000000000000000000000000001")
    cloid2 = Cloid.from_str("0x00000000000000000000000000000002")

    # Test multiple cancels by cloid
    cancel_requests = [
        {"coin": "ETH", "cloid": cloid1},
        {"coin": "BTC", "cloid": cloid2}
    ]
    
    response = exchange.bulk_cancel_by_cloid(cancel_requests)
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "cancelByCloid"
    assert len(action["cancels"]) == 2
    assert action["cancels"][0]["asset"] == 1
    assert action["cancels"][0]["cloid"] == cloid1.to_raw()
    assert action["cancels"][1]["asset"] == 1
    assert action["cancels"][1]["cloid"] == cloid2.to_raw()

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_schedule_cancel(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test schedule_cancel method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test 1: Basic schedule cancel without time (uses current timestamp)
    response = exchange.schedule_cancel()
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "scheduleCancel"
    assert "time" not in action  # No specific time provided
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature
    
    # Test 2: Schedule cancel with specific time
    mock_sign.reset_mock()
    mock_post_action.reset_mock()
    
    cancel_time = 1234567890 + 10000  # 10 seconds from now
    response = exchange.schedule_cancel(cancel_time)
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "scheduleCancel"
    assert action["time"] == cancel_time
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_update_leverage(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test update_leverage method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    # Test 1: Update leverage with default cross margin
    response = exchange.update_leverage(leverage=10, name="ETH")
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "updateLeverage"
    assert action["asset"] == 1
    assert action["leverage"] == 10
    assert action["isCross"] is True
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature
    
    # Test 2: Update leverage with isolated margin
    mock_sign.reset_mock()
    mock_post_action.reset_mock()
    
    response = exchange.update_leverage(
        leverage=5,
        name="BTC",
        is_cross=False
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "updateLeverage"
    assert action["asset"] == 1
    assert action["leverage"] == 5
    assert action["isCross"] is False
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_update_isolated_margin(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test update_isolated_margin method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}
    exchange.info.name_to_asset = lambda x: 1

    # Test: Update isolated margin
    response = exchange.update_isolated_margin(
        amount=1000.0,
        name="ETH"
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "updateIsolatedMargin"
    assert action["asset"] == 1
    assert action["isBuy"] is True  # isBuy is always True in the implementation
    assert "ntli" in action  # ntli (notional) should be present
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_set_referrer(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test set_referrer method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test setting referrer code
    response = exchange.set_referrer("ASDFASDF")
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "setReferrer"
    assert action["code"] == "ASDFASDF"
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_create_sub_account(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test create_sub_account method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test creating sub account
    response = exchange.create_sub_account("example")
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "createSubAccount"
    assert action["name"] == "example"
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature

@patch('hyperliquid.exchange.sign_usd_class_transfer_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_usd_class_transfer(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test usd_class_transfer method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test 1: Basic transfer without vault address
    response = exchange.usd_class_transfer(amount=1000.0, to_perp=True)
    
    assert response == {"status": "ok"}
    
    # Verify sign_usd_class_transfer_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "usdClassTransfer"
    assert action["amount"] == "1000.0"
    assert action["toPerp"] is True
    assert action["nonce"] == 1234567890
    
    # Test 2: Transfer with vault address
    mock_sign.reset_mock()
    mock_post_action.reset_mock()
    exchange.vault_address = "0x1234"
    
    response = exchange.usd_class_transfer(amount=500.5, to_perp=False)
    
    assert response == {"status": "ok"}
    
    # Verify sign_usd_class_transfer_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "usdClassTransfer"
    assert action["amount"] == "500.5 subaccount:0x1234"
    assert action["toPerp"] is False
    assert action["nonce"] == 1234567890

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_sub_account_transfer(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test sub_account_transfer method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test deposit to sub account
    sub_account = "0x1d9470d4b963f552e6f671a81619d395877bf409"
    response = exchange.sub_account_transfer(
        sub_account_user=sub_account,
        is_deposit=True,
        usd=1000
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "subAccountTransfer"
    assert action["subAccountUser"] == sub_account
    assert action["isDeposit"] is True
    assert action["usd"] == 1000
    
    # Test withdrawal from sub account
    mock_sign.reset_mock()
    mock_post_action.reset_mock()
    
    response = exchange.sub_account_transfer(
        sub_account_user=sub_account,
        is_deposit=False,
        usd=500
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "subAccountTransfer"
    assert action["subAccountUser"] == sub_account
    assert action["isDeposit"] is False
    assert action["usd"] == 500

@patch('hyperliquid.exchange.sign_l1_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_vault_usd_transfer(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test vault_usd_transfer method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test vault transfer
    vault_address = "0xa15099a30bbf2e68942d6f4c43d70d04faeab0a0"
    response = exchange.vault_usd_transfer(
        vault_address=vault_address,
        is_deposit=True,
        usd=5_000_000
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_l1_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    action = call_args[1]
    assert action["type"] == "vaultTransfer"
    assert action["vaultAddress"] == vault_address
    assert action["isDeposit"] is True
    assert action["usd"] == 5_000_000
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    assert call_args[1] == "test_signature"  # signature

@patch('hyperliquid.exchange.sign_usd_transfer_action')
@patch('hyperliquid.exchange.get_timestamp_ms')
@patch('hyperliquid.exchange.Exchange._post_action')
def test_usd_transfer(mock_post_action, mock_timestamp, mock_sign, exchange):
    """Test usd_transfer method"""
    # Setup
    mock_timestamp.return_value = 1234567890
    mock_sign.return_value = "test_signature"
    mock_post_action.return_value = {"status": "ok"}

    # Test USD transfer
    destination = "0x5e9ee1089755c3435139848e47e6635505d5a13a"
    response = exchange.usd_transfer(
        destination=destination,
        amount=1000.0
    )
    
    assert response == {"status": "ok"}
    
    # Verify sign_usd_transfer_action was called correctly
    mock_sign.assert_called_once()
    call_args = mock_sign.call_args[0]
    message = call_args[1]
    assert message["destination"] == destination
    assert message["amount"] == "1000.0"
    assert message["time"] == 1234567890
    
    # Verify _post_action was called correctly
    mock_post_action.assert_called_once()
    call_args = mock_post_action.call_args[0]
    action = call_args[0]
    assert action["type"] == "usdSend"  # Corrected action type
    assert action["destination"] == destination
    assert action["amount"] == "1000.0"
    assert action["time"] == 1234567890
