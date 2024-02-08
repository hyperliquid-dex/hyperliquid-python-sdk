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
    CancelRequest,
    CancelByCloidRequest,
    ModifyRequest,
    OrderRequest,
    OrderType,
    OrderWire,
    float_to_usd_int,
    get_timestamp_ms,
    order_request_to_order_wire,
    order_wires_to_order_action,
    sign_l1_action,
    sign_usd_transfer_action,
    sign_withdraw_from_bridge_action,
    sign_agent,
)
from hyperliquid.utils.types import Any, List, Meta, Optional, Tuple, Cloid


class Exchange(API):

    # Default Max Slippage for Market Orders 5%
    DEFAULT_SLIPPAGE = 0.05

    def __init__(
        self,
        wallet: LocalAccount,
        base_url: Optional[str] = None,
        meta: Optional[Meta] = None,
        vault_address: Optional[str] = None,
        account_address: Optional[str] = None,
    ):
        super().__init__(base_url)
        self.wallet = wallet
        self.vault_address = vault_address
        self.account_address = account_address
        self.info = Info(base_url, skip_ws=True)
        if meta is None:
            self.meta = self.info.meta()
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

    def _slippage_price(
        self,
        coin: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:

        if not px:
            # Get midprice
            px = float(self.info.all_mids()[coin])
        # Calculate Slippage
        px *= (1 + slippage) if is_buy else (1 - slippage)
        # We round px to 5 significant figures and 6 decimals
        return round(float(f"{px:.5g}"), 6)

    def order(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: OrderType,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        order: OrderRequest = {
            "coin": coin,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": limit_px,
            "order_type": order_type,
            "reduce_only": reduce_only,
        }
        if cloid:
            order["cloid"] = cloid
        return self.bulk_orders([order])

    def bulk_orders(self, order_requests: List[OrderRequest]) -> Any:
        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.coin_to_asset[order["coin"]]) for order in order_requests
        ]
        timestamp = get_timestamp_ms()

        order_action = order_wires_to_order_action(order_wires)

        signature = sign_l1_action(
            self.wallet,
            order_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            order_action,
            signature,
            timestamp,
        )

    def modify_order(
        self,
        oid: int,
        coin: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: OrderType,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
    ) -> Any:

        modify: ModifyRequest = {
            "oid": oid,
            "order": {
                "coin": coin,
                "is_buy": is_buy,
                "sz": sz,
                "limit_px": limit_px,
                "order_type": order_type,
                "reduce_only": reduce_only,
                "cloid": cloid,
            },
        }
        return self.bulk_modify_orders_new([modify])

    def bulk_modify_orders_new(self, modify_requests: List[ModifyRequest]) -> Any:
        timestamp = get_timestamp_ms()
        modify_wires = [
            {
                "oid": modify["oid"],
                "order": order_request_to_order_wire(modify["order"], self.coin_to_asset[modify["order"]["coin"]]),
            }
            for modify in modify_requests
        ]

        modify_action = {
            "type": "batchModify",
            "modifies": modify_wires,
        }

        signature = sign_l1_action(
            self.wallet,
            modify_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            modify_action,
            signature,
            timestamp,
        )

    def market_open(
        self,
        coin: str,
        is_buy: bool,
        sz: float,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
    ) -> Any:

        # Get aggressive Market Price
        px = self._slippage_price(coin, is_buy, slippage, px)
        # Market Order is an aggressive Limit Order IoC
        return self.order(coin, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=False, cloid=cloid)

    def market_close(
        self,
        coin: str,
        sz: Optional[float] = None,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
    ) -> Any:
        address = self.wallet.address
        if self.account_address:
            address = self.account_address
        if self.vault_address:
            address = self.vault_address
        positions = self.info.user_state(address)["assetPositions"]
        for position in positions:
            item = position["position"]
            if coin != item["coin"]:
                continue
            szi = float(item["szi"])
            if not sz:
                sz = abs(szi)
            is_buy = True if szi < 0 else False
            # Get aggressive Market Price
            px = self._slippage_price(coin, is_buy, slippage, px)
            # Market Order is an aggressive Limit Order IoC
            return self.order(coin, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=True, cloid=cloid)

    def cancel(self, coin: str, oid: int) -> Any:
        return self.bulk_cancel([{"coin": coin, "oid": oid}])

    def cancel_by_cloid(self, coin: str, cloid: Cloid) -> Any:
        return self.bulk_cancel_by_cloid([{"coin": coin, "cloid": cloid}])

    def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        timestamp = get_timestamp_ms()
        cancel_action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": self.coin_to_asset[cancel["coin"]],
                    "o": cancel["oid"],
                }
                for cancel in cancel_requests
            ],
        }
        signature = sign_l1_action(
            self.wallet,
            cancel_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    def bulk_cancel_by_cloid(self, cancel_requests: List[CancelByCloidRequest]) -> Any:
        timestamp = get_timestamp_ms()

        cancel_action = {
            "type": "cancelByCloid",
            "cancels": [
                {
                    "asset": self.coin_to_asset[cancel["coin"]],
                    "cloid": cancel["cloid"].to_raw(),
                }
                for cancel in cancel_requests
            ],
        }
        signature = sign_l1_action(
            self.wallet,
            cancel_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    def update_leverage(self, leverage: int, coin: str, is_cross: bool = True) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        update_leverage_action = {
            "type": "updateLeverage",
            "asset": asset,
            "isCross": is_cross,
            "leverage": leverage,
        }
        signature = sign_l1_action(
            self.wallet,
            update_leverage_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            update_leverage_action,
            signature,
            timestamp,
        )

    def update_isolated_margin(self, amount: float, coin: str) -> Any:
        timestamp = get_timestamp_ms()
        asset = self.coin_to_asset[coin]
        amount = float_to_usd_int(amount)
        update_isolated_margin_action = {
            "type": "updateIsolatedMargin",
            "asset": asset,
            "isBuy": True,
            "ntli": amount,
        }
        signature = sign_l1_action(
            self.wallet,
            update_isolated_margin_action,
            self.vault_address,
            timestamp,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            update_isolated_margin_action,
            signature,
            timestamp,
        )

    def usd_transfer(self, amount: float, destination: str) -> Any:
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
                "chain": "Arbitrum" if is_mainnet else "ArbitrumTestnet",
                "payload": payload,
                "type": "usdTransfer",
            },
            signature,
            timestamp,
        )

    def withdraw_from_bridge(self, usd: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        payload = {
            "destination": destination,
            "usd": str(usd),
            "time": timestamp,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_withdraw_from_bridge_action(self.wallet, payload, is_mainnet)
        return self._post_action(
            {
                "chain": "Arbitrum" if is_mainnet else "ArbitrumTestnet",
                "payload": payload,
                "type": "withdraw2",
            },
            signature,
            timestamp,
        )

    def approve_agent(self, name: Optional[str] = None) -> Tuple[Any, str]:
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        if name is not None:
            connection_id = keccak(encode(["address", "string"], [account.address, name]))
        else:
            connection_id = keccak(encode(["address"], [account.address]))
        agent = {
            "source": "https://hyperliquid.xyz",
            "connectionId": connection_id,
        }
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_agent(self.wallet, agent, is_mainnet)
        agent["connectionId"] = to_hex(agent["connectionId"])
        action = {
            "chain": "Arbitrum" if is_mainnet else "ArbitrumTestnet",
            "agent": agent,
            "agentAddress": account.address,
            "type": "connect",
        }
        if name is not None:
            action["extraAgentName"] = name
        return (
            self._post_action(
                action,
                signature,
                timestamp,
            ),
            agent_key,
        )
