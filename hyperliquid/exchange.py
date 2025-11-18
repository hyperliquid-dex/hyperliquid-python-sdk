import json
import logging
import secrets

import eth_account
from eth_account.signers.local import LocalAccount

from hyperliquid.api import API
from hyperliquid.info import Info
from hyperliquid.utils.constants import MAINNET_API_URL
from hyperliquid.utils.signing import (
    CancelByCloidRequest,
    CancelRequest,
    Grouping,
    ModifyRequest,
    OidOrCloid,
    OrderRequest,
    OrderType,
    OrderWire,
    ScheduleCancelAction,
    float_to_usd_int,
    get_timestamp_ms,
    order_request_to_order_wire,
    order_wires_to_order_action,
    sign_agent,
    sign_approve_builder_fee,
    sign_convert_to_multi_sig_user_action,
    sign_l1_action,
    sign_multi_sig_action,
    sign_send_asset_action,
    sign_spot_transfer_action,
    sign_token_delegate_action,
    sign_usd_class_transfer_action,
    sign_usd_transfer_action,
    sign_user_dex_abstraction_action,
    sign_withdraw_from_bridge_action,
)
from hyperliquid.utils.types import (
    Any,
    BuilderInfo,
    Cloid,
    Dict,
    List,
    Meta,
    Optional,
    PerpDexSchemaInput,
    SpotMeta,
    Tuple,
)


