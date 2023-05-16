import logging

from eth_account.signers.local import LocalAccount

from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.signing import (
    ZERO_ADDRESS,
    OrderSpec,
    OrderType,
    float_to_usd_int,
    get_timestamp_ms,
    order_grouping_to_number,
    order_spec_preprocessing,
    order_spec_to_order_wire,
    sign_l1_action,
)
from hyperliquid.utils.types import Any, Literal, Meta, Optional


class Exchange(API):
    def __init__(
        self,
        wallet: LocalAccount,
        base_url: Optional[str] = None,
        meta: Optional[Meta] = None,
        vault_address: Optional[str] = None,
    ):
        super().__init__(base_url)
        self.wallet = wallet
        self.vault_address = vault_address
        if meta is None:
            info = Info(base_url, skip_ws=True)
            self.meta = info.meta()
        else:
            self.meta = meta
        self.coin_to_asset = {asset_info["name"]: asset for (asset, asset_info) in enumerate(self.meta["universe"])}

    def _post_action(self, action, signature, nonce):
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": self.vault_address,
        }
        logging.debug(payload)
        return self.post("/exchange", payload)

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
            ZERO_ADDRESS if self.vault_address is None else self.vault_address,
            timestamp,
        )

        return self._post_action(
            {
                "type": "order",
                "grouping": grouping,
                "orders": [order_spec_to_order_wire(order_spec)],
            },
            signature,
            timestamp,
        )

    def cancel(self, coin: str, oid: int) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        signature = sign_l1_action(
            self.wallet,
            ["(uint32,uint64)[]"],
            [[(asset, oid)]],
            ZERO_ADDRESS if self.vault_address is None else self.vault_address,
            timestamp,
        )
        return self._post_action(
            {
                "type": "cancel",
                "cancels": [
                    {
                        "asset": asset,
                        "oid": oid,
                    }
                ],
            },
            signature,
            timestamp,
        )

    def update_leverage(self, leverage: int, coin: str, is_cross: bool = True) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        signature = sign_l1_action(
            self.wallet,
            ["uint32", "bool", "uint32"],
            [asset, is_cross, leverage],
            ZERO_ADDRESS if self.vault_address is None else self.vault_address,
            timestamp,
        )
        return self._post_action(
            {
                "type": "updateLeverage",
                "asset": asset,
                "isCross": is_cross,
                "leverage": leverage,
            },
            signature,
            timestamp,
        )

    def update_isolated_margin(self, amount: float, coin: str) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        amount = float_to_usd_int(amount)
        signature = sign_l1_action(
            self.wallet,
            ["uint32", "bool", "int64"],
            [asset, True, amount],
            ZERO_ADDRESS if self.vault_address is None else self.vault_address,
            timestamp,
        )
        return self._post_action(
            {
                "type": "updateIsolatedMargin",
                "asset": asset,
                "isBuy": True,
                "ntli": amount,
            },
            signature,
            timestamp,
        )
