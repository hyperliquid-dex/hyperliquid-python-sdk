import json
import logging
import secrets
from typing import Dict, Any, List, Optional, Tuple, Callable

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
    sign_l1_action,
    sign_approve_builder_fee,
    sign_convert_to_multi_sig_user_action,
    sign_multi_sig_action,
    sign_send_asset_action,
    sign_spot_transfer_action,
    sign_token_delegate_action,
    sign_usd_class_transfer_action,
    sign_usd_transfer_action,
    sign_withdraw_from_bridge_action,
    sign_agent,
    sign_user_dex_abstraction_action,
)
from hyperliquid.utils.types import (
    Any,
    BuilderInfo,
    Cloid,
    Meta,
    PerpDexSchemaInput,
    SpotMeta,
)


class Exchange(API):
    """
    Client class for interacting with the Hyperliquid exchange API, handling 
    signing of L1 actions and various trading functionalities.
    """
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
        # Cache the mainnet check for efficiency and cleaner code
        self._is_mainnet = self.base_url == MAINNET_API_URL
    
    @staticmethod
    def _get_dex(coin: str) -> str:
        """Extracts the DEX name from a coin string (e.g., 'coin:dex' -> 'dex')."""
        return coin.split(":")[0] if ":" in coin else ""

    def _post_action(self, action: Dict[str, Any], signature: str, nonce: int) -> Any:
        """
        Posts the signed action payload to the exchange endpoint.
        
        Handles conditional inclusion of vaultAddress and expiresAfter based on action type.
        """
        
        # Actions like usdClassTransfer and sendAsset are signed by the L1 EOA and do not reference the vault address
        requires_vault = action.get("type") not in ["usdClassTransfer", "sendAsset"]
        
        payload = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            "vaultAddress": self.vault_address if requires_vault else None,
            "expiresAfter": self.expires_after,
        }
        logging.debug(payload)
        return self.post("/exchange", payload)

    def _sign_and_post_l1_action(
        self, 
        action: Dict[str, Any], 
        signer_function: Callable = sign_l1_action,
        nonce: Optional[int] = None,
        vault_override: Optional[str] = None
    ) -> Any:
        """
        Handles the repetitive logic of timestamp generation, action signing, and posting.
        Used for the majority of L1-signed actions.
        """
        timestamp = nonce if nonce is not None else get_timestamp_ms()
        
        # Determine the vault address to use for signing, defaulting to the instance vault address
        signing_vault = vault_override if vault_override is not None else self.vault_address

        # Signature function determined by the caller (defaults to sign_l1_action)
        signature = signer_function(
            self.wallet,
            action,
            signing_vault,
            timestamp,
            self.expires_after,
            self._is_mainnet,
        )

        return self._post_action(
            action,
            signature,
            timestamp,
        )

    def _slippage_price(
        self,
        name: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:
        """Calculates the limit price with slippage applied."""
        coin = self.info.name_to_coin[name]
        
        if not px:
            # Get midprice from the info client
            dex = self._get_dex(coin)
            px = float(self.info.all_mids(dex)[coin])

        asset = self.info.coin_to_asset[coin]
        # Spot assets have asset IDs >= 10,000
        is_spot = asset >= 10_000

        # Apply Slippage: Increase price for buy, decrease for sell.
        px *= (1 + slippage) if is_buy else (1 - slippage)
        
        # Round px based on significant figures (5g) and the asset's size decimals.
        sz_decimals = self.info.asset_to_sz_decimals[asset]
        target_decimals = (6 if not is_spot else 8) - sz_decimals
        
        # This complex logic ensures precision is handled correctly for the target asset.
        return round(float(f"{px:.5g}"), target_decimals)

    # expires_after will cause actions to be rejected after that timestamp in milliseconds
    # expires_after is not supported on user_signed actions (e.g. usd_transfer) and must be None 
    # in order for those actions to work.
    def set_expires_after(self, expires_after: Optional[int]) -> None:
        """Sets the expiration timestamp (in UTC milliseconds) for subsequent L1 actions."""
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
        """Sends a single order request."""
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
        """Sends a batch of order requests."""
        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.info.name_to_asset(order["coin"])) for order in order_requests
        ]
        
        if builder:
            # Ensure builder address is lowercase
            builder["b"] = builder["b"].lower()
        order_action = order_wires_to_order_action(order_wires, builder, grouping)

        return self._sign_and_post_l1_action(order_action)

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
        """Modifies a single existing order by OID or Cloid."""
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
        """Sends a batch of order modification requests."""
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

        return self._sign_and_post_l1_action(modify_action)

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
        """Submits a market order (aggressive Limit Order with IoC TIF)."""
        # Calculate aggressive Market Price with slippage applied
        px = self._slippage_price(name, is_buy, slippage, px)
        
        # Market Order is an aggressive Limit Order IoC
        return self.order(
            name, 
            is_buy, 
            sz, 
            px, 
            order_type={"limit": {"tif": "Ioc"}}, 
            reduce_only=False, 
            cloid=cloid, 
            builder=builder
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
        """
        Closes an open position for a given coin.
        If sz is None, closes the full position size.
        """
        
        # Determine the account address to query positions for
        address: str = self.account_address or self.vault_address or self.wallet.address
        
        dex = self._get_dex(coin)
        user_state = self.info.user_state(address, dex)
        
        if user_state is None or "assetPositions" not in user_state:
            logging.warning(f"No asset positions found for coin: {coin} on dex: {dex}")
            return None

        for position in user_state["assetPositions"]:
            item = position["position"]
            if coin != item["coin"]:
                continue
            
            szi = float(item["szi"])
            
            # If size (sz) is not provided, use the absolute current position size
            order_sz = abs(szi) if sz is None else sz
            
            # Determine the order direction (opposite of current position)
            is_buy = szi < 0 
            
            # Calculate aggressive Market Price
            limit_px = self._slippage_price(coin, is_buy, slippage, px)
            
            # Market Close Order (aggressive Limit Order IoC)
            return self.order(
                coin,
                is_buy,
                order_sz,
                limit_px,
                order_type={"limit": {"tif": "Ioc"}},
                reduce_only=True,
                cloid=cloid,
                builder=builder,
            )
        
        logging.warning(f"Position for {coin} not found.")
        return None

    def cancel(self, name: str, oid: int) -> Any:
        """Cancels a single order by Order ID (OID)."""
        return self.bulk_cancel([{"coin": name, "oid": oid}])

    def cancel_by_cloid(self, name: str, cloid: Cloid) -> Any:
        """Cancels a single order by Client Order ID (Cloid)."""
        return self.bulk_cancel_by_cloid([{"coin": name, "cloid": cloid}])

    def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        """Cancels a batch of orders by OID."""
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
        return self._sign_and_post_l1_action(cancel_action)

    def bulk_cancel_by_cloid(self, cancel_requests: List[CancelByCloidRequest]) -> Any:
        """Cancels a batch of orders by Cloid."""
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
        return self._sign_and_post_l1_action(cancel_action)

    def schedule_cancel(self, time: Optional[int]) -> Any:
        """
        Schedules a time (in UTC millis) to cancel all open orders. 
        If time is None, unsets any future cancel time.
        """
        schedule_cancel_action: ScheduleCancelAction = {
            "type": "scheduleCancel",
        }
        if time is not None:
            schedule_cancel_action["time"] = time
            
        return self._sign_and_post_l1_action(schedule_cancel_action)

    def update_leverage(self, leverage: int, name: str, is_cross: bool = True) -> Any:
        """Updates the leverage setting for a specific perpetual asset."""
        update_leverage_action = {
            "type": "updateLeverage",
            "asset": self.info.name_to_asset(name),
            "isCross": is_cross,
            "leverage": leverage,
        }
        return self._sign_and_post_l1_action(update_leverage_action)

    def update_isolated_margin(self, amount: float, name: str) -> Any:
        """Updates the isolated margin amount for a perpetual asset."""
        amount_int = float_to_usd_int(amount)
        update_isolated_margin_action = {
            "type": "updateIsolatedMargin",
            "asset": self.info.name_to_asset(name),
            "isBuy": True, # This field is typically fixed/ignored in the SDK and may relate to the internal protocol logic
            "ntli": amount_int,
        }
        return self._sign_and_post_l1_action(update_isolated_margin_action)

    def set_referrer(self, code: str) -> Any:
        """Sets the referral code for the current account."""
        set_referrer_action = {
            "type": "setReferrer",
            "code": code,
        }
        # setReferrer does not use vaultAddress
        return self._sign_and_post_l1_action(set_referrer_action, vault_override=None)

    def create_sub_account(self, name: str) -> Any:
        """Creates a new sub-account with a given name."""
        create_sub_account_action = {
            "type": "createSubAccount",
            "name": name,
        }
        # createSubAccount does not use vaultAddress
        return self._sign_and_post_l1_action(create_sub_account_action, vault_override=None)

    def usd_class_transfer(self, amount: float, to_perp: bool) -> Any:
        """Transfers USD from perp to spot margin or vice versa."""
        timestamp = get_timestamp_ms()
        str_amount = str(amount)
        
        # Include subaccount info in the amount string if vault is used
        if self.vault_address:
            str_amount += f" subaccount:{self.vault_address}"

        action = {
            "type": "usdClassTransfer",
            "amount": str_amount,
            "toPerp": to_perp,
            "nonce": timestamp,
        }
        # Uses a specific signing function
        signature = sign_usd_class_transfer_action(self.wallet, action, self._is_mainnet)
        
        # usdClassTransfer does not require vaultAddress in the payload
        return self._post_action(action, signature, timestamp)

    def send_asset(self, destination: str, source_dex: str, destination_dex: str, token: str, amount: float) -> Any:
        """
        Transfers assets between different DEXs or accounts.
        Token must match the collateral token if transferring to or from a perp dex.
        """
        timestamp = get_timestamp_ms()
        action = {
            "type": "sendAsset",
            "destination": destination,
            "sourceDex": source_dex,
            "destinationDex": destination_dex,
            "token": token,
            "amount": str(amount),
            "fromSubAccount": self.vault_address if self.vault_address else "",
            "nonce": timestamp,
        }
        # Uses a specific signing function
        signature = sign_send_asset_action(self.wallet, action, self._is_mainnet)
        
        # sendAsset does not require vaultAddress in the payload
        return self._post_action(action, signature, timestamp)

    def sub_account_transfer(self, sub_account_user: str, is_deposit: bool, usd: int) -> Any:
        """Transfers USD between the main account and a sub-account."""
        sub_account_transfer_action = {
            "type": "subAccountTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        # subAccountTransfer does not use vaultAddress for signing context
        return self._sign_and_post_l1_action(sub_account_transfer_action, vault_override=None)

    def sub_account_spot_transfer(self, sub_account_user: str, is_deposit: bool, token: str, amount: float) -> Any:
        """Transfers spot token between the main account and a sub-account."""
        sub_account_transfer_action = {
            "type": "subAccountSpotTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "token": token,
            "amount": str(amount),
        }
        # subAccountSpotTransfer does not use vaultAddress for signing context
        return self._sign_and_post_l1_action(sub_account_transfer_action, vault_override=None)

    def vault_usd_transfer(self, vault_address: str, is_deposit: bool, usd: int) -> Any:
        """Transfers USD into or out of a vault."""
        vault_transfer_action = {
            "type": "vaultTransfer",
            "vaultAddress": vault_address,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        # vaultTransfer does not use vaultAddress for signing context
        return self._sign_and_post_l1_action(vault_transfer_action, vault_override=None)

    def usd_transfer(self, amount: float, destination: str) -> Any:
        """Sends USD to another account (L1 signed action)."""
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "usdSend"}
        
        # Uses a specific signing function (sign_usd_transfer_action)
        signature = sign_usd_transfer_action(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    def spot_transfer(self, amount: float, destination: str, token: str) -> Any:
        """Sends a spot token to another account (L1 signed action)."""
        timestamp = get_timestamp_ms()
        action = {
            "destination": destination,
            "amount": str(amount),
            "token": token,
            "time": timestamp,
            "type": "spotSend",
        }
        # Uses a specific signing function (sign_spot_transfer_action)
        signature = sign_spot_transfer_action(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    def token_delegate(self, validator: str, wei: int, is_undelegate: bool) -> Any:
        """Delegates or undelegates governance tokens."""
        timestamp = get_timestamp_ms()
        action = {
            "validator": validator,
            "wei": wei,
            "isUndelegate": is_undelegate,
            "nonce": timestamp,
            "type": "tokenDelegate",
        }
        # Uses a specific signing function (sign_token_delegate_action)
        signature = sign_token_delegate_action(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    def withdraw_from_bridge(self, amount: float, destination: str) -> Any:
        """Withdraws assets from the Hyperliquid bridge."""
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "withdraw3"}
        # Uses a specific signing function (sign_withdraw_from_bridge_action)
        signature = sign_withdraw_from_bridge_action(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    def approve_agent(self, name: Optional[str] = None) -> Tuple[Any, str]:
        """Approves a new agent key for trading and returns the new agent's private key."""
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        timestamp = get_timestamp_ms()
        
        action = {
            "type": "approveAgent",
            "agentAddress": account.address,
            "agentName": name or "",
            "nonce": timestamp,
        }
        
        # Uses a specific signing function (sign_agent)
        signature = sign_agent(self.wallet, action, self._is_mainnet)
        
        if name is None:
            del action["agentName"]

        response = self._post_action(action, signature, timestamp)
        
        return response, agent_key

    def approve_builder_fee(self, builder: str, max_fee_rate: str) -> Any:
        """Approves a maximum fee rate for a specific order builder."""
        timestamp = get_timestamp_ms()

        action = {"maxFeeRate": max_fee_rate, "builder": builder, "nonce": timestamp, "type": "approveBuilderFee"}
        # Uses a specific signing function (sign_approve_builder_fee)
        signature = sign_approve_builder_fee(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    def convert_to_multi_sig_user(self, authorized_users: List[str], threshold: int) -> Any:
        """Converts the current account to a multi-signature account."""
        timestamp = get_timestamp_ms()
        authorized_users = sorted(authorized_users)
        signers = {
            "authorizedUsers": authorized_users,
            "threshold": threshold,
        }
        action = {
            "type": "convertToMultiSigUser",
            # The 'signers' object must be serialized to JSON string for the protocol
            "signers": json.dumps(signers), 
            "nonce": timestamp,
        }
        # Uses a specific signing function (sign_convert_to_multi_sig_user_action)
        signature = sign_convert_to_multi_sig_user_action(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    # --- Spot Deploy Actions ---
    # NOTE: The following methods use _sign_and_post_l1_action with vault_override=None
    # because deployment actions are typically signed by the EOA and are not vault actions.

    def spot_deploy_register_token(
        self, token_name: str, sz_decimals: int, wei_decimals: int, max_gas: int, full_name: str
    ) -> Any:
        """Deploys and registers a new spot token."""
        action = {
            "type": "spotDeploy",
            "registerToken2": {
                "spec": {"name": token_name, "szDecimals": sz_decimals, "weiDecimals": wei_decimals},
                "maxGas": max_gas,
                "fullName": full_name,
            },
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_user_genesis(
        self, token: int, user_and_wei: List[Tuple[str, str]], existing_token_and_wei: List[Tuple[int, str]]
    ) -> Any:
        """Sets initial token balances for users."""
        action = {
            "type": "spotDeploy",
            "userGenesis": {
                "token": token,
                "userAndWei": [(user.lower(), wei) for (user, wei) in user_and_wei],
                "existingTokenAndWei": existing_token_and_wei,
            },
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_enable_freeze_privilege(self, token: int) -> Any:
        """Enables the freeze privilege for a token."""
        return self.spot_deploy_token_action_inner("enableFreezePrivilege", token)

    def spot_deploy_freeze_user(self, token: int, user: str, freeze: bool) -> Any:
        """Freezes or unfreezes a specific user for a token."""
        action = {
            "type": "spotDeploy",
            "freezeUser": {
                "token": token,
                "user": user.lower(),
                "freeze": freeze,
            },
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_revoke_freeze_privilege(self, token: int) -> Any:
        """Revokes the freeze privilege for a token."""
        return self.spot_deploy_token_action_inner("revokeFreezePrivilege", token)

    def spot_deploy_enable_quote_token(self, token: int) -> Any:
        """Enables a token to be used as a quote token."""
        return self.spot_deploy_token_action_inner("enableQuoteToken", token)

    def spot_deploy_token_action_inner(self, variant: str, token: int) -> Any:
        """Helper for simple spot deploy actions involving only a token ID."""
        action = {
            "type": "spotDeploy",
            variant: {
                "token": token,
            },
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_genesis(self, token: int, max_supply: str, no_hyperliquidity: bool) -> Any:
        """Sets the genesis parameters for a token."""
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
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_register_spot(self, base_token: int, quote_token: int) -> Any:
        """Registers a new spot market."""
        action = {
            "type": "spotDeploy",
            "registerSpot": {
                "tokens": [base_token, quote_token],
            },
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_register_hyperliquidity(
        self, spot: int, start_px: float, order_sz: float, n_orders: int, n_seeded_levels: Optional[int]
    ) -> Any:
        """Registers hyperliquidity for a spot market."""
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
        return self._sign_and_post_l1_action(action, vault_override=None)

    def spot_deploy_set_deployer_trading_fee_share(self, token: int, share: str) -> Any:
        """Sets the deployer's share of trading fees for a token."""
        action = {
            "type": "spotDeploy",
            "setDeployerTradingFeeShare": {
                "token": token,
                "share": share,
            },
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    # --- Perp Deploy Actions ---

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
        """Deploys and registers a new perpetual asset."""
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
        return self._sign_and_post_l1_action(action, vault_override=None)

    def perp_deploy_set_oracle(
        self,
        dex: str,
        oracle_pxs: Dict[str, str],
        all_mark_pxs: List[Dict[str, str]],
        external_perp_pxs: Dict[str, str],
    ) -> Any:
        """Sets oracle and mark prices for perpetual assets."""
        # Ensure data is sorted for consistent signing/serialization
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
        return self._sign_and_post_l1_action(action, vault_override=None)

    # --- C-Signer Actions (Validators) ---

    def c_signer_unjail_self(self) -> Any:
        """Unjails the C-Signer."""
        return self.c_signer_inner("unjailSelf")

    def c_signer_jail_self(self) -> Any:
        """Jails the C-Signer."""
        return self.c_signer_inner("jailSelf")

    def c_signer_inner(self, variant: str) -> Any:
        """Helper for C-Signer actions."""
        action = {
            "type": "CSignerAction",
            variant: None,
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

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
        """Registers a new C-Validator."""
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
        return self._sign_and_post_l1_action(action, vault_override=None)

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
        """Changes the profile settings for an existing C-Validator."""
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
        return self._sign_and_post_l1_action(action, vault_override=None)

    def c_validator_unregister(self) -> Any:
        """Unregisters the C-Validator."""
        action = {
            "type": "CValidatorAction",
            "unregister": None,
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def multi_sig(self, multi_sig_user: str, inner_action: Dict[str, Any], signatures: List[str], nonce: int, vault_address: Optional[str] = None) -> Any:
        """Submits a multi-signature action."""
        multi_sig_user = multi_sig_user.lower()
        multi_sig_action = {
            "type": "multiSig",
            # Chain ID for EIP-712 signing context (often fixed to 0x66eee for HL)
            "signatureChainId": "0x66eee", 
            "signatures": signatures,
            "payload": {
                "multiSigUser": multi_sig_user,
                "outerSigner": self.wallet.address.lower(),
                "action": inner_action,
            },
        }
        
        # Uses a specific signing function
        signature = sign_multi_sig_action(
            self.wallet,
            multi_sig_action,
            self._is_mainnet,
            vault_address,
            nonce,
            self.expires_after,
        )
        
        return self._post_action(multi_sig_action, signature, nonce)

    def use_big_blocks(self, enable: bool) -> Any:
        """Enables/disables the 'use big blocks' EVM feature for the user."""
        action = {
            "type": "evmUserModify",
            "usingBigBlocks": enable,
        }
        return self._sign_and_post_l1_action(action, vault_override=None)

    def agent_enable_dex_abstraction(self) -> Any:
        """Enables DEX abstraction for the current agent."""
        action = {
            "type": "agentEnableDexAbstraction",
        }
        return self._sign_and_post_l1_action(action)

    def user_dex_abstraction(self, user: str, enabled: bool) -> Any:
        """Sets the DEX abstraction status for a specific user."""
        timestamp = get_timestamp_ms()
        action = {
            "type": "userDexAbstraction",
            "user": user.lower(),
            "enabled": enabled,
            "nonce": timestamp,
        }
        # Uses a specific signing function (sign_user_dex_abstraction_action)
        signature = sign_user_dex_abstraction_action(self.wallet, action, self._is_mainnet)
        
        return self._post_action(action, signature, timestamp)

    def noop(self, nonce: int) -> Any:
        """Sends a no-operation action to the exchange."""
        action = {"type": "noop"}
        return self._sign_and_post_l1_action(action, nonce=nonce)
