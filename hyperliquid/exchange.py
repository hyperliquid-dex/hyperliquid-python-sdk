import logging

from eth_account.signers.local import LocalAccount

from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.signing import (
    OrderSpec,
    order_spec_preprocessing,
    order_grouping_to_number,
    sign_l1_action,
    ZERO_ADDRESS,
    OrderType,
    order_spec_to_order_wire,
    get_timestamp_ms,
)
from hyperliquid.utils.types import Meta, Any, Literal, Optional


class Exchange(API):
    def __init__(self, wallet: LocalAccount, base_url: Optional[str] = None, meta: Optional[Meta] = None):
        super().__init__(base_url)
        self.wallet = wallet
        if meta is None:
            info = Info(base_url, skip_ws=True)
            self.meta = info.meta()
        else:
            self.meta = meta
        self.coin_to_asset = {asset_info["name"]: asset for (asset, asset_info) in enumerate(self.meta["universe"])}

    def order(
        self, coin: str, is_buy: bool, sz: float, limit_px: float, order_type: OrderType, reduce_only: bool = False
    ) -> Any:
        order_spec: OrderSpec = {
            "order": {
                "asset": self.coin_to_asset[coin],
                "isBuy": is_buy,
                "reduceOnly": reduce_only,
                "limitPx": limit_px,
                "sz": sz,
            },
            "orderType": order_type,
        }
        timestamp = get_timestamp_ms()
        grouping: Literal["na"] = "na"

        signature = sign_l1_action(
            self.wallet,
            ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8"],
            [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
            ZERO_ADDRESS,
            timestamp,
        )
        logging.debug(
            {
                "action": {
                    "type": "order",
                    "grouping": grouping,
                    "orders": [order_spec_to_order_wire(order_spec)],
                },
                "nonce": timestamp,
                "signature": signature,
                "vaultAddress": None,
            }
        )
        return self.post(
            "/exchange",
            {
                "action": {
                    "type": "order",
                    "grouping": grouping,
                    "orders": [order_spec_to_order_wire(order_spec)],
                },
                "nonce": timestamp,
                "signature": signature,
                "vaultAddress": None,
            },
        )

    def cancel(self, coin: str, oid: int) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        signature = sign_l1_action(self.wallet, ["(uint32,uint64)[]"], [[(asset, oid)]], ZERO_ADDRESS, timestamp)
        return self.post(
            "/exchange",
            {
                "action": {
                    "type": "cancel",
                    "cancels": [
                        {
                            "asset": asset,
                            "oid": oid,
                        }
                    ],
                },
                "nonce": timestamp,
                "signature": signature,
                "vaultAddress": None,
            },
        )
