import eth_account
import logging
import secrets

from eth_abi import encode
from eth_account.signers.local import LocalAccount
from eth_utils import keccak, to_hex

from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import (
    ZERO_ADDRESS,
    CancelRequest,
    OrderRequest,
    OrderSpec,
    OrderType,
    float_to_usd_int,
    get_timestamp_ms,
    order_grouping_to_number,
    order_spec_preprocessing,
    order_spec_to_order_wire,
    sign_l1_action,
    sign_usd_transfer_action,
    sign_agent,
)
from hyperliquid.utils.types import Any, List, Literal, Meta, Optional, Tuple


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
        return self.bulk_orders(
            [
                {
                    "coin": coin,
                    "is_buy": is_buy,
                    "sz": sz,
                    "limit_px": limit_px,
                    "order_type": order_type,
                    "reduce_only": reduce_only,
                }
            ]
        )

    def bulk_orders(self, order_requests: List[OrderRequest]) -> Any:
        order_specs: List[OrderSpec] = [
            {
                "order": {
                    "asset": self.coin_to_asset[order["coin"]],
                    "isBuy": order["is_buy"],
                    "reduceOnly": order["reduce_only"],
                    "limitPx": order["limit_px"],
                    "sz": order["sz"],
                },
                "orderType": order["order_type"],
            }
            for order in order_requests
        ]

        timestamp = get_timestamp_ms()
        grouping: Literal["na"] = "na"

        signature = sign_l1_action(
            self.wallet,
            ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8"],
            [[order_spec_preprocessing(order_spec) for order_spec in order_specs], order_grouping_to_number(grouping)],
            ZERO_ADDRESS if self.vault_address is None else self.vault_address,
            timestamp,
        )

        return self._post_action(
            {
                "type": "order",
                "grouping": grouping,
                "orders": [order_spec_to_order_wire(order_spec) for order_spec in order_specs],
            },
            signature,
            timestamp,
        )

    def cancel(self, coin: str, oid: int) -> Any:
        return self.bulk_cancel([{"coin": coin, "oid": oid}])

    def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        timestamp = get_timestamp_ms()
        signature = sign_l1_action(
            self.wallet,
            ["(uint32,uint64)[]"],
            [[(self.coin_to_asset[cancel["coin"]], cancel["oid"]) for cancel in cancel_requests]],
            ZERO_ADDRESS if self.vault_address is None else self.vault_address,
            timestamp,
        )
        return self._post_action(
            {
                "type": "cancel",
                "cancels": [
                    {
                        "asset": self.coin_to_asset[cancel["coin"]],
                        "oid": cancel["oid"],
                    }
                    for cancel in cancel_requests
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

    def usd_tranfer(self, amount: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        payload = {
            "destination": destination,
            "amount": str(amount),
            "time": timestamp,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_usd_transfer_action(self.wallet, payload, is_mainnet)
        return self._post_action(
            {
                "chain": "Arbitrum" if is_mainnet else "ArbitrumGoerli",
                "payload": payload,
                "type": "usdTransfer",
            },
            signature,
            timestamp,
        )

    def approve_agent(self) -> Tuple[Any, str]:
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        agent = {
            "source": "https://hyperliquid.xyz",
            "connectionId": keccak(encode(["address"], [account.address])),
        }
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_agent(self.wallet, agent, is_mainnet)
        agent["connectionId"] = to_hex(agent["connectionId"])
        return (
            self._post_action(
                {
                    "chain": "Arbitrum" if is_mainnet else "ArbitrumGoerli",
                    "agent": agent,
                    "agentAddress": account.address,
                    "type": "connect",
                },
                signature,
                timestamp,
            ),
            agent_key,
        )
