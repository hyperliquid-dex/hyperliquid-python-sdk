from hyperliquid.api import API
from hyperliquid.utils.types import (
    Any,
    Callable,
    Cloid,
    List,
    Meta,
    Optional,
    SpotMeta,
    SpotMetaAndAssetCtxs,
    Subscription,
    cast,
)
from hyperliquid.websocket_manager import WebsocketManager

class Info(API):
    """
    A client class for querying public and user-specific information from the Hyperliquid exchange.
    Inherits API for REST communication and manages an optional WebsocketManager for real-time data.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        skip_ws: Optional[bool] = False,
        meta: Optional[Meta] = None,
        spot_meta: Optional[SpotMeta] = None,
        # Note: "" represents the original/default perp dex.
        perp_dexs: Optional[List[str]] = None, 
        timeout: Optional[float] = None,
    ):
        super().__init__(base_url, timeout)
        
        self.ws_manager: Optional[WebsocketManager] = None
        self._initialize_websocket(skip_ws)

        # Asset Mapping Dictionaries
        self.coin_to_asset: dict[str, int] = {}       # Maps coin name (str) to asset index (int)
        self.name_to_coin: dict[str, str] = {}        # Maps verbose name (e.g., 'BTC/USD') to coin name (e.g., 'BTC')
        self.asset_to_sz_decimals: dict[int, int] = {} # Maps asset index (int) to size decimals (int)

        # Initialize Asset Mappings
        self._map_spot_assets(spot_meta)
        self._map_perp_assets(meta, perp_dexs)

    def _initialize_websocket(self, skip_ws: Optional[bool]) -> None:
        """Initializes and starts the WebSocket Manager."""
        if not skip_ws:
            self.ws_manager = WebsocketManager(self.base_url)
            self.ws_manager.start()

    def _map_spot_assets(self, spot_meta: Optional[SpotMeta]) -> None:
        """Populates mapping dictionaries for spot assets (starting at offset 10000)."""
        if spot_meta is None:
            spot_meta = self.spot_meta()

        # spot assets start at 10000
        for spot_info in spot_meta["universe"]:
            asset = spot_info["index"] + 10000
            self.coin_to_asset[spot_info["name"]] = asset
            self.name_to_coin[spot_info["name"]] = spot_info["name"]
            
            # Extract token details to create verbose name mapping (e.g., ETH/USD)
            base_index, quote_index = spot_info["tokens"]
            base_info = spot_meta["tokens"][base_index]
            quote_info = spot_meta["tokens"][quote_index]
            
            self.asset_to_sz_decimals[asset] = base_info["szDecimals"]
            name = f'{base_info["name"]}/{quote_info["name"]}'
            if name not in self.name_to_coin:
                self.name_to_coin[name] = spot_info["name"]

    def _map_perp_assets(self, meta: Optional[Meta], perp_dex_list: Optional[List[str]]) -> None:
        """Populates mapping dictionaries for perpetual assets, handling multiple DEXs and offsets."""
        
        perp_dex_to_offset = {"": 0} # Default/original dex has offset 0
        
        # Calculate offsets for builder-deployed perpetual DEXs
        if perp_dex_list is None:
            perp_dex_list = [""]
        
        perp_dex_infos = self.perp_dexs()
        
        if len(perp_dex_infos) > 1:
            # Builder-deployed perp dexs start at 110000, incremented by 10000
            for i, perp_dex in enumerate(perp_dex_infos[1:]):
                perp_dex_to_offset[perp_dex["name"]] = 110000 + i * 10000

        # Process metadata for each specified perp DEX
        for perp_dex in perp_dex_list:
            offset = perp_dex_to_offset[perp_dex]
            
            # Fetch metadata if not provided (or for non-default DEXs)
            fresh_meta = meta if perp_dex == "" and meta is not None else self.meta(dex=perp_dex)
            
            if fresh_meta is not None:
                self.set_perp_meta(fresh_meta, offset)

    def set_perp_meta(self, meta: Meta, offset: int) -> None:
        """Helper to set mappings for a specific perpetual exchange's metadata."""
        for asset, asset_info in enumerate(meta["universe"]):
            asset += offset
            self.coin_to_asset[asset_info["name"]] = asset
            self.name_to_coin[asset_info["name"]] = asset_info["name"]
            self.asset_to_sz_decimals[asset] = asset_info["szDecimals"]

    def disconnect_websocket(self) -> None:
        """Stops and closes the WebSocket connection."""
        if self.ws_manager is None:
            raise RuntimeError("Cannot call disconnect_websocket since skip_ws was used")
        self.ws_manager.stop()

    # --- REST API Methods (POST /info) ---

    def user_state(self, address: str, dex: str = "") -> Any:
        """
        Retrieve trading details about a user's perpetual and cross margin state.

        POST /info
        
        Args:
            address (str): Onchain address (42-character hex).
            dex (str): Perpetual DEX name (defaults to original "").
        
        Returns:
            Dict[str, Any]: User's asset positions, margin summaries, and withdrawable funds.
        """
        return self.post("/info", {"type": "clearinghouseState", "user": address, "dex": dex})

    def spot_user_state(self, address: str) -> Any:
        """Retrieve trading details about a user's spot clearinghouse state. POST /info"""
        return self.post("/info", {"type": "spotClearinghouseState", "user": address})

    def open_orders(self, address: str, dex: str = "") -> Any:
        """
        Retrieve a user's open orders (standard format).

        POST /info
        
        Args:
            address (str): Onchain address (42-character hex).
            dex (str): Perpetual DEX name (defaults to original "").
            
        Returns: 
            List[Dict]: Basic details of open orders.
        """
        return self.post("/info", {"type": "openOrders", "user": address, "dex": dex})

    def frontend_open_orders(self, address: str, dex: str = "") -> Any:
        """
        Retrieve a user's open orders with additional frontend/UI-focused details (e.g., children, orderType).
        POST /info
        """
        return self.post("/info", {"type": "frontendOpenOrders", "user": address, "dex": dex})

    def all_mids(self, dex: str = "") -> Any:
        """
        Retrieve all mids (mid-prices) for all actively traded coins.
        POST /info
        
        Returns:
            Dict[str, float string]: Mapping of coin name to mid-price.
        """
        return self.post("/info", {"type": "allMids", "dex": dex})

    def user_fills(self, address: str) -> Any:
        """Retrieve a given user's fills. POST /info"""
        return self.post("/info", {"type": "userFills", "user": address})

    def user_fills_by_time(
        self, 
        address: str, 
        start_time: int, 
        end_time: Optional[int] = None, 
        aggregate_by_time: Optional[bool] = False
    ) -> Any:
        """Retrieve a given user's fills within a time range, with optional aggregation. POST /info"""
        return self.post(
            "/info",
            {
                "type": "userFillsByTime",
                "user": address,
                "startTime": start_time,
                "endTime": end_time,
                "aggregateByTime": aggregate_by_time,
            },
        )

    def meta(self, dex: str = "") -> Meta:
        """
        Retrieve exchange perpetual metadata (universe, szDecimals).
        POST /info
        """
        return cast(Meta, self.post("/info", {"type": "meta", "dex": dex}))

    def meta_and_asset_ctxs(self) -> Any:
        """
        Retrieve exchange MetaAndAssetCtxs (metadata plus current asset context metrics like mark price, funding, open interest).
        POST /info
        """
        return self.post("/info", {"type": "metaAndAssetCtxs"})

    def perp_dexs(self) -> Any:
        """Retrieve a list of all deployed perpetual DEXs. POST /info"""
        return self.post("/info", {"type": "perpDexs"})

    def spot_meta(self) -> SpotMeta:
        """Retrieve exchange spot metadata (universe, tokens). POST /info"""
        return cast(SpotMeta, self.post("/info", {"type": "spotMeta"}))

    def spot_meta_and_asset_ctxs(self) -> SpotMetaAndAssetCtxs:
        """Retrieve exchange spot asset contexts (metadata plus spot metrics). POST /info"""
        return cast(SpotMetaAndAssetCtxs, self.post("/info", {"type": "spotMetaAndAssetCtxs"}))

    def funding_history(self, name: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve funding history for a given coin name within a time range. POST /info"""
        coin = self.name_to_coin[name]
        request_params = {"type": "fundingHistory", "coin": coin, "startTime": startTime}
        if endTime is not None:
            request_params["endTime"] = endTime
        return self.post("/info", request_params)

    def user_funding_history(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve a user's funding history within a time range. POST /info"""
        request_params = {"type": "userFunding", "user": user, "startTime": startTime}
        if endTime is not None:
            request_params["endTime"] = endTime
        return self.post("/info", request_params)

    def l2_snapshot(self, name: str) -> Any:
        """Retrieve L2 order book snapshot for a given coin. POST /info"""
        return self.post("/info", {"type": "l2Book", "coin": self.name_to_coin[name]})

    def candles_snapshot(self, name: str, interval: str, startTime: int, endTime: int) -> Any:
        """Retrieve candlestick data for a given coin, interval, and time range. POST /info"""
        req = {"coin": self.name_to_coin[name], "interval": interval, "startTime": startTime, "endTime": endTime}
        return self.post("/info", {"type": "candleSnapshot", "req": req})

    def user_fees(self, address: str) -> Any:
        """Retrieve the volume and fee schedule associated with a user. POST /info"""
        return self.post("/info", {"type": "userFees", "user": address})

    def user_staking_summary(self, address: str) -> Any:
        """Retrieve the staking summary (delegated, undelegated) associated with a user. POST /info"""
        return self.post("/info", {"type": "delegatorSummary", "user": address})

    def user_staking_delegations(self, address: str) -> Any:
        """Retrieve the user's current staking delegations. POST /info"""
        return self.post("/info", {"type": "delegations", "user": address})

    def user_staking_rewards(self, address: str) -> Any:
        """Retrieve the historic staking rewards associated with a user. POST /info"""
        return self.post("/info", {"type": "delegatorRewards", "user": address})

    def delegator_history(self, user: str) -> Any:
        """Retrieve comprehensive staking history (delegation/undelegation events) for a user. POST /info"""
        return self.post("/info", {"type": "delegatorHistory", "user": user})

    def query_order_by_oid(self, user: str, oid: int) -> Any:
        """Retrieve the status of a specific order by its Order ID (oid). POST /info"""
        return self.post("/info", {"type": "orderStatus", "user": user, "oid": oid})

    def query_order_by_cloid(self, user: str, cloid: Cloid) -> Any:
        """Retrieve the status of a specific order by its Client Order ID (cloid). POST /info"""
        return self.post("/info", {"type": "orderStatus", "user": user, "oid": cloid.to_raw()})

    def query_referral_state(self, user: str) -> Any:
        """Retrieve the user's referral state and rewards information. POST /info"""
        return self.post("/info", {"type": "referral", "user": user})

    def query_sub_accounts(self, user: str) -> Any:
        """Retrieve sub-accounts associated with a master account. POST /info"""
        return self.post("/info", {"type": "subAccounts", "user": user})

    def query_user_to_multi_sig_signers(self, multi_sig_user: str) -> Any:
        """Retrieve the signers for a multi-sig user account. POST /info"""
        return self.post("/info", {"type": "userToMultiSigSigners", "user": multi_sig_user})

    def query_perp_deploy_auction_status(self) -> Any:
        """Retrieve the status of the perpetual deployment auction. POST /info"""
        return self.post("/info", {"type": "perpDeployAuctionStatus"})

    def query_user_dex_abstraction_state(self, user: str) -> Any:
        """Retrieve a user's DEX abstraction state (used for specific trading features). POST /info"""
        return self.post("/info", {"type": "userDexAbstraction", "user": user})

    def query_user_abstraction_state(self, user: str) -> Any:
        return self.post("/info", {"type": "userAbstraction", "user": user})

    def historical_orders(self, user: str) -> Any:
        """Retrieve a user's most recent historical orders (max 2000). POST /info"""
        return self.post("/info", {"type": "historicalOrders", "user": user})

    def user_non_funding_ledger_updates(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve non-funding ledger updates (deposits, withdrawals, liquidations, etc.) for a user within a time range. POST /info"""
        return self.post(
            "/info",
            {"type": "userNonFundingLedgerUpdates", "user": user, "startTime": startTime, "endTime": endTime},
        )

    def portfolio(self, user: str) -> Any:
        """Retrieve comprehensive portfolio performance data, including PnL and volume metrics. POST /info"""
        return self.post("/info", {"type": "portfolio", "user": user})

    def user_twap_slice_fills(self, user: str) -> Any:
        """Retrieve a user's Time-Weighted Average Price (TWAP) slice fills. POST /info"""
        return self.post("/info", {"type": "userTwapSliceFills", "user": user})

    def user_vault_equities(self, user: str) -> Any:
        """Retrieve user's equity positions across all vaults. POST /info"""
        return self.post("/info", {"type": "userVaultEquities", "user": user})

    def user_role(self, user: str) -> Any:
        """Retrieve the role and account type information for a user. POST /info"""
        return self.post("/info", {"type": "userRole", "user": user})

    def user_rate_limit(self, user: str) -> Any:
        """Retrieve user's API rate limit configuration and current usage. POST /info"""
        return self.post("/info", {"type": "userRateLimit", "user": user})

    def query_spot_deploy_auction_status(self, user: str) -> Any:
        """Retrieve the status of the spot deployment auction. POST /info"""
        return self.post("/info", {"type": "spotDeployState", "user": user})

    def extra_agents(self, user: str) -> Any:
        """Retrieve extra agents (e.g., delegated trading accounts) associated with a user. POST /info"""
        return self.post("/info", {"type": "extraAgents", "user": user})

    # --- WebSocket Helper Methods ---

    def _remap_coin_subscription(self, subscription: Subscription) -> None:
        """Helper to replace coin name with the canonical coin string for WebSocket subscriptions."""
        if subscription["type"] in ("l2Book", "trades", "candle", "bbo", "activeAssetCtx"):
            subscription["coin"] = self.name_to_coin[subscription["coin"]]

    def subscribe(self, subscription: Subscription, callback: Callable[[Any], None]) -> int:
        """Subscribes to a real-time data stream via WebSocket."""
        self._remap_coin_subscription(subscription)
        if self.ws_manager is None:
            raise RuntimeError("Cannot call subscribe since skip_ws was used")
        return self.ws_manager.subscribe(subscription, callback)

    def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        """Unsubscribes from a real-time data stream via WebSocket."""
        self._remap_coin_subscription(subscription)
        if self.ws_manager is None:
            raise RuntimeError("Cannot call unsubscribe since skip_ws was used")
        return self.ws_manager.unsubscribe(subscription, subscription_id)

    def name_to_asset(self, name: str) -> int:
        """Converts a coin name (e.g., 'BTC', 'ETH/USD') into its unique integer asset index."""
        return self.coin_to_asset[self.name_to_coin[name]]
