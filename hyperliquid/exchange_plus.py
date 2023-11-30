from eth_account.signers.local import LocalAccount

from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils.types import Any, List, Literal, Meta, Optional, Tuple, Cloid

# Extends Exchange Class with 'Market Orders'
class ExchangePlus(Exchange):
    DEFAULT_SLIPPAGE = 0.05 # Max allowed Slippage for Market Orders

    def __init__(
        self,
        wallet: LocalAccount,
        base_url: Optional[str] = None,
        meta: Optional[Meta] = None,
        vault_address: Optional[str] = None,
    ):
        super().__init__(wallet, base_url, meta, vault_address) 
        self.info = Info(base_url, skip_ws=True)

        # create a szDecimals map
        self.sz_decimals = {}
        for asset_info in self.meta["universe"]:
            self.sz_decimals[asset_info["name"]] = asset_info["szDecimals"]        

    def __round_sz(
        self,
        coin: str,
        sz: float                
    ) -> float:
        # we round sz based on the sz_decimals map
        return round(sz, self.sz_decimals[coin])

    def __round_px(
        self,
        px: float
    ) -> float:
        # We round px to 5 significant figures and 6 decimals
        return round(float(f"{px:.5g}"), 6) 

    def __slippage_price(
        self,
        coin: str, 
        is_buy: bool,
        slippage: float
    ) -> float:
        
        # Get midprice
        px = float(self.info.all_mids()[coin])
        # Calculate Slippage
        px *= (1 + slippage) if is_buy else (1 - slippage)
        # Round Price
        return self.__round_px(px)

    def market_open(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        slippage: Optional[float] = DEFAULT_SLIPPAGE,            
        cloid: Optional[Cloid] = None,        
    ) -> Any:

        # Get aggressive Market Price
        px = self.__slippage_price(coin, is_buy, slippage)
        sz = self.__round_sz(coin, sz)
        # Market Order is an aggressive Limit Order IoC
        return super().order(
            coin, 
            is_buy, 
            sz, 
            px, 
            order_type = {"limit": {"tif": "Ioc"}},
            reduce_only=False,
            cloid=cloid
            )

    def market_close(
        self,
        coin: str,
        sz: Optional[float] = None,  
        slippage: Optional[float] = DEFAULT_SLIPPAGE,            
        cloid: Optional[Cloid] = None,                  
    ):
        positions = self.info.user_state(self.wallet.address)['assetPositions']
        for position in positions:
            item = position['position']
            if coin != item['coin']:
                continue
            szi = float(item['szi'])
            if not sz:
                sz = szi
            is_buy = True if szi < 0 else False
            # Get aggressive Market Price
            px = self.__slippage_price(coin, is_buy, slippage)
            sz = self.__round_sz(coin, sz)
            # Market Order is an aggressive Limit Order IoC
            return super().order(
                coin, 
                is_buy, 
                sz, 
                px, 
                order_type = {"limit": {"tif": "Ioc"}},
                reduce_only=True,
                cloid=cloid
                )    