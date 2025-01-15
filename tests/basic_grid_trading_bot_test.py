import pytest
from unittest.mock import Mock, patch

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

class TestBasicGridTradingBot:
    @pytest.fixture
    def mock_setup(self):
        with patch('examples.example_utils.setup') as mock:
            mock.return_value = (
                "0x123...789",  # address
                Mock(spec=Info),  # info
                Mock(spec=Exchange)  # exchange
            )
            yield mock

    @pytest.fixture
    def bot(self, mock_setup):
        from examples.basic_grid_trading_bot import GridTradingBot
        return GridTradingBot(
            coin="ETH",
            grid_size=5,
            price_spacing_percent=0.01,
            order_size=0.1
        )

    def test_initialization(self, bot):
        assert bot.coin == "ETH"
        assert bot.grid_size == 5
        assert bot.price_spacing == 0.01
        assert bot.order_size == 0.1
        assert isinstance(bot.active_orders, dict)

    def test_get_mid_price(self, bot):
        # Mock the l2_snapshot response
        bot.info.l2_snapshot.return_value = {
            "levels": [
                [{"px": "1900"}],  # Best bid
                [{"px": "2100"}]   # Best ask
            ]
        }
        
        mid_price = bot.get_mid_price()
        assert mid_price == 2000.0
        bot.info.l2_snapshot.assert_called_once_with("ETH")

    def test_create_grid(self, bot):
        # Mock the get_mid_price method
        bot.get_mid_price = Mock(return_value=2000.0)
        
        # Mock successful order placement with incrementing OIDs
        oid_counter = 100
        def mock_order(*args, **kwargs):
            nonlocal oid_counter
            oid_counter += 1
            return {
                "status": "ok",
                "response": {
                    "data": {
                        "statuses": [{
                            "resting": {
                                "oid": oid_counter
                            }
                        }]
                    }
                }
            }
        
        bot.exchange.order = Mock(side_effect=mock_order)
        
        bot.create_grid()
        
        # Should create grid_size * 2 orders (buys and sells)
        assert bot.exchange.order.call_count == bot.grid_size * 2
        
        # Verify active orders were tracked
        assert len(bot.active_orders) == bot.grid_size * 2

    def test_check_and_replace_filled_orders(self, bot):
        # Setup mock active orders
        bot.active_orders = {
            123: {"price": 1900.0, "is_buy": True},
            456: {"price": 2100.0, "is_buy": False}
        }

        # Mock order status checks
        def mock_query_order(address, oid):
            return {"status": "filled" if oid == 123 else "active"}
        
        bot.info.query_order_by_oid = Mock(side_effect=mock_query_order)

        # Mock new order placement with a new OID
        bot.exchange.order.return_value = {
            "status": "ok",
            "response": {
                "data": {
                    "statuses": [{
                        "resting": {
                            "oid": 789
                        }
                    }]
                }
            }
        }

        bot.check_and_replace_filled_orders()

        # Verify filled order was replaced
        assert 123 not in bot.active_orders
        assert 456 in bot.active_orders
        assert 789 in bot.active_orders

    def test_error_handling_in_create_grid(self, bot):
        bot.get_mid_price = Mock(return_value=2000.0)
        
        # Mock failed order placement
        bot.exchange.order.return_value = {
            "status": "error",
            "message": "Insufficient funds"
        }

        bot.create_grid()
        
        # Should attempt to create orders but not track them
        assert bot.exchange.order.call_count == bot.grid_size * 2
        assert len(bot.active_orders) == 0

    @pytest.mark.parametrize("price_spacing,grid_size", [
        (-0.01, 5),   # Negative spacing
        (0, 5),       # Zero spacing
        (0.01, 0),    # Zero grid size
        (0.01, -1),   # Negative grid size
    ])
    def test_invalid_parameters(self, mock_setup, price_spacing, grid_size):
        from examples.basic_grid_trading_bot import GridTradingBot
        
        with pytest.raises(ValueError):
            GridTradingBot(
                coin="ETH",
                grid_size=grid_size,
                price_spacing_percent=price_spacing,
                order_size=0.1
            )
