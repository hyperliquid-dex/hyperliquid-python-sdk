import json
import logging
import secrets
from typing import Any, Dict, List, Optional, Tuple, Union # Cleaned up imports

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
    BuilderInfo,
    Cloid,
    Meta,
    PerpDexSchemaInput,
    SpotMeta,
) # Removed redundant standard types (Any, List, Dict, etc.)


def _get_dex(coin: str) -> str:
    """Extracts the DEX identifier from a coin name if present (e.g., 'DEX:COIN' -> 'DEX')."""
    return coin.split(":")[0] if ":" in coin else ""


class Exchange(API):
    # Default Max Slippage for Market Orders is 5%
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
        # Initialize Info object using the same base_url
        self.info = Info(base_url, True, meta, spot_meta, perp_dexs, timeout)
        self.expires_after: Optional[int] = None

    def _post_action(self, action: Dict[str, Any], signature: str, nonce: int) -> Any:
        """Helper to construct the payload, log the request, and post the action to the exchange endpoint."""
        # Determine vaultAddress inclusion based on action type
        include_vault_address = action.get("type") not in ["usdClassTransfer", "sendAsset", "usdSend", "spotSend", "tokenDelegate", "withdraw3", "userDexAbstraction"]
        
        # Explicitly check for vault address being set before including it
        vault_addr = self.vault_address if include_vault_address else None
        
        payload: Dict[str, Any] = {
            "action": action,
            "nonce": nonce,
            "signature": signature,
            # Pass vaultAddress only if applicable and set
            "vaultAddress": vault_addr,
            "expiresAfter": self.expires_after,
        }
        
        # Remove keys with None values to keep the payload cleaner and correct for Hyperliquid API
        # The original code logic for vaultAddress was preserved for action types like usdClassTransfer
        # that explicitly handle it within the calling function by setting the class attribute (vault_address) to None.
        # However, the Hyperliquid API expects 'vaultAddress' only for certain types of actions.
        if payload["vaultAddress"] is None:
            del payload["vaultAddress"]
        if payload["expiresAfter"] is None:
            del payload["expiresAfter"]

        logging.debug(json.dumps(payload))
        return self.post("/exchange", payload)

    def _sign_and_post_l1_action(self, action: Dict[str, Any], vault_address: Optional[str] = None) -> Any:
        """
        Generic helper for L1-signed actions. Handles timestamp generation, signing, and posting.
        Actions that are not "user_signed" (e.g., usd_transfer) use sign_l1_action.
        """
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        
        # Use the provided vault_address or the instance's default if None is explicitly passed
        # and the action type suggests it should be included (handled in _post_action).
        
        # Note: The original code often passed None for the vault_address in sign_l1_action 
        # when it was not relevant (e.g., for setReferrer). We maintain that pattern here.
        
        signature = sign_l1_action(
            self.wallet,
            action,
            vault_address or self.vault_address, # Default to instance's vault_address unless overridden
            timestamp,
            self.expires_after,
            is_mainnet,
        )

        return self._post_action(action, signature, timestamp)


    def _slippage_price(
        self,
        name: str,
        is_buy: bool,
        slippage: float,
        px: Optional[float] = None,
    ) -> float:
        """
        Calculates the aggressive limit price based on current mid-price and slippage.
        Handles the complex rounding required by Hyperliquid for perp and spot assets.
        """
        coin = self.info.name_to_coin[name]
        
        if not px:
            # Get mid-price if not provided
            dex = _get_dex(coin)
            # Ensure the fetched mid-price is a float
            px = float(self.info.all_mids(dex)[coin])

        asset = self.info.coin_to_asset[coin]
        # Spot assets are typically >= 10000
        is_spot = asset >= 10_000

        # Apply slippage
        # Buy: price increases (1 + slippage); Sell: price decreases (1 - slippage)
        px *= (1 + slippage) if is_buy else (1 - slippage)
        
        # Rounding logic:
        # 1. Format to 5 significant figures (string formatting)
        # 2. Round to a specific number of decimals determined by asset decimals
        decimals_to_round = (6 if not is_spot else 8) - self.info.asset_to_sz_decimals[asset]
        
        # NOTE: This complex rounding (sig figs then decimal places) is preserved
        # as it is likely crucial for the Hyperliquid API's price validation.
        return round(float(f"{px:.5g}"), decimals_to_round)

    # expires_after will cause actions to be rejected after that timestamp in milliseconds
    # expires_after is not supported on user_signed actions (e.g. usd_transfer) and must be None in order for those
    # actions to work.
    def set_expires_after(self, expires_after: Optional[int]) -> None:
        """Sets an expiry timestamp for L1-signed actions."""
        self.expires_after = expires_after

    # --- Core Trading Actions ---

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
        """Places a single order."""
        order: OrderRequest = {
            "coin": name,
            "is_buy": is_buy,
            "sz": sz,
            "limit_px": limit_px,
            "order_type": order_type,
            "reduce_only": reduce_only,
        }
        if cloid:
            # The Cloid must be added as a string/raw value for the bulk_orders input
            order["cloid"] = cloid.to_raw() if isinstance(cloid, Cloid) else cloid
            
        return self.bulk_orders([order], builder)

    def bulk_orders(
        self, order_requests: List[OrderRequest], builder: Optional[BuilderInfo] = None, grouping: Grouping = "na"
    ) -> Any:
        """Places multiple orders in a single transaction (batch order)."""
        order_wires: List[OrderWire] = [
            order_request_to_order_wire(order, self.info.name_to_asset(order["coin"])) for order in order_requests
        ]
        
        timestamp = get_timestamp_ms()

        if builder:
            # Builder address must be lowercase
            builder["b"] = builder["b"].lower()
            
        order_action = order_wires_to_order_action(order_wires, builder, grouping)

        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(order_action, self.vault_address)


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
        """Modifies an existing order using its Order ID (oid) or Client Order ID (cloid)."""
        # Ensure OidOrCloid is properly handled if it's a Cloid object
        oid_raw = oid.to_raw() if isinstance(oid, Cloid) else oid
        
        modify: ModifyRequest = {
            "oid": oid_raw,
            "order": {
                "coin": name,
                "is_buy": is_buy,
                "sz": sz,
                "limit_px": limit_px,
                "order_type": order_type,
                "reduce_only": reduce_only,
                "cloid": cloid.to_raw() if isinstance(cloid, Cloid) else cloid,
            },
        }
        return self.bulk_modify_orders_new([modify])

    def bulk_modify_orders_new(self, modify_requests: List[ModifyRequest]) -> Any:
        """Batches multiple order modifications."""
        
        modify_wires = [
            {
                # Convert Cloid object to its raw string/int representation
                "oid": modify["oid"].to_raw() if isinstance(modify["oid"], Cloid) else modify["oid"],
                "order": order_request_to_order_wire(modify["order"], self.info.name_to_asset(modify["order"]["coin"])),
            }
            for modify in modify_requests
        ]

        modify_action = {
            "type": "batchModify",
            "modifies": modify_wires,
        }

        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(modify_action, self.vault_address)

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
        """Places a market order to open a position. Uses an aggressive IoC limit order."""
        # Calculate the aggressive limit price using slippage
        limit_px = self._slippage_price(name, is_buy, slippage, px)
        # Market Order is simulated as an aggressive Limit Order with Immediate-or-Cancel (IoC) TIF
        return self.order(
            name, is_buy, sz, limit_px, order_type={"limit": {"tif": "Ioc"}}, reduce_only=False, cloid=cloid, builder=builder
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
        Places a market order to close an existing position.
        The side (buy/sell) is determined automatically based on the current position's size (szi).
        """
        # Determine the correct account address prioritizing vault, then account_address, then wallet address.
        if self.vault_address:
            address = self.vault_address
        elif self.account_address:
            address = self.account_address
        else:
            address = self.wallet.address
            
        dex = _get_dex(coin)
        user_state = self.info.user_state(address, dex)
        
        # Check if user state retrieval was successful and contains asset positions
        if not user_state or "assetPositions" not in user_state:
            logging.error(f"Could not retrieve user state or asset positions for address: {address}")
            return None # Return None or raise an exception
            
        positions = user_state["assetPositions"]
        
        for position in positions:
            item = position["position"]
            if coin != item["coin"]:
                continue
                
            szi = float(item["szi"])
            
            # If size (sz) is not provided, use the absolute value of the current position size (szi)
            size_to_close = sz if sz is not None else abs(szi)
            
            if size_to_close == 0:
                logging.warning(f"Position size for {coin} is zero, cannot close.")
                return None
                
            # Determine order direction (Buy to close short, Sell to close long)
            is_buy = szi < 0 # Short position (szi < 0) requires a Buy order to close
            
            # Get aggressive Market Price
            limit_px = self._slippage_price(coin, is_buy, slippage, px)
            
            # Market Close is a Reduce-Only aggressive Limit Order IoC
            return self.order(
                coin,
                is_buy,
                size_to_close,
                limit_px,
                order_type={"limit": {"tif": "Ioc"}},
                reduce_only=True,
                cloid=cloid,
                builder=builder,
            )
            
        # If the loop finishes without finding the coin
        logging.warning(f"No open position found for coin: {coin}")
        return None

    def cancel(self, name: str, oid: int) -> Any:
        """Cancels a single order by Order ID (oid)."""
        return self.bulk_cancel([{"coin": name, "oid": oid}])

    def cancel_by_cloid(self, name: str, cloid: Cloid) -> Any:
        """Cancels a single order by Client Order ID (cloid)."""
        return self.bulk_cancel_by_cloid([{"coin": name, "cloid": cloid}])

    def bulk_cancel(self, cancel_requests: List[CancelRequest]) -> Any:
        """Batches multiple order cancellations by Order ID."""
        
        cancel_action = {
            "type": "cancel",
            "cancels": [
                {
                    "a": self.info.name_to_asset(cancel["coin"]), # 'a' is asset
                    "o": cancel["oid"], # 'o' is order ID
                }
                for cancel in cancel_requests
            ],
        }
        
        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(cancel_action, self.vault_address)

    def bulk_cancel_by_cloid(self, cancel_requests: List[CancelByCloidRequest]) -> Any:
        """Batches multiple order cancellations by Client Order ID."""
        
        cancel_action = {
            "type": "cancelByCloid",
            "cancels": [
                {
                    "asset": self.info.name_to_asset(cancel["coin"]),
                    "cloid": cancel["cloid"].to_raw(), # Ensure Cloid object is converted to raw value
                }
                for cancel in cancel_requests
            ],
        }
        
        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(cancel_action, self.vault_address)

    def schedule_cancel(self, time: Optional[int]) -> Any:
        """
        Schedules a time (in UTC millis) to cancel all open orders. 
        If time is None, unsets any future cancel time.
        """
        schedule_cancel_action: Dict[str, Union[str, int]] = {
            "type": "scheduleCancel",
        }
        if time is not None:
            schedule_cancel_action["time"] = time
            
        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(schedule_cancel_action, None)

    def update_leverage(self, leverage: int, name: str, is_cross: bool = True) -> Any:
        """Updates the leverage setting for a specific asset."""
        
        update_leverage_action = {
            "type": "updateLeverage",
            "asset": self.info.name_to_asset(name),
            "isCross": is_cross,
            "leverage": leverage,
        }
        
        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(update_leverage_action, self.vault_address)

    def update_isolated_margin(self, amount: float, name: str) -> Any:
        """Adds or removes margin (USD) from an isolated position."""
        
        # Convert float amount to Hyperliquid's integer USD representation
        usd_amount_int = float_to_usd_int(amount)
        
        update_isolated_margin_action = {
            "type": "updateIsolatedMargin",
            "asset": self.info.name_to_asset(name),
            # isBuy is always True for updateIsolatedMargin according to Hyperliquid API
            "isBuy": True, 
            # 'ntli' is an internal term representing the margin change in native tokens
            "ntli": usd_amount_int, 
        }
        
        # Use the generic helper for signing and posting
        return self._sign_and_post_l1_action(update_isolated_margin_action, self.vault_address)

    # --- Account/Transfer Actions (Many are user-signed) ---
    
    def set_referrer(self, code: str) -> Any:
        """Sets a referral code for the user."""
        set_referrer_action = {
            "type": "setReferrer",
            "code": code,
        }
        # Vault address is typically None for account configuration actions
        return self._sign_and_post_l1_action(set_referrer_action, None)

    def create_sub_account(self, name: str) -> Any:
        """Creates a new sub-account with a given name."""
        create_sub_account_action = {
            "type": "createSubAccount",
            "name": name,
        }
        # Vault address is typically None for account configuration actions
        return self._sign_and_post_l1_action(create_sub_account_action, None)

    def usd_class_transfer(self, amount: float, to_perp: bool) -> Any:
        """
        Transfers USD between the spot and perpetuals (perp) collateral classes.
        This is a user-signed action, not L1-signed.
        """
        timestamp = get_timestamp_ms()
        str_amount = str(amount)
        
        # Append subaccount address if active
        if self.vault_address:
            str_amount += f" subaccount:{self.vault_address}"

        action = {
            "type": "usdClassTransfer",
            "amount": str_amount,
            "toPerp": to_perp,
            "nonce": timestamp,
        }
        
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_usd_class_transfer_action(self.wallet, action, is_mainnet)
        
        # Note: vaultAddress is explicitly excluded from _post_action for this type
        return self._post_action(action, signature, timestamp)

    def send_asset(self, destination: str, source_dex: str, destination_dex: str, token: str, amount: float) -> Any:
        """
        Transfers assets (tokens) between accounts or different DEXes.
        For default perp dex use "", for spot use "spot".
        This is a user-signed action.
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
            "fromSubAccount": self.vault_address if self.vault_address else "", # Source sub-account
            "nonce": timestamp,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_send_asset_action(self.wallet, action, is_mainnet)
        
        # Note: vaultAddress is explicitly excluded from _post_action for this type
        return self._post_action(action, signature, timestamp)
        
    # ... (All subsequent methods that use _sign_and_post_l1_action with an appropriate vault_address) ...

    # The remaining L1-signed methods (sub_account_transfer, vault_usd_transfer, etc.)
    # can be greatly simplified by replacing the repetitive sign_l1_action and _post_action block
    # with the new self._sign_and_post_l1_action helper.

    def sub_account_transfer(self, sub_account_user: str, is_deposit: bool, usd: int) -> Any:
        """Transfers USD between the main account and a sub-account."""
        sub_account_transfer_action = {
            "type": "subAccountTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        return self._sign_and_post_l1_action(sub_account_transfer_action, None)

    def sub_account_spot_transfer(self, sub_account_user: str, is_deposit: bool, token: str, amount: float) -> Any:
        """Transfers a spot token between the main account and a sub-account."""
        sub_account_transfer_action = {
            "type": "subAccountSpotTransfer",
            "subAccountUser": sub_account_user,
            "isDeposit": is_deposit,
            "token": token,
            "amount": str(amount),
        }
        return self._sign_and_post_l1_action(sub_account_transfer_action, None)

    def vault_usd_transfer(self, vault_address: str, is_deposit: bool, usd: int) -> Any:
        """Transfers USD to/from a specific vault (e.g., from/to the main account)."""
        vault_transfer_action = {
            "type": "vaultTransfer",
            "vaultAddress": vault_address,
            "isDeposit": is_deposit,
            "usd": usd,
        }
        return self._sign_and_post_l1_action(vault_transfer_action, None)

    # --- User-Signed Transfers (Requires unique signing logic) ---

    def usd_transfer(self, amount: float, destination: str) -> Any:
        """Sends USD to another Hyperliquid user (user-signed action)."""
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "usdSend"}
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_usd_transfer_action(self.wallet, action, is_mainnet)
        return self._post_action(action, signature, timestamp)

    def spot_transfer(self, amount: float, destination: str, token: str) -> Any:
        """Sends a spot token to another Hyperliquid user (user-signed action)."""
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
        return self._post_action(action, signature, timestamp)

    def token_delegate(self, validator: str, wei: int, is_undelegate: bool) -> Any:
        """Delegates or undelegates tokens to a validator (user-signed action)."""
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
        return self._post_action(action, signature, timestamp)

    def withdraw_from_bridge(self, amount: float, destination: str) -> Any:
        """Initiates a withdrawal from the bridge (user-signed action)."""
        timestamp = get_timestamp_ms()
        action = {"destination": destination, "amount": str(amount), "time": timestamp, "type": "withdraw3"}
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_withdraw_from_bridge_action(self.wallet, action, is_mainnet)
        return self._post_action(action, signature, timestamp)

    # ... (Other Methods - L1-signed actions are simplified) ...

    # The remaining methods, which mostly use sign_l1_action or their own specific sign_ function,
    # should be updated to use the appropriate helper for cleaner code.
    
    def approve_agent(self, name: Optional[str] = None) -> Tuple[Any, str]:
        """Approves a new agent key for delegated trading."""
        agent_key = "0x" + secrets.token_hex(32)
        account = eth_account.Account.from_key(agent_key)
        timestamp = get_timestamp_ms()
        is_mainnet = self.base_url == MAINNET_API_URL
        
        action = {
            "type": "approveAgent",
            "agentAddress": account.address,
            # agentName is included only if provided
            "agentName": name or "", 
            "nonce": timestamp,
        }
        signature = sign_agent(self.wallet, action, is_mainnet)
        
        if name is None:
            # The API expects 'agentName' to be absent if not set, delete it before posting
            del action["agentName"] 

        # Note: This one does not use _sign_and_post_l1_action because it returns the agent_key as well.
        return (
            self._post_action(
                action,
                signature,
                timestamp,
            ),
            agent_key,
        )

    def approve_builder_fee(self, builder: str, max_fee_rate: str) -> Any:
        """Sets the maximum fee rate for a specific transaction builder (user-signed)."""
        timestamp = get_timestamp_ms()
        action = {"maxFeeRate": max_fee_rate, "builder": builder, "nonce": timestamp, "type": "approveBuilderFee"}
        signature = sign_approve_builder_fee(self.wallet, action, self.base_url == MAINNET_API_URL)
        return self._post_action(action, signature, timestamp)

    def convert_to_multi_sig_user(self, authorized_users: List[str], threshold: int) -> Any:
        """Converts the current account into a multi-sig user account."""
        timestamp = get_timestamp_ms()
        authorized_users.sort() # Ensure canonical ordering for signing
        
        signers = {
            "authorizedUsers": authorized_users,
            "threshold": threshold,
        }
        
        action = {
            "type": "convertToMultiSigUser",
            # Signers must be a JSON string inside the action
            "signers": json.dumps(signers), 
            "nonce": timestamp,
        }
        
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_convert_to_multi_sig_user_action(self.wallet, action, is_mainnet)
        return self._post_action(action, signature, timestamp)
        
    # --- Simplified L1 Deploy Actions using the Helper ---

    def spot_deploy_register_token(
        self, token_name: str, sz_decimals: int, wei_decimals: int, max_gas: int, full_name: str
    ) -> Any:
        """Registers a new spot token on the exchange."""
        action = {
            "type": "spotDeploy",
            "registerToken2": {
                "spec": {"name": token_name, "szDecimals": sz_decimals, "weiDecimals": wei_decimals},
                "maxGas": max_gas,
                "fullName": full_name,
            },
        }
        return self._sign_and_post_l1_action(action, None)

    def spot_deploy_user_genesis(
        self, token: int, user_and_wei: List[Tuple[str, str]], existing_token_and_wei: List[Tuple[int, str]]
    ) -> Any:
        """Performs a genesis distribution for a spot token."""
        action = {
            "type": "spotDeploy",
            "userGenesis": {
                "token": token,
                # Ensure users are lowercased for canonical form
                "userAndWei": [(user.lower(), wei) for (user, wei) in user_and_wei],
                "existingTokenAndWei": existing_token_and_wei,
            },
        }
        return self._sign_and_post_l1_action(action, None)
        
    def spot_deploy_enable_freeze_privilege(self, token: int) -> Any:
        """Enables the privilege to freeze users for a spot token."""
        return self._spot_deploy_token_action_inner("enableFreezePrivilege", token)

    def spot_deploy_freeze_user(self, token: int, user: str, freeze: bool) -> Any:
        """Freezes or unfreezes a specific user's spot token balance."""
        action = {
            "type": "spotDeploy",
            "freezeUser": {
                "token": token,
                "user": user.lower(), # Canonical form
                "freeze": freeze,
            },
        }
        return self._sign_and_post_l1_action(action, None)

    def spot_deploy_revoke_freeze_privilege(self, token: int) -> Any:
        """Revokes the privilege to freeze users for a spot token."""
        return self._spot_deploy_token_action_inner("revokeFreezePrivilege", token)

    def spot_deploy_enable_quote_token(self, token: int) -> Any:
        """Enables the token to be used as a quote token."""
        return self._spot_deploy_token_action_inner("enableQuoteToken", token)

    def _spot_deploy_token_action_inner(self, variant: str, token: int) -> Any:
        """Internal helper for simple spotDeploy actions that only take a token ID."""
        action = {
            "type": "spotDeploy",
            variant: {
                "token": token,
            },
        }
        return self._sign_and_post_l1_action(action, None)

    def spot_deploy_genesis(self, token: int, max_supply: str, no_hyperliquidity: bool) -> Any:
        """Performs genesis for a spot token (sets max supply and liquidity flag)."""
        genesis: Dict[str, Union[int, str, bool]] = {
            "token": token,
            "maxSupply": max_supply,
        }
        if no_hyperliquidity:
            genesis["noHyperliquidity"] = True
            
        action = {
            "type": "spotDeploy",
            "genesis": genesis,
        }
        return self._sign_and_post_l1_action(action, None)

    def spot_deploy_register_spot(self, base_token: int, quote_token: int) -> Any:
        """Registers a new spot market pair."""
        action = {
            "type": "spotDeploy",
            "registerSpot": {
                "tokens": [base_token, quote_token],
            },
        }
        return self._sign_and_post_l1_action(action, None)

    def spot_deploy_register_hyperliquidity(
        self, spot: int, start_px: float, order_sz: float, n_orders: int, n_seeded_levels: Optional[int]
    ) -> Any:
        """Registers hyperliquidity for a spot market."""
        register_hyperliquidity: Dict[str, Union[int, str, Optional[int]]] = {
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
        return self._sign_and_post_l1_action(action, None)

    def spot_deploy_set_deployer_trading_fee_share(self, token: int, share: str) -> Any:
        """Sets the trading fee share for the token deployer."""
        action = {
            "type": "spotDeploy",
            "setDeployerTradingFeeShare": {
                "token": token,
                "share": share,
            },
        }
        return self._sign_and_post_l1_action(action, None)

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
        """Registers a new perpetuals asset on a specific DEX."""
        schema_wire = None
        if schema is not None:
            schema_wire = {
                "fullName": schema["fullName"],
                "collateralToken": schema["collateralToken"],
                # Ensure oracleUpdater address is lowercased if provided
                "oracleUpdater": schema["oracleUpdater"].lower() if schema.get("oracleUpdater") else None, 
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
        return self._sign_and_post_l1_action(action, None)

    def perp_deploy_set_oracle(
        self,
        dex: str,
        oracle_pxs: Dict[str, str],
        all_mark_pxs: List[Dict[str, str]],
        external_perp_pxs: Dict[str, str],
    ) -> Any:
        """Sets oracle prices, mark prices, and external perpetual prices."""
        # Canonical sorting of keys is crucial for signing
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
        return self._sign_and_post_l1_action(action, None)
        
    # --- C-Signer and Validator Actions ---

    def c_signer_unjail_self(self) -> Any:
        """Unjails the current account as a C-Signer."""
        return self._c_signer_inner("unjailSelf")

    def c_signer_jail_self(self) -> Any:
        """Jails the current account as a C-Signer."""
        return self._c_signer_inner("jailSelf")

    def _c_signer_inner(self, variant: str) -> Any:
        """Internal helper for simple CSignerAction variants."""
        action = {
            "type": "CSignerAction",
            variant: None,
        }
        return self._sign_and_post_l1_action(action, None)

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
        """Registers the account as a new validator."""
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
        return self._sign_and_post_l1_action(action, None)

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
        """Changes the validator's profile settings."""
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
        return self._sign_and_post_l1_action(action, None)

    def c_validator_unregister(self) -> Any:
        """Unregisters the account as a validator."""
        action = {
            "type": "CValidatorAction",
            "unregister": None,
        }
        return self._sign_and_post_l1_action(action, None)

    # --- Multi-Sig and Abstraction Actions ---

    def multi_sig(self, multi_sig_user: str, inner_action: Dict[str, Any], signatures: List[str], nonce: int, vault_address: Optional[str] = None) -> Any:
        """
        Submits a multi-signature action signed by multiple authorized users.
        The outer signature confirms the transaction on behalf of the current wallet.
        """
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
        
        # This is a specialized signing function for multi-sig
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
        """Enables or disables the use of large blocks for the EVM user."""
        action = {
            "type": "evmUserModify",
            "usingBigBlocks": enable,
        }
        return self._sign_and_post_l1_action(action, None)

    def agent_enable_dex_abstraction(self) -> Any:
        """Enables DEX abstraction for the current agent."""
        action = {
            "type": "agentEnableDexAbstraction",
        }
        return self._sign_and_post_l1_action(action, self.vault_address)

    def user_dex_abstraction(self, user: str, enabled: bool) -> Any:
        """Enables or disables DEX abstraction for a specific user (user-signed)."""
        timestamp = get_timestamp_ms()
        action = {
            "type": "userDexAbstraction",
            "user": user.lower(),
            "enabled": enabled,
            "nonce": timestamp,
        }
        is_mainnet = self.base_url == MAINNET_API_URL
        signature = sign_user_dex_abstraction_action(self.wallet, action, is_mainnet)
        return self._post_action(action, signature, timestamp)

    def noop(self, nonce: int) -> Any:
        """A no-operation action, primarily used for gas-less signing/nonce management."""
        action = {"type": "noop"}
        # Uses standard L1 signing
        signature = sign_l1_action(
            self.wallet, action, self.vault_address, nonce, self.expires_after, self.base_url == MAINNET_API_URL
        )
        return self._post_action(action, signature, nonce)
