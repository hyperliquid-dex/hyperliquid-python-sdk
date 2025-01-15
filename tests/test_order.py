from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from hyperliquid.exchange import Exchange
from hyperliquid.utils.types import Cloid
from order import Order, OrderSide, TimeInForce, TriggerType


@pytest.fixture
def mock_exchange():
    exchange = Mock(spec=Exchange)
    # Mock the info attribute and its methods
    exchange.info = Mock()
    exchange.info.name_to_coin = {"ETH": "1", "BTC": "0"}
    exchange.info.all_mids = lambda: {"1": "1800.0", "0": "45000.0"}
    return exchange


@pytest.fixture
def order_wrapper(mock_exchange):
    return Order(mock_exchange)


class TestOrderWrapper:
    def test_market_order_buy(self, order_wrapper, mock_exchange):
        """Test market buy order placement"""
        order_wrapper.market_order("ETH", OrderSide.BUY, 1.0)

        mock_exchange.market_open.assert_called_once_with("ETH", True, 1.0, None, Exchange.DEFAULT_SLIPPAGE, None, None)

    def test_market_order_sell(self, order_wrapper, mock_exchange):
        """Test market sell order placement"""
        order_wrapper.market_order("ETH", OrderSide.SELL, 1.0, slippage=0.01)

        mock_exchange.market_open.assert_called_once_with("ETH", False, 1.0, None, 0.01, None, None)

    def test_market_order_notional_buy(self, order_wrapper, mock_exchange):
        """Test market buy order with notional amount"""
        # $1800 worth of ETH at current price of $1800 = 1.0 ETH
        order_wrapper.market_order_notional("ETH", OrderSide.BUY, 1800)

        mock_exchange.market_open.assert_called_once_with("ETH", True, 1.0, None, Exchange.DEFAULT_SLIPPAGE, None, None)

    def test_limit_order_buy(self, order_wrapper, mock_exchange):
        """Test limit buy order placement"""
        order_wrapper.limit_order("ETH", OrderSide.BUY, 1.0, 1750.0, TimeInForce.GTC)

        mock_exchange.order.assert_called_once_with(
            "ETH", True, 1.0, 1750.0, {"limit": {"tif": "Gtc"}}, False, None, None
        )

    def test_limit_order_sell_post_only(self, order_wrapper, mock_exchange):
        """Test post-only limit sell order"""
        order_wrapper.limit_order("ETH", OrderSide.SELL, 1.0, 1850.0, TimeInForce.ALO)

        mock_exchange.order.assert_called_once_with(
            "ETH", False, 1.0, 1850.0, {"limit": {"tif": "Alo"}}, False, None, None
        )

    def test_stop_loss_market(self, order_wrapper, mock_exchange):
        """Test market stop loss order"""
        order_wrapper.stop_loss("ETH", OrderSide.SELL, 1.0, 1750.0, is_market=True)

        mock_exchange.order.assert_called_once_with(
            "ETH", False, 1.0, 1750.0, {"trigger": {"triggerPx": 1750.0, "isMarket": True, "tpsl": "sl"}}, True, None
        )

    def test_take_profit_limit(self, order_wrapper, mock_exchange):
        """Test limit take profit order"""
        order_wrapper.take_profit("ETH", OrderSide.SELL, 1.0, 1900.0, is_market=False, limit_price=1895.0)

        mock_exchange.order.assert_called_once_with(
            "ETH", False, 1.0, 1895.0, {"trigger": {"triggerPx": 1900.0, "isMarket": False, "tpsl": "tp"}}, True, None
        )

    def test_bracket_order(self, order_wrapper, mock_exchange):
        """Test bracket order placement"""
        mock_exchange.order.return_value = {"status": "ok"}
        cloid = Cloid.from_int(1)

        order_wrapper.bracket_order("ETH", OrderSide.BUY, 1.0, 1800.0, 1750.0, 1850.0, TimeInForce.GTC, True, cloid)

        # Should place 3 orders: entry, stop loss, and take profit
        assert mock_exchange.order.call_count == 3

        calls = mock_exchange.order.call_args_list

        # Verify entry order
        assert calls[0][0][0:4] == ("ETH", True, 1.0, 1800.0)
        assert calls[0][0][4] == {"limit": {"tif": "Gtc"}}

        # Verify stop loss order
        assert calls[1][0][0:4] == ("ETH", False, 1.0, 1750.0)
        assert calls[1][0][4]["trigger"]["tpsl"] == "sl"

        # Verify take profit order
        assert calls[2][0][0:4] == ("ETH", False, 1.0, 1850.0)
        assert calls[2][0][4]["trigger"]["tpsl"] == "tp"

    def test_modify_order(self, order_wrapper, mock_exchange):
        """Test order modification"""
        oid = 12345
        order_wrapper.modify_order(oid, "ETH", OrderSide.BUY, 1.0, 1800.0, TimeInForce.GTC)

        mock_exchange.modify_order.assert_called_once_with(
            oid, "ETH", True, 1.0, 1800.0, {"limit": {"tif": "Gtc"}}, False, None
        )

    def test_cancel_order(self, order_wrapper, mock_exchange):
        """Test order cancellation"""
        order_wrapper.cancel_order("ETH", 12345)
        mock_exchange.cancel.assert_called_once_with("ETH", 12345)

    def test_cancel_order_by_cloid(self, order_wrapper, mock_exchange):
        """Test order cancellation by CLOID"""
        cloid = Cloid.from_int(1)
        order_wrapper.cancel_order_by_cloid("ETH", cloid)
        mock_exchange.cancel_by_cloid.assert_called_once_with("ETH", cloid)

    def test_price_calculation(self, order_wrapper):
        """Test internal price calculation methods"""
        eth_price = order_wrapper._get_asset_price("ETH")
        assert eth_price == 1800.0

        quantity = order_wrapper._calculate_quantity("ETH", 1800)
        assert quantity == 1.0

    @pytest.mark.parametrize("side,expected", [(OrderSide.BUY, True), (OrderSide.SELL, False)])
    def test_order_side_conversion(self, order_wrapper, mock_exchange, side, expected):
        """Test order side enum conversion"""
        order_wrapper.market_order("ETH", side, 1.0)
        args = mock_exchange.market_open.call_args[0]
        assert args[1] == expected