def _get_dex(coin: str) -> str:
    return coin.split(":")[0] if ":" in coin else ""


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
        spot_meta: Optional[SpotMeta] = None,
        perp_dexs: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ):
        super().__init__(base_url, timeout)
        self.wallet = wallet
        self.vault_address = vault_address
        self.account_address = account_address
        self.info = Info(base_url, True, meta, spot_meta, perp_dexs, timeout)
        self.expires_after: Optional[int] = None

    def _post_action(self, action, signature, nonce):
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": self.vault_address if action["type"] not in ["usdClassTransfer", "sendAsset"] else None,
            "expiresAfter": self.expires_after,
        }
        logging.debug(payload)
        return self.post("/exchange", payload)

    def _slippage_price(
        self,
        name: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:
        coin = self.info.name_to_coin[name]
        if not px:
            # Get midprice
            dex = _get_dex(coin)
            px = float(self.info.all_mids(dex)[coin])

        asset = self.info.coin_to_asset[coin]
        # spot assets start at 10000
        is_spot = asset >= 10_000

        # Calculate Slippage
        px *= (1 + slippage) if is_buy else (1 - slippage)
        # We round px to 5 significant figures and 6 decimals for perps, 8 decimals for spot
        return round(float(f"{px:.5g}"), (6 if not is_spot else 8) - self.info.asset_to_sz_decimals[asset])

    # expires_after will cause actions to be rejected after that timestamp in milliseconds
    # expires_after is not supported on user_signed actions (e.g. usd_transfer) and must be None in order for those
    # actions to work.
    def set_expires_after(self, expires_after: Optional[int]) -> None:
        self.expires_after = expires_after

    def order(
        self,
        name: str,
        is_buy: bool,
        sz: float,
        limit_px: float,
        order_type: OrderType,
        reduce_only: bool = False,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None,
    ) -> Any:
        order: OrderRequest = {
            "coin": name,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": limit_px,
            "order_type": order_type,
            "reduce_only": reduce_only,
        }
        if cloid:
            order["cloid"] = cloid
        return self.bulk_orders([order], builder)

    def bulk_orders(
        self, order_requests: List[OrderRequest], builder: Optional[BuilderInfo] = None, grouping: Grouping = "na"
    ) -> Any:
        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.info.name_to_asset(order["coin"])) for order in order_requests
        ]
        timestamp = get_timestamp_ms()

        if builder:
            builder["b"] = builder["b"].lower()
        order_action = order_wires_to_order_action(order_wires, builder, grouping)

        signature = sign_l1_action(
            self.wallet,
            order_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            order_action,
            signature,
            timestamp,
        )

    def modify_order(
        self,
        oid: OidOrCloid,
        name: str,
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
                "coin": name,
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
                "oid": modify["oid"].to_raw() if isinstance(modify["oid"], Cloid) else modify["oid"],
                "order": order_request_to_order_wire(modify["order"], self.info.name_to_asset(modify["order"]["coin"])),
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
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            modify_action,
            signature,
            timestamp,
        )

    def market_open(
        self,
        name: str,
        is_buy: bool,
        sz: float,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None,
    ) -> Any:
        # Get aggressive Market Price
        px = self._slippage_price(name, is_buy, slippage, px)
        # Market Order is an aggressive Limit Order IoC
        return self.order(
            name, is_buy, sz, px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=False, cloid=cloid, builder=builder
        )

    def market_close(
        self,
        coin: str,
        sz: Optional[float] = None,
        px: Optional[float] = None,
        slippage: float = DEFAULT_SLIPPAGE,
        cloid: Optional[Cloid] = None,
        builder: Optional[BuilderInfo] = None,
    ) -> Any:
        address: str = self.wallet.address
        if self.account_address:
            address = self.account_address
        if self.vault_address:
            address = self.vault_address
        dex = _get_dex(coin)
        positions = self.info.user_state(address, dex)["assetPositions"]
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
            return self.order(
                coin,
                is_buy,
                sz,
                px,
                order_type={"limit": {"tif": "Ioc"}},
                reduce_only=True,
                cloid=cloid,
                builder=builder,
            )

    def cancel(self, name: str, oid: int) -> Any:
        return self.bulk_cancel([{"coin": name, "oid": oid}])

    def cancel_by_cloid(self, name: str, cloid: Cloid) -> Any:
        return self.bulk_cancel_by_cloid([{"coin": name, "cloid": cloid}])

    def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        timestamp = get_timestamp_ms()
        cancel_action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": self.info.name_to_asset(cancel["coin"]),
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
            self.expires_after,
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
                    "asset": self.info.name_to_asset(cancel["coin"]),
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
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )

        return self._post_action(
            cancel_action,
            signature,
            timestamp,
        )

    def schedule_cancel(self, time: Optional[int]) -> Any:
        """Schedules a time (in UTC millis) to cancel all open orders. The time must be at least 5 seconds after the current time.
        Once the time comes, all open orders will be canceled and a trigger count will be incremented. The max number of triggers
        per day is 10. This trigger count is reset at 00:00 UTC.

        Args:
            time (int): if time is not None, then set the cancel time in the future. If None, then unsets any cancel time in the future.
        """
        timestamp = get_timestamp_ms()
        schedule_cancel_action: ScheduleCancelAction = {
            "type": "scheduleCancel",
        }
        if time is not None:
            schedule_cancel_action["time"] = time
        signature = sign_l1_action(
            self.wallet,
            schedule_cancel_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            schedule_cancel_action,
            signature,
            timestamp,
        )

    def update_leverage(self, leverage: int, name: str, is_cross: bool = True) -> Any:
        timestamp = get_timestamp_ms()
        update_leverage_action = {
            "type": "updateLeverage",
            "asset": self.info.name_to_asset(name),
            "isCross": is_cross,
            "leverage": leverage,
        }
        signature = sign_l1_action(
            self.wallet,
            update_leverage_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            update_leverage_action,
            signature,
            timestamp,
        )

    def update_isolated_margin(self, amount: float, name: str) -> Any:
        timestamp = get_timestamp_ms()
        amount = float_to_usd_int(amount)
        update_isolated_margin_action = {
            "type": "updateIsolatedMargin",
            "asset": self.info.name_to_asset(name),
            "isBuy": True,
            "ntli": amount,
        }
        signature = sign_l1_action(
            self.wallet,
            update_isolated_margin_action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            update_isolated_margin_action,
            signature,
            timestamp,
        )

    def set_referrer(self, code: str) -> Any:
        timestamp = get_timestamp_ms()
        set_referrer_action = {
            "type": "setReferrer",
            "code": code,
        }
        signature = sign_l1_action(
            self.wallet,
            set_referrer_action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            set_referrer_action,
            signature,
            timestamp,
        )

    def create_sub_account(self, name: str) -> Any:
        timestamp = get_timestamp_ms()
        create_sub_account_action = {
            "type": "createSubAccount",
            "name": name,
        }
        signature = sign_l1_action(
            self.wallet,
            create_sub_account_action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            create_sub_account_action,
            signature,
            timestamp,
        )

    def usd_class_transfer(self, amount: float, to_perp: bool) -> Any:
        timestamp = get_timestamp_ms()
        str_amount = str(amount)
        if self.vault_address:
            str_amount += f" subaccount:{self.vault_address}"

        action = {
            "type": "usdClassTransfer",
            "amount": str_amount,
            "toPerp": to_perp,
            "nonce": timestamp,
        }
        signature = sign_usd_class_transfer_action(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def send_asset(self, destination: str, source_dex: str, destination_dex: str, token: str, amount: float) -> Any:
        """
        For the default perp dex use the empty string "" as name. For spot use "spot".
        Token must match the collateral token if transferring to or from a perp dex.
        """
        timestamp = get_timestamp_ms()
        str_amount = str(amount)

        action = {
            "type": "sendAsset",
            "destination": destination,
            "sourceDex": source_dex,
            "destinationDex": destination_dex,
            "token": token,
            "amount": str_amount,
            "fromSubAccount": self.vault_address if self.vault_address else "",
            "nonce": timestamp,
        }
        signature = sign_send_asset_action(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def sub_account_transfer(self, sub_account_user: str, is_deposit: bool, usd: int) -> Any:
        timestamp = get_timestamp_ms()
        sub_account_transfer_action = {
            "type": "subAccountTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        signature = sign_l1_action(
            self.wallet,
            sub_account_transfer_action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            sub_account_transfer_action,
            signature,
            timestamp,
        )

    def sub_account_spot_transfer(self, sub_account_user: str, is_deposit: bool, token: str, amount: float) -> Any:
        timestamp = get_timestamp_ms()
        sub_account_transfer_action = {
            "type": "subAccountSpotTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "token": token,
            "amount": str(amount),
        }
        signature = sign_l1_action(
            self.wallet,
            sub_account_transfer_action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            sub_account_transfer_action,
            signature,
            timestamp,
        )

    def vault_usd_transfer(self, vault_address: str, is_deposit: bool, usd: int) -> Any:
        timestamp = get_timestamp_ms()
        vault_transfer_action = {
            "type": "vaultTransfer",
            "vaultAddress": vault_address,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_l1_action(self.wallet, vault_transfer_action, None, timestamp, self.expires_after, is_mainnet)
        return self._post_action(
            vault_transfer_action,
            signature,
            timestamp,
        )

    def usd_transfer(self, amount: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "usdSend"}
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_usd_transfer_action(self.wallet, action, is_mainnet)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_transfer(self, amount: float, destination: str, token: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "destination": destination,
            "amount": str(amount),
            "token": token,
            "time": timestamp,
            "type": "spotSend",
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_spot_transfer_action(self.wallet, action, is_mainnet)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def token_delegate(self, validator: str, wei: int, is_undelegate: bool) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "validator": validator,
            "wei": wei,
            "isUndelegate": is_undelegate,
            "nonce": timestamp,
            "type": "tokenDelegate",
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_token_delegate_action(self.wallet, action, is_mainnet)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def withdraw_from_bridge(self, amount: float, destination: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "withdraw3"}
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_withdraw_from_bridge_action(self.wallet, action, is_mainnet)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def approve_agent(self, name: Optional[str] = None) -> Tuple[Any, str]:
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        action = {
            "type": "approveAgent",
            "agentAddress": account.address,
            "agentName": name or "",
            "nonce": timestamp,
        }
        signature = sign_agent(self.wallet, action, is_mainnet)
        if name is None:
            del action["agentName"]

        return (
            self._post_action(
                action,
                signature,
                timestamp,
            ),
            agent_key,
        )

    def approve_builder_fee(self, builder: str, max_fee_rate: str) -> Any:
        timestamp = get_timestamp_ms()

        action = {"maxFeeRate": max_fee_rate, "builder": builder, "nonce": timestamp, "type": "approveBuilderFee"}
        signature = sign_approve_builder_fee(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(action, signature, timestamp)

    def convert_to_multi_sig_user(self, authorized_users: List[str], threshold: int) -> Any:
        timestamp = get_timestamp_ms()
        authorized_users = sorted(authorized_users)
        signers = {
            "authorizedUsers": authorized_users,
            "threshold": threshold,
        }
        action = {
            "type": "convertToMultiSigUser",
            "signers": json.dumps(signers),
            "nonce": timestamp,
        }
        signature = sign_convert_to_multi_sig_user_action(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_register_token(
        self, token_name: str, sz_decimals: int, wei_decimals: int, max_gas: int, full_name: str
    ) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "registerToken2": {
                "spec": {"name": token_name, "szDecimals": sz_decimals, "weiDecimals": wei_decimals},
                "maxGas": max_gas,
                "fullName": full_name,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_user_genesis(
        self, token: int, user_and_wei: List[Tuple[str, str]], existing_token_and_wei: List[Tuple[int, str]]
    ) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "userGenesis": {
                "token": token,
                "userAndWei": [(user.lower(), wei) for (user, wei) in user_and_wei],
                "existingTokenAndWei": existing_token_and_wei,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_enable_freeze_privilege(self, token: int) -> Any:
        return self.spot_deploy_token_action_inner("enableFreezePrivilege", token)

    def spot_deploy_freeze_user(self, token: int, user: str, freeze: bool) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "freezeUser": {
                "token": token,
                "user": user.lower(),
                "freeze": freeze,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_revoke_freeze_privilege(self, token: int) -> Any:
        return self.spot_deploy_token_action_inner("revokeFreezePrivilege", token)

    def spot_deploy_enable_quote_token(self, token: int) -> Any:
        return self.spot_deploy_token_action_inner("enableQuoteToken", token)

    def spot_deploy_token_action_inner(self, variant: str, token: int) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            variant: {
                "token": token,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_genesis(self, token: int, max_supply: str, no_hyperliquidity: bool) -> Any:
        timestamp = get_timestamp_ms()
        genesis = {
            "token": token,
            "maxSupply": max_supply,
        }
        if no_hyperliquidity:
            genesis["noHyperliquidity"] = True
        action = {
            "type": "spotDeploy",
            "genesis": genesis,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_register_spot(self, base_token: int, quote_token: int) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "registerSpot": {
                "tokens": [base_token, quote_token],
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_register_hyperliquidity(
        self, spot: int, start_px: float, order_sz: float, n_orders: int, n_seeded_levels: Optional[int]
    ) -> Any:
        timestamp = get_timestamp_ms()
        register_hyperliquidity = {
            "spot": spot,
            "startPx": str(start_px),
            "orderSz": str(order_sz),
            "nOrders": n_orders,
        }
        if n_seeded_levels is not None:
            register_hyperliquidity["nSeededLevels"] = n_seeded_levels
        action = {
            "type": "spotDeploy",
            "registerHyperliquidity": register_hyperliquidity,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def spot_deploy_set_deployer_trading_fee_share(self, token: int, share: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "spotDeploy",
            "setDeployerTradingFeeShare": {
                "token": token,
                "share": share,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def perp_deploy_register_asset(
        self,
        dex: str,
        max_gas: Optional[int],
        coin: str,
        sz_decimals: int,
        oracle_px: str,
        margin_table_id: int,
        only_isolated: bool,
        schema: Optional[PerpDexSchemaInput],
    ) -> Any:
        timestamp = get_timestamp_ms()
        schema_wire = None
        if schema is not None:
            schema_wire = {
                "fullName": schema["fullName"],
                "collateralToken": schema["collateralToken"],
                "oracleUpdater": schema["oracleUpdater"].lower() if schema["oracleUpdater"] is not None else None,
            }
        action = {
            "type": "perpDeploy",
            "registerAsset": {
                "maxGas": max_gas,
                "assetRequest": {
                    "coin": coin,
                    "szDecimals": sz_decimals,
                    "oraclePx": oracle_px,
                    "marginTableId": margin_table_id,
                    "onlyIsolated": only_isolated,
                },
                "dex": dex,
                "schema": schema_wire,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def perp_deploy_set_oracle(
        self,
        dex: str,
        oracle_pxs: Dict[str, str],
        all_mark_pxs: List[Dict[str, str]],
        external_perp_pxs: Dict[str, str],
    ) -> Any:
        timestamp = get_timestamp_ms()
        oracle_pxs_wire = sorted(list(oracle_pxs.items()))
        mark_pxs_wire = [sorted(list(mark_pxs.items())) for mark_pxs in all_mark_pxs]
        external_perp_pxs_wire = sorted(list(external_perp_pxs.items()))
        action = {
            "type": "perpDeploy",
            "setOracle": {
                "dex": dex,
                "oraclePxs": oracle_pxs_wire,
                "markPxs": mark_pxs_wire,
                "externalPerpPxs": external_perp_pxs_wire,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def c_signer_unjail_self(self) -> Any:
        return self.c_signer_inner("unjailSelf")

    def c_signer_jail_self(self) -> Any:
        return self.c_signer_inner("jailSelf")

    def c_signer_inner(self, variant: str) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "CSignerAction",
            variant: None,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def c_validator_register(
        self,
        node_ip: str,
        name: str,
        description: str,
        delegations_disabled: bool,
        commission_bps: int,
        signer: str,
        unjailed: bool,
        initial_wei: int,
    ) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "CValidatorAction",
            "register": {
                "profile": {
                    "node_ip": {"Ip": node_ip},
                    "name": name,
                    "description": description,
                    "delegations_disabled": delegations_disabled,
                    "commission_bps": commission_bps,
                    "signer": signer,
                },
                "unjailed": unjailed,
                "initial_wei": initial_wei,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def c_validator_change_profile(
        self,
        node_ip: Optional[str],
        name: Optional[str],
        description: Optional[str],
        unjailed: bool,
        disable_delegations: Optional[bool],
        commission_bps: Optional[int],
        signer: Optional[str],
    ) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "CValidatorAction",
            "changeProfile": {
                "node_ip": None if node_ip is None else {"Ip": node_ip},
                "name": name,
                "description": description,
                "unjailed": unjailed,
                "disable_delegations": disable_delegations,
                "commission_bps": commission_bps,
                "signer": signer,
            },
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def c_validator_unregister(self) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "CValidatorAction",
            "unregister": None,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def multi_sig(self, multi_sig_user, inner_action, signatures, nonce, vault_address=None):
        multi_sig_user = multi_sig_user.lower()
        multi_sig_action = {
            "type": "multiSig",
            "signatureChainId": "0x66eee",
            "signatures": signatures,
            "payload": {
                "multiSigUser": multi_sig_user,
                "outerSigner": self.wallet.address.lower(),
                "action": inner_action,
            },
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_multi_sig_action(
            self.wallet,
            multi_sig_action,
            is_mainnet,
            vault_address,
            nonce,
            self.expires_after,
        )
        return self._post_action(
            multi_sig_action,
            signature,
            nonce,
        )

    def use_big_blocks(self, enable: bool) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "evmUserModify",
            "usingBigBlocks": enable,
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            None,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def agent_enable_dex_abstraction(self) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "agentEnableDexAbstraction",
        }
        signature = sign_l1_action(
            self.wallet,
            action,
            self.vault_address,
            timestamp,
            self.expires_after,
            self.base_url == MAINNET_API_URL,
        )
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def user_dex_abstraction(self, user: str, enabled: bool) -> Any:
        timestamp = get_timestamp_ms()
        action = {
            "type": "userDexAbstraction",
            "user": user.lower(),
            "enabled": enabled,
            "nonce": timestamp,
        }
        signature = sign_user_dex_abstraction_action(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def noop(self, nonce):
        action = {"type": "noop"}
        signature = sign_l1_action(
            self.wallet, action, self.vault_address, nonce, self.expires_after, self.base_url == MAINNET_API_URL
        )
        return self._post_action(action, signature, nonce)
