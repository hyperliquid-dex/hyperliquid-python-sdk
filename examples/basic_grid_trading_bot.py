import time
from typing import Dict, List, Optional
from examples import example_utils
from hyperliquid.utils import constants
from unittest.mock import Mock

class GridTradingBot:
    def __init__(self, coin: str, grid_size: int, price_spacing_percent: float, order_size: float):
        """
        Initialize grid trading bot
        
        Args:
            coin: Trading pair (e.g. "ETH")
            grid_size: Number of buy and sell orders on each side
            price_spacing_percent: Percentage between each grid level
            order_size: Size of each order
            
        Raises:
            ValueError: If grid_size <= 0 or price_spacing_percent <= 0
        """
        if grid_size <= 0:
            raise ValueError("grid_size must be positive")
        if price_spacing_percent <= 0:
            raise ValueError("price_spacing_percent must be positive")
            
        self.address, self.info, self.exchange = example_utils.setup(
            constants.TESTNET_API_URL, 
            skip_ws=True
        )
        self.coin = coin
        self.grid_size = grid_size
        self.price_spacing = price_spacing_percent
        self.order_size = order_size
        self.active_orders: Dict[int, dict] = {}  # oid -> order details

    def get_mid_price(self) -> float:
        """Get current mid price from order book"""
        book = self.info.l2_snapshot(self.coin)
        best_bid = float(book["levels"][0][0]["px"])
        best_ask = float(book["levels"][1][0]["px"])
        return (best_bid + best_ask) / 2

    def create_grid(self):
        """Create initial grid of orders"""
        mid_price = self.get_mid_price()
        
        # Create buy orders below current price
        for i in range(self.grid_size):
            grid_price = mid_price * (1 - (i + 1) * self.price_spacing)
            result = self.exchange.order(
                self.coin,
                is_buy=True,
                sz=self.order_size,
                limit_px=grid_price,
                order_type={"limit": {"tif": "Gtc"}}
            )
            if result["status"] == "ok":
                status = result["response"]["data"]["statuses"][0]
                if "resting" in status:
                    self.active_orders[status["resting"]["oid"]] = {
                        "price": grid_price,
                        "is_buy": True
                    }

        # Create sell orders above current price
        for i in range(self.grid_size):
            grid_price = mid_price * (1 + (i + 1) * self.price_spacing)
            result = self.exchange.order(
                self.coin,
                is_buy=False,
                sz=self.order_size,
                limit_px=grid_price,
                order_type={"limit": {"tif": "Gtc"}}
            )
            if result["status"] == "ok":
                status = result["response"]["data"]["statuses"][0]
                if "resting" in status:
                    self.active_orders[status["resting"]["oid"]] = {
                        "price": grid_price,
                        "is_buy": False
                    }

    def check_and_replace_filled_orders(self):
        """Check for filled orders and place new ones"""
        orders_to_process = list(self.active_orders.items())
        orders_to_remove = []
        
        # Check each active order
        for oid, order_details in orders_to_process:
            status = self.info.query_order_by_oid(self.address, oid)
            
            # If order is no longer active (filled)
            if status.get("status") != "active":
                # Place a new order on opposite side
                new_price = order_details["price"]
                result = self.exchange.order(
                    self.coin,
                    is_buy=not order_details["is_buy"],
                    sz=self.order_size,
                    limit_px=new_price,
                    order_type={"limit": {"tif": "Gtc"}}
                )
                
                if result["status"] == "ok":
                    status = result["response"]["data"]["statuses"][0]
                    if "resting" in status:
                        self.active_orders[status["resting"]["oid"]] = {
                            "price": new_price,
                            "is_buy": not order_details["is_buy"]
                        }
                
                orders_to_remove.append(oid)
        
        # Remove filled orders from tracking
        for oid in orders_to_remove:
            del self.active_orders[oid]

    def run(self):
        """Run the grid trading bot"""
        print(f"Starting grid trading bot for {self.coin}")
        print(f"Grid size: {self.grid_size}")
        print(f"Price spacing: {self.price_spacing*100}%")
        print(f"Order size: {self.order_size}")
        
        # Create initial grid
        self.create_grid()
        
        # Main loop
        while True:
            try:
                self.check_and_replace_filled_orders()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)  # Wait before retrying

def main():
    # Example configuration
    bot = GridTradingBot(
        coin="ETH",                   # Trading ETH
        grid_size=10,                 # 10 orders on each side
        price_spacing_percent=0.01,   # 1% between each level
        order_size=0.1                # 0.1 ETH per order
    )
    bot.run()

if __name__ == "__main__":
    main()
