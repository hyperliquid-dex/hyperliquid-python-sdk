from enum import Enum
from typing import Optional, Union, Dict, Any, List

from hyperliquid.exchange import Exchange
from hyperliquid.utils.types import BuilderInfo, Cloid

class TimeInForce(Enum):
    """Time in force options for orders"""
    GTC = "Gtc"  # Good till cancelled
    IOC = "Ioc"  # Immediate or cancel
    ALO = "Alo"  # Add liquidity only (post-only)

class OrderSide(Enum):
    """Order side (buy/sell)"""
    BUY = True
    SELL = False

class TriggerType(Enum):
    """Trigger order types"""
    TAKE_PROFIT = "tp"
    STOP_LOSS = "sl"

class Order:
    """
    A wrapper class for Hyperliquid exchange order methods that provides a simpler interface.
    
    Reference: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint
    """
    
    def __init__(self, exchange: Exchange):
        """
        Initialize the Order wrapper with a Hyperliquid exchange instance.
        
        Args:
            exchange (Exchange): An initialized Hyperliquid exchange instance
        """
        self.exchange = exchange
        self.info = exchange.info

    def _get_asset_price(self, asset: str) -> float:
        """Get current mid price for an asset"""
        coin = self.info.name_to_coin[asset]
        return float(self.info.all_mids()[coin])

    def _calculate_quantity(self, asset: str, notional_amount: float, price: Optional[float] = None) -> float:
        """Calculate asset quantity from notional amount"""
        if price is None:
            price = self._get_asset_price(asset)
        return notional_amount / price

    def _create_order_type(self, tif: TimeInForce) -> Dict:
        """Create order type dictionary"""
        return {"limit": {"tif": tif.value}}

    def market_order(
        self,
        asset: str,
        side: OrderSide,
        quantity: float,
        slippage: float = Exchange.DEFAULT_SLIPPAGE,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None
    ) -> Any:
        """
        Place a market order using asset quantity.

        Args:
            asset: Asset symbol (e.g. "ETH", "BTC")
            side: OrderSide.BUY or OrderSide.SELL
            quantity: Quantity of asset
            slippage: Maximum allowed slippage (default 5%)
            reduce_only: Whether order reduces position only
            cloid: Optional client order ID
            builder: Optional builder information

        Returns:
            Exchange response
        """
        return self.exchange.market_open(
            asset, side.value, quantity, None, slippage, cloid, builder
        )

    def market_order_notional(
        self,
        asset: str,
        side: OrderSide,
        notional_amount: float,
        slippage: float = Exchange.DEFAULT_SLIPPAGE,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None
    ) -> Any:
        """
        Place a market order using notional amount (USD).

        Args:
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            notional_amount: Amount in USD
            slippage: Maximum allowed slippage (default 5%)
            reduce_only: Whether order reduces position only
            cloid: Optional client order ID
            builder: Optional builder information

        Returns:
            Exchange response
        """
        quantity = self._calculate_quantity(asset, notional_amount)
        return self.market_order(
            asset, side, quantity, slippage, reduce_only, cloid, builder
        )

    def limit_order(
        self,
        asset: str,
        side: OrderSide,
        quantity: float,
        price: float,
        tif: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None
    ) -> Any:
        """
        Place a limit order using asset quantity.

        Args:
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            quantity: Quantity of asset
            price: Limit price
            tif: Time in force (GTC/IOC/ALO)
            reduce_only: Whether order reduces position only
            cloid: Optional client order ID
            builder: Optional builder information

        Returns:
            Exchange response
        """
        order_type = self._create_order_type(tif)
        return self.exchange.order(
            asset, side.value, quantity, price, order_type, reduce_only, cloid, builder
        )

    def limit_order_notional(
        self,
        asset: str,
        side: OrderSide,
        notional_amount: float,
        price: float,
        tif: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None
    ) -> Any:
        """
        Place a limit order using notional amount (USD).

        Args:
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            notional_amount: Amount in USD
            price: Limit price
            tif: Time in force (GTC/IOC/ALO)
            reduce_only: Whether order reduces position only
            cloid: Optional client order ID
            builder: Optional builder information

        Returns:
            Exchange response
        """
        quantity = self._calculate_quantity(asset, notional_amount, price)
        return self.limit_order(
            asset, side, quantity, price, tif, reduce_only, cloid, builder
        )

    def cancel_order(self, asset: str, oid: int) -> Any:
        """Cancel an order by order ID"""
        return self.exchange.cancel(asset, oid)

    def cancel_order_by_cloid(self, asset: str, cloid: Cloid) -> Any:
        """Cancel an order by client order ID"""
        return self.exchange.cancel_by_cloid(asset, cloid)

    def modify_order(
        self,
        oid_or_cloid: Union[int, Cloid],
        asset: str,
        side: OrderSide,
        quantity: float,
        price: float,
        tif: TimeInForce = TimeInForce.GTC,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None
    ) -> Any:
        """
        Modify an existing order.

        Args:
            oid_or_cloid: Order ID or client order ID to modify
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            quantity: New quantity
            price: New price
            tif: Time in force (GTC/IOC/ALO)
            reduce_only: Whether order reduces position only
            cloid: Optional new client order ID

        Returns:
            Exchange response
        """
        order_type = self._create_order_type(tif)
        return self.exchange.modify_order(
            oid_or_cloid, asset, side.value, quantity, price, order_type, reduce_only, cloid
        ) 

    def stop_loss(
        self,
        asset: str,
        side: OrderSide,
        quantity: float,
        trigger_price: float,
        is_market: bool = True,
        limit_price: Optional[float] = None,
        reduce_only: bool = True,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        """
        Place a stop loss order.
        
        Args:
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            quantity: Quantity of asset
            trigger_price: Price at which the stop loss triggers
            is_market: If True, executes as market order when triggered
            limit_price: Optional limit price for stop-limit orders
            reduce_only: Whether order reduces position only
            cloid: Optional client order ID
        """
        order_type = {
            "trigger": {
                "triggerPx": trigger_price,
                "isMarket": is_market,
                "tpsl": "sl"
            }
        }
        
        # For stop-limit orders, use the limit price, otherwise use trigger price
        exec_price = limit_price if limit_price is not None else trigger_price
        
        return self.exchange.order(
            asset, side.value, quantity, exec_price, 
            order_type, reduce_only, cloid
        )

    def take_profit(
        self,
        asset: str,
        side: OrderSide,
        quantity: float,
        trigger_price: float,
        is_market: bool = True,
        limit_price: Optional[float] = None,
        reduce_only: bool = True,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        """
        Place a take profit order.
        
        Args:
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            quantity: Quantity of asset
            trigger_price: Price at which the take profit triggers
            is_market: If True, executes as market order when triggered
            limit_price: Optional limit price for limit orders
            reduce_only: Whether order reduces position only
            cloid: Optional client order ID
        """
        order_type = {
            "trigger": {
                "triggerPx": trigger_price,
                "isMarket": is_market,
                "tpsl": "tp"
            }
        }
        
        exec_price = limit_price if limit_price is not None else trigger_price
        
        return self.exchange.order(
            asset, side.value, quantity, exec_price, 
            order_type, reduce_only, cloid
        )

    def bracket_order(
        self,
        asset: str,
        side: OrderSide,
        quantity: float,
        entry_price: float,
        stop_loss_price: float,
        take_profit_price: float,
        entry_type: TimeInForce = TimeInForce.GTC,
        is_market_tp_sl: bool = True,
        cloid: Optional[Cloid] = None,
    ) -> List[Any]:
        """
        Place a bracket order (entry + stop loss + take profit).
        
        Args:
            asset: Asset symbol
            side: OrderSide.BUY or OrderSide.SELL
            quantity: Quantity of asset
            entry_price: Entry order price
            stop_loss_price: Stop loss trigger price
            take_profit_price: Take profit trigger price
            entry_type: Time in force for entry order
            is_market_tp_sl: If True, TP/SL execute as market orders
            cloid: Optional client order ID base (will be incremented)
        """
        results = []
        
        # Entry order
        entry_order_type = self._create_order_type(entry_type)
        entry_cloid = Cloid.from_int(int(cloid.to_raw(), 16)) if cloid else None
        
        entry = self.exchange.order(
            asset, side.value, quantity, entry_price,
            entry_order_type, False, entry_cloid
        )
        results.append(entry)

        # Only place TP/SL if entry order is accepted
        if entry["status"] == "ok":
            # Stop loss (opposite side of entry)
            sl_cloid = Cloid.from_int(int(entry_cloid.to_raw(), 16) + 1) if entry_cloid else None
            opposite_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
            sl = self.stop_loss(
                asset, opposite_side, quantity, stop_loss_price,
                is_market_tp_sl, None, True, sl_cloid
            )
            results.append(sl)

            # Take profit (opposite side of entry)
            tp_cloid = Cloid.from_int(int(entry_cloid.to_raw(), 16) + 2) if entry_cloid else None
            tp = self.take_profit(
                asset, opposite_side, quantity, take_profit_price,
                is_market_tp_sl, None, True, tp_cloid
            )
            results.append(tp)

        return results 
