import example_utils

from hyperliquid.utils import constants
from hyperliquid.utils.types import Cloid
from order import Order, OrderSide, TimeInForce


def main():
    # Setup exchange connection
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)

    # Create order wrapper
    order = Order(exchange)

    # Example 1: Simple Market Orders
    print("\n=== Market Order Examples ===")

    # Market buy 0.1 ETH
    result = order.market_order(asset="ETH", side=OrderSide.BUY, quantity=0.1, slippage=0.01)  # 1% max slippage
    print(f"Market Buy Result: {result}")

    # Market sell $1000 worth of BTC
    result = order.market_order_notional(asset="BTC", side=OrderSide.SELL, notional_amount=1000)  # USD amount
    print(f"Market Sell (Notional) Result: {result}")

    # Example 2: Limit Orders
    print("\n=== Limit Order Examples ===")

    # Limit buy 0.1 ETH at $1800
    result = order.limit_order(
        asset="ETH", side=OrderSide.BUY, quantity=0.1, price=1800, tif=TimeInForce.GTC  # Good till cancelled
    )
    print(f"Limit Buy Result: {result}")

    # Post-only limit sell $2000 worth of ETH at $1900
    result = order.limit_order_notional(
        asset="ETH",
        side=OrderSide.SELL,
        notional_amount=2000,
        price=1900,
        tif=TimeInForce.ALO,  # Add liquidity only (post-only)
    )
    print(f"Post-only Limit Sell Result: {result}")

    # Example 3: Stop Loss Orders
    print("\n=== Stop Loss Examples ===")

    # Market stop loss for long position
    result = order.stop_loss(
        asset="ETH",
        side=OrderSide.SELL,
        quantity=0.1,
        trigger_price=1750,
        is_market=True,  # Market order when triggered
    )
    print(f"Market Stop Loss Result: {result}")

    # Limit stop loss for short position
    result = order.stop_loss(
        asset="BTC",
        side=OrderSide.BUY,
        quantity=0.05,
        trigger_price=45000,
        is_market=False,
        limit_price=45100,  # Limit price when triggered
    )
    print(f"Limit Stop Loss Result: {result}")

    # Example 4: Take Profit Orders
    print("\n=== Take Profit Examples ===")

    # Market take profit
    result = order.take_profit(asset="ETH", side=OrderSide.SELL, quantity=0.1, trigger_price=2000, is_market=True)
    print(f"Market Take Profit Result: {result}")

    # Example 5: Bracket Orders
    print("\n=== Bracket Order Example ===")

    # Entry + Stop Loss + Take Profit
    cloid = Cloid.from_int(1)  # Optional client order ID
    results = order.bracket_order(
        asset="ETH",
        side=OrderSide.BUY,
        quantity=0.1,
        entry_price=1800,
        stop_loss_price=1750,
        take_profit_price=1900,
        entry_type=TimeInForce.GTC,
        is_market_tp_sl=True,
        cloid=cloid,
    )
    print(f"Bracket Order Results:")
    print(f"Entry Order: {results[0]}")
    if len(results) > 1:
        print(f"Stop Loss Order: {results[1]}")
        print(f"Take Profit Order: {results[2]}")

    # Example 6: Order Modification
    print("\n=== Order Modification Example ===")

    # Place a limit order first
    order_result = order.limit_order(
        asset="ETH", side=OrderSide.BUY, quantity=0.1, price=1750, tif=TimeInForce.GTC, cloid=Cloid.from_int(2)
    )

    # Modify the order if it's resting
    if order_result["status"] == "ok":
        status = order_result["response"]["data"]["statuses"][0]
        if "resting" in status:
            oid = status["resting"]["oid"]
            # Modify order price and quantity
            modify_result = order.modify_order(
                oid_or_cloid=oid,
                asset="ETH",
                side=OrderSide.BUY,
                quantity=0.15,  # New quantity
                price=1760,  # New price
                tif=TimeInForce.GTC,
            )
            print(f"Order Modification Result: {modify_result}")


if __name__ == "__main__":
    main()
