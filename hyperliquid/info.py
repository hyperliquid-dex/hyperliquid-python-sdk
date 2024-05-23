from hyperliquid.api import API
from hyperliquid.utils.types import Any, Callable, Meta, SpotMeta, Optional, Subscription, cast, Cloid
from hyperliquid.websocket_manager import WebsocketManager


class Info(API):
    def __init__(self, base_url=None, skip_ws=False):
        super().__init__(base_url)
        if not skip_ws:
            self.ws_manager = WebsocketManager(self.base_url)
            self.ws_manager.start()

    def user_state(self, address: str) -> Any:
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
        return self.post("/info", {"type": "clearinghouseState", "user": address})

    def spot_user_state(self, address: str) -> Any:
        return self.post("/info", {"type": "spotClearinghouseState", "user": address})

    def open_orders(self, address: str) -> Any:
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
        return self.post("/info", {"type": "openOrders", "user": address})

    def frontend_open_orders(self, address: str) -> Any:
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
        return self.post("/info", {"type": "frontendOpenOrders", "user": address})

    def all_mids(self) -> Any:
        """Retrieve all mids for all actively traded coins.

        POST /info

        Returns:
            {
              ATOM: float string,
              BTC: float string,
              any other coins which are trading: float string
            }
        """
        return self.post("/info", {"type": "allMids"})

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

    def meta(self) -> Meta:
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
        return cast(Meta, self.post("/info", {"type": "meta"}))

    def spot_meta(self) -> SpotMeta:
        """Retrieve exchange spot metadata

        POST /info

        Returns:
            {
                tokens: [
                    {
                        name: str,
                        szDecimals: int,
                        weiDecimals: int
                    },
                    ...
                ],
                universe: [
                    {
                        name: str,
                        tokens: [int, int]
                    },
                    ...
                ]
            }
        """
        return cast(SpotMeta, self.post("/info", {"type": "spotMeta"}))

    def funding_history(self, coin: str, startTime: int, endTime: Optional[int] = None) -> Any:
        """Retrieve funding history for a given coin

        POST /info

        Args:
            coin (str): Coin to retrieve funding history for.
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

    def l2_snapshot(self, coin: str) -> Any:
        """Retrieve L2 snapshot for a given coin

        POST /info

        Args:
            coin (str): Coin to retrieve L2 snapshot for.

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
        return self.post("/info", {"type": "l2Book", "coin": coin})

    def candles_snapshot(self, coin: str, interval: str, startTime: int, endTime: int) -> Any:
        """Retrieve candles snapshot for a given coin

        POST /info

        Args:
            coin (str): Coin to retrieve candles snapshot for.
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
        req = {"coin": coin, "interval": interval, "startTime": startTime, "endTime": endTime}
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

    def query_order_by_oid(self, user: str, oid: int) -> Any:
        return self.post("/info", {"type": "orderStatus", "user": user, "oid": oid})

    def query_order_by_cloid(self, user: str, cloid: Cloid) -> Any:
        return self.post("/info", {"type": "orderStatus", "user": user, "oid": cloid.to_raw()})

    def query_referral_state(self, user: str) -> Any:
        return self.post("/info", {"type": "referral", "user": user})

    def query_sub_accounts(self, user: str) -> Any:
        return self.post("/info", {"type": "subAccounts", "user": user})

    def subscribe(self, subscription: Subscription, callback: Callable[[Any], None]) -> int:
        if self.ws_manager is None:
            raise RuntimeError("Cannot call subscribe since skip_ws was used")
        else:
            return self.ws_manager.subscribe(subscription, callback)

    def unsubscribe(self, subscription: Subscription, subscription_id: int) -> bool:
        if self.ws_manager is None:
            raise RuntimeError("Cannot call unsubscribe since skip_ws was used")
        else:
            return self.ws_manager.unsubscribe(subscription, subscription_id)
