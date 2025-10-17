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
    def __init__(
        self,
        base_url: Optional[str] = None,
        skip_ws: Optional[bool] = False,
        meta: Optional[Meta] = None,
        spot_meta: Optional[SpotMeta] = None,
        # Note that when perp_dexs is None, then "" is used as the perp dex. "" represents
        # the original dex.
        perp_dexs: Optional[List[str]] = None,
        timeout: Optional[float] = None,
    ):  # pylint: disable=too-many-locals
        super().__init__(base_url, timeout)
        self.ws_manager: Optional[WebsocketManager] = None
        if not skip_ws:
            self.ws_manager = WebsocketManager(self.base_url)
            self.ws_manager.start()

        if spot_meta is None:
            spot_meta = self.spot_meta()

        self.coin_to_asset = {}
        self.name_to_coin = {}
        self.asset_to_sz_decimals = {}

        # spot assets start at 10000
        for spot_info in spot_meta["universe"]:
            asset = spot_info["index"] + 10000
            self.coin_to_asset[spot_info["name"]] = asset
            self.name_to_coin[spot_info["name"]] = spot_info["name"]
            base, quote = spot_info["tokens"]
            base_info = spot_meta["tokens"][base]
            quote_info = spot_meta["tokens"][quote]
            self.asset_to_sz_decimals[asset] = base_info["szDecimals"]
            name = f'{base_info["name"]}/{quote_info["name"]}'
            if name not in self.name_to_coin:
                self.name_to_coin[name] = spot_info["name"]

        perp_dex_to_offset = {"": 0}
        if perp_dexs is None:
            perp_dexs = [""]
        else:
            for i, perp_dex in enumerate(self.perp_dexs()[1:]):
                # builder-deployed perp dexs start at 110000
                perp_dex_to_offset[perp_dex["name"]] = 110000 + i * 10000

        for perp_dex in perp_dexs:
            offset = perp_dex_to_offset[perp_dex]
            if perp_dex == "" and meta is not None:
                self.set_perp_meta(meta, 0)
            else:
                fresh_meta = self.meta(dex=perp_dex)
                self.set_perp_meta(fresh_meta, offset)

    def set_perp_meta(self, meta: Meta, offset: int) -> Any:
        for asset, asset_info in enumerate(meta["universe"]):
            asset += offset
            self.coin_to_asset[asset_info["name"]] = asset
            self.name_to_coin[asset_info["name"]] = asset_info["name"]
            self.asset_to_sz_decimals[asset] = asset_info["szDecimals"]

    def disconnect_websocket(self):
        if self.ws_manager is None:
            raise RuntimeError("Cannot call disconnect_websocket since skip_ws was used")
        else:
            self.ws_manager.stop()

    def user_state(self, address: str, dex: str = "") -> Any:
        """Retrieve trading details about a user.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            {
                assetPositions: [
                    {
                        position: {
                            coin: str,
                            entryPx: Optional[float string]
                            leverage: {
                                type: "cross" | "isolated",
                                value: int,
                                rawUsd: float string  # only if type is "isolated"
                            },
                            liquidationPx: Optional[float string]
                            marginUsed: float string,
                            positionValue: float string,
                            returnOnEquity: float string,
                            szi: float string,
                            unrealizedPnl: float string
                        },
                        type: "oneWay"
                    }
                ],
                crossMarginSummary: MarginSummary,
                marginSummary: MarginSummary,
                withdrawable: float string,
            }

            where MarginSummary is {
                    accountValue: float string,
                    totalMarginUsed: float string,
                    totalNtlPos: float string,
                    totalRawUsd: float string,
                }
        """
        return self.post("/info", {"type": "clearinghouseState", "user": address, "dex": dex})

    def spot_user_state(self, address: str) -> Any:
        return self.post("/info", {"type": "spotClearinghouseState", "user": address})

    def open_orders(self, address: str, dex: str = "") -> Any:
        """Retrieve a user's open orders.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns: [
            {
                coin: str,
                limitPx: float string,
                oid: int,
                side: "A" | "B",
                sz: float string,
                timestamp: int
            }
        ]
        """
        return self.post("/info", {"type": "openOrders", "user": address, "dex": dex})

    def frontend_open_orders(self, address: str, dex: str = "") -> Any:
        """Retrieve a user's open orders with additional frontend info.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns: [
            {
                children:
                    [
                        dict of frontend orders
                    ]
                coin: str,
                isPositionTpsl: bool,
                isTrigger: bool,
                limitPx: float string,
                oid: int,
                orderType: str,
                origSz: float string,
                reduceOnly: bool,
                side: "A" | "B",
                sz: float string,
                tif: str,
                timestamp: int,
                triggerCondition: str,
                triggerPx: float str
            }
        ]
        """
        return self.post("/info", {"type": "frontendOpenOrders", "user": address, "dex": dex})

    def all_mids(self, dex: str = "") -> Any:
        """Retrieve all mids for all actively traded coins.

        POST /info

        Returns:
            {
              ATOM: float string,
              BTC: float string,
              any other coins which are trading: float string
            }
        """
        return self.post("/info", {"type": "allMids", "dex": dex})

    def user_fills(self, address: str) -> Any:
        """Retrieve a given user's fills.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.

        Returns:
            [
              {
                closedPnl: float string,
                coin: str,
                crossed: bool,
                dir: str,
                hash: str,
                oid: int,
                px: float string,
                side: str,
                startPosition: float string,
                sz: float string,
                time: int
              },
              ...
            ]
        """
        return self.post("/info", {"type": "userFills", "user": address})

    def user_fills_by_time(
        self, address: str, start_time: int, end_time: Optional[int] = None, aggregate_by_time: Optional[bool] = False
    ) -> Any:
        """Retrieve a given user's fills by time.

        POST /info

        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
            start_time (int): Unix timestamp in milliseconds
            end_time (Optional[int]): Unix timestamp in milliseconds
            aggregate_by_time (Optional[bool]): When true, partial fills are combined when a crossing order gets filled by multiple different resting orders. Resting orders filled by multiple crossing orders will not be aggregated.

        Returns:
            [
              {
                closedPnl: float string,
                coin: str,
                crossed: bool,
                dir: str,
                hash: str,
                oid: int,
                px: float string,
                side: str,
                startPosition: float string,
                sz: float string,
                time: int
              },
              ...
            ]
        """
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
        """Retrieve exchange perp metadata

        POST /info

        Returns:
            {
                universe: [
                    {
                        name: str,
                        szDecimals: int
                    },
                    ...
                ]
            }
        """
        return cast(Meta, self.post("/info", {"type": "meta", "dex": dex}))

    def meta_and_asset_ctxs(self) -> Any:
        """Retrieve exchange MetaAndAssetCtxs

        POST /info

        Returns:
            [
                {
                    universe: [
                        {
                            'name': str,
                            'szDecimals': int
                            'maxLeverage': int,
                            'onlyIsolated': bool,
                        },
                        ...
                    ]
                },
            [
                {
                    "dayNtlVlm": float string,
                    "funding": float string,
                    "impactPxs": Optional([float string, float string]),
                    "markPx": Optional(float string),
                    "midPx": Optional(float string),
                    "openInterest": float string,
                    "oraclePx": float string,
                    "premium": Optional(float string),
                    "prevDayPx": float string
                },
                ...
            ]
        """
        return self.post("/info", {"type": "metaAndAssetCtxs"})

    def perp_dexs(self) -> Any:
        return self.post("/info", {"type": "perpDexs"})

    def spot_meta(self) -> SpotMeta:
        """Retrieve exchange spot metadata

        POST /info

        Returns:
            {
                universe: [
                    {
                        tokens: [int, int],
                        name: str,
                        index: int,
                        isCanonical: bool
                    },
                    ...
                ],
                tokens: [
                    {
                        name: str,
                        szDecimals: int,
                        weiDecimals: int,
                        index: int,
                        tokenId: str,
                        isCanonical: bool
                    },
                    ...
                ]
            }
        """
        return cast(SpotMeta, self.post("/info", {"type": "spotMeta"}))

    def spot_meta_and_asset_ctxs(self) -> SpotMetaAndAssetCtxs:
        """Retrieve exchange spot asset contexts
        POST /info
        Returns:
            [
                {
                    universe: [
                        {
                            tokens: [int, int],
                            name: str,
                            index: int,
                            isCanonical: bool
                        },
                        ...
                    ],
                    tokens: [
                        {
                            name: str,
                            szDecimals: int,
                            weiDecimals: int,
                            index: int,
                            tokenId: str,
                            isCanonical: bool
                        },
                        ...
                    ]
                },
                [
                    {
                        dayNtlVlm: float string,
                        markPx: float string,
                        midPx: Optional(float string),
                        prevDayPx: float string,
                        circulatingSupply: float string,
                        coin: str
                    }
                    ...
                ]
            ]
        """
        return cast(SpotMetaAndAssetCtxs, self.post("/info", {"type": "spotMetaAndAssetCtxs"}))

    def funding_history(self, name: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve funding history for a given coin

        POST /info

        Args:
            name (str): Coin to retrieve funding history for.
            startTime (int): Unix timestamp in milliseconds.
            endTime (int): Unix timestamp in milliseconds.

        Returns:
            [
                {
                    coin: str,
                    fundingRate: float string,
                    premium: float string,
                    time: int
                },
                ...
            ]
        """
        coin = self.name_to_coin[name]
        if endTime is not None:
            return self.post(
                "/info", {"type": "fundingHistory", "coin": coin, "startTime": startTime, "endTime": endTime}
            )
        return self.post("/info", {"type": "fundingHistory", "coin": coin, "startTime": startTime})

    def user_funding_history(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve a user's funding history
        POST /info
        Args:
            user (str): Address of the user in 42-character hexadecimal format.
            startTime (int): Start time in milliseconds, inclusive.
            endTime (int, optional): End time in milliseconds, inclusive. Defaults to current time.
        Returns:
            List[Dict]: A list of funding history records, where each record contains:
                - user (str): User address.
                - type (str): Type of the record, e.g., "userFunding".
                - startTime (int): Unix timestamp of the start time in milliseconds.
                - endTime (int): Unix timestamp of the end time in milliseconds.
        """
        if endTime is not None:
            return self.post("/info", {"type": "userFunding", "user": user, "startTime": startTime, "endTime": endTime})
        return self.post("/info", {"type": "userFunding", "user": user, "startTime": startTime})

    def l2_snapshot(self, name: str) -> Any:
        """Retrieve L2 snapshot for a given coin

        POST /info

        Args:
            name (str): Coin to retrieve L2 snapshot for.

        Returns:
            {
                coin: str,
                levels: [
                    [
                        {
                            n: int,
                            px: float string,
                            sz: float string
                        },
                        ...
                    ],
                    ...
                ],
                time: int
            }
        """
        return self.post("/info", {"type": "l2Book", "coin": self.name_to_coin[name]})

    def candles_snapshot(self, name: str, interval: str, startTime: int, endTime: int) -> Any:
        """Retrieve candles snapshot for a given coin

        POST /info

        Args:
            name (str): Coin to retrieve candles snapshot for.
            interval (str): Candlestick interval.
            startTime (int): Unix timestamp in milliseconds.
            endTime (int): Unix timestamp in milliseconds.

        Returns:
            [
                {
                    T: int,
                    c: float string,
                    h: float string,
                    i: str,
                    l: float string,
                    n: int,
                    o: float string,
                    s: string,
                    t: int,
                    v: float string
                },
                ...
            ]
        """
        req = {"coin": self.name_to_coin[name], "interval": interval, "startTime": startTime, "endTime": endTime}
        return self.post("/info", {"type": "candleSnapshot", "req": req})

    def user_fees(self, address: str) -> Any:
        """Retrieve the volume of trading activity associated with a user.
        POST /info
        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            {
                activeReferralDiscount: float string,
                dailyUserVlm: [
                    {
                        date: str,
                        exchange: str,
                        userAdd: float string,
                        userCross: float string
                    },
                ],
                feeSchedule: {
                    add: float string,
                    cross: float string,
                    referralDiscount: float string,
                    tiers: {
                        mm: [
                            {
                                add: float string,
                                makerFractionCutoff: float string
                            },
                        ],
                        vip: [
                            {
                                add: float string,
                                cross: float string,
                                ntlCutoff: float string
                            },
                        ]
                    }
                },
                userAddRate: float string,
                userCrossRate: float string
            }
        """
        return self.post("/info", {"type": "userFees", "user": address})

    def user_staking_summary(self, address: str) -> Any:
        """Retrieve the staking summary associated with a user.
        POST /info
        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            {
                delegated: float string,
                undelegated: float string,
                totalPendingWithdrawal: float string,
                nPendingWithdrawals: int
            }
        """
        return self.post("/info", {"type": "delegatorSummary", "user": address})

    def user_staking_delegations(self, address: str) -> Any:
        """Retrieve the user's staking delegations.
        POST /info
        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            [
                {
                    validator: string,
                    amount: float string,
                    lockedUntilTimestamp: int
                },
            ]
        """
        return self.post("/info", {"type": "delegations", "user": address})

    def user_staking_rewards(self, address: str) -> Any:
        """Retrieve the historic staking rewards associated with a user.
        POST /info
        Args:
            address (str): Onchain address in 42-character hexadecimal format;
                            e.g. 0x0000000000000000000000000000000000000000.
        Returns:
            [
                {
                    time: int,
                    source: string,
                    totalAmount: float string
                },
            ]
        """
        return self.post("/info", {"type": "delegatorRewards", "user": address})

    def delegator_history(self, user: str) -> Any:
        """Retrieve comprehensive staking history for a user.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.

        Returns:
            Comprehensive staking history including delegation and undelegation
            events with timestamps, transaction hashes, and detailed delta information.
        """
        return self.post("/info", {"type": "delegatorHistory", "user": user})

    def query_order_by_oid(self, user: str, oid: int) -> Any:
        return self.post("/info", {"type": "orderStatus", "user": user, "oid": oid})

    def query_order_by_cloid(self, user: str, cloid: Cloid) -> Any:
        return self.post("/info", {"type": "orderStatus", "user": user, "oid": cloid.to_raw()})

    def query_referral_state(self, user: str) -> Any:
        return self.post("/info", {"type": "referral", "user": user})

    def query_sub_accounts(self, user: str) -> Any:
        return self.post("/info", {"type": "subAccounts", "user": user})

    def query_user_to_multi_sig_signers(self, multi_sig_user: str) -> Any:
        return self.post("/info", {"type": "userToMultiSigSigners", "user": multi_sig_user})

    def query_perp_deploy_auction_status(self) -> Any:
        return self.post("/info", {"type": "perpDeployAuctionStatus"})

    def query_user_dex_abstraction_state(self, user: str) -> Any:
        return self.post("/info", {"type": "userDexAbstraction", "user": user})

    def historical_orders(self, user: str) -> Any:
        """Retrieve a user's historical orders.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format;
                        e.g. 0x0000000000000000000000000000000000000000.

        Returns:
            Returns at most 2000 most recent historical orders with their current
            status and detailed order information.
        """
        return self.post("/info", {"type": "historicalOrders", "user": user})

    def user_non_funding_ledger_updates(self, user: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve non-funding ledger updates for a user.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.
            startTime (int): Start time in milliseconds (epoch timestamp).
            endTime (Optional[int]): End time in milliseconds (epoch timestamp).

        Returns:
            Comprehensive ledger updates including deposits, withdrawals, transfers,
            liquidations, and other account activities excluding funding payments.
        """
        return self.post(
            "/info",
            {"type": "userNonFundingLedgerUpdates", "user": user, "startTime": startTime, "endTime": endTime},
        )

    def portfolio(self, user: str) -> Any:
        """Retrieve comprehensive portfolio performance data.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.

        Returns:
            Comprehensive portfolio performance data across different time periods,
            including account value history, PnL history, and volume metrics.
        """
        return self.post("/info", {"type": "portfolio", "user": user})

    def user_twap_slice_fills(self, user: str) -> Any:
        """Retrieve a user's TWAP slice fills.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.

        Returns:
            Returns at most 2000 most recent TWAP slice fills with detailed
            execution information.
        """
        return self.post("/info", {"type": "userTwapSliceFills", "user": user})

    def user_vault_equities(self, user: str) -> Any:
        """Retrieve user's equity positions across all vaults.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.

        Returns:
            Detailed information about user's equity positions across all vaults
            including current values, profit/loss metrics, and withdrawal details.
        """
        return self.post("/info", {"type": "userVaultEquities", "user": user})

    def user_role(self, user: str) -> Any:
        """Retrieve the role and account type information for a user.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.

        Returns:
            Role and account type information including account structure,
            permissions, and relationships within the Hyperliquid ecosystem.
        """
        return self.post("/info", {"type": "userRole", "user": user})

    def user_rate_limit(self, user: str) -> Any:
        """Retrieve user's API rate limit configuration and usage.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format.

        Returns:
            Detailed information about user's API rate limit configuration
            and current usage for managing API usage and avoiding rate limiting.
        """
        return self.post("/info", {"type": "userRateLimit", "user": user})

    def query_spot_deploy_auction_status(self, user: str) -> Any:
        return self.post("/info", {"type": "spotDeployState", "user": user})

    def extra_agents(self, user: str) -> Any:
        """Retrieve extra agents associated with a user.

        POST /info

        Args:
            user (str): Onchain address in 42-character hexadecimal format;
                        e.g. 0x0000000000000000000000000000000000000000.

        Returns:
            [
                {
                    "name": str,
                    "address": str,
                    "validUntil": int
                },
                ...
            ]
        """
        return self.post("/info", {"type": "extraAgents", "user": user})

    def _remap_coin_subscription(self, subscription: Subscription) -> None:
        if (
            subscription["type"] == "l2Book"
            or subscription["type"] == "trades"
            or subscription["type"] == "candle"
            or subscription["type"] == "bbo"
            or subscription["type"] == "activeAssetCtx"
        ):
            subscription["coin"] = self.name_to_coin[subscription["coin"]]

    def subscribe(self, subscription: Subscription, callback: Callable[[Any], None]) -> int:
        self._remap_coin_subscription(subscription)
        if self.ws_manager is None:
            raise RuntimeError("Cannot call subscribe since skip_ws was used")
        else:
            return self.ws_manager.subscribe(subscription, callback)

    def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        self._remap_coin_subscription(subscription)
        if self.ws_manager is None:
            raise RuntimeError("Cannot call unsubscribe since skip_ws was used")
        else:
            return self.ws_manager.unsubscribe(subscription, subscription_id)

    def name_to_asset(self, name: str) -> int:
        return self.coin_to_asset[self.name_to_coin[name]]
