from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal, NamedTuple, Optional, Tuple, TypedDict, Union, cast
from typing_extensions import NotRequired

Any = Any
Option = Optional
cast = cast
Callable = Callable
NamedTuple = NamedTuple
NotRequired = NotRequired

AssetInfo = TypedDict("AssetInfo", {"name": str, "szDecimals": int})
Meta = TypedDict("Meta", {"universe": List[AssetInfo]})
Side = Union[Literal["A"], Literal["B"]]
SIDES: List[Side] = ["A", "B"]

SpotAssetInfo = TypedDict("SpotAssetInfo", {"name": str, "tokens": List[int], "index": int, "isCanonical": bool})
SpotTokenInfo = TypedDict(
    "SpotTokenInfo",
    {
        "name": str,
        "szDecimals": int,
        "weiDecimals": int,
        "index": int,
        "tokenId": str,
        "isCanonical": bool,
        "evmContract": Optional[str],
        "fullName": Optional[str],
    },
)
SpotMeta = TypedDict("SpotMeta", {"universe": List[SpotAssetInfo], "tokens": List[SpotTokenInfo]})
SpotAssetCtx = TypedDict(
    "SpotAssetCtx",
    {"dayNtlVlm": str, "markPx": str, "midPx": Optional[str], "prevDayPx": str, "circulatingSupply": str, "coin": str},
)
SpotMetaAndAssetCtxs = Tuple[SpotMeta, List[SpotAssetCtx]]

AllMidsSubscription = TypedDict("AllMidsSubscription", {"type": Literal["allMids"]})
BboSubscription = TypedDict("BboSubscription", {"type": Literal["bbo"], "coin": str})
L2BookSubscription = TypedDict("L2BookSubscription", {"type": Literal["l2Book"], "coin": str})
TradesSubscription = TypedDict("TradesSubscription", {"type": Literal["trades"], "coin": str})
UserEventsSubscription = TypedDict("UserEventsSubscription", {"type": Literal["userEvents"], "user": str})
UserFillsSubscription = TypedDict("UserFillsSubscription", {"type": Literal["userFills"], "user": str})
CandleSubscription = TypedDict("CandleSubscription", {"type": Literal["candle"], "coin": str, "interval": str})
OrderUpdatesSubscription = TypedDict("OrderUpdatesSubscription", {"type": Literal["orderUpdates"], "user": str})
UserFundingsSubscription = TypedDict("UserFundingsSubscription", {"type": Literal["userFundings"], "user": str})
UserNonFundingLedgerUpdatesSubscription = TypedDict(
    "UserNonFundingLedgerUpdatesSubscription", {"type": Literal["userNonFundingLedgerUpdates"], "user": str}
)
WebData2Subscription = TypedDict("WebData2Subscription", {"type": Literal["webData2"], "user": str})
ActiveAssetCtxSubscription = TypedDict("ActiveAssetCtxSubscription", {"type": Literal["activeAssetCtx"], "coin": str})
ActiveAssetDataSubscription = TypedDict(
    "ActiveAssetDataSubscription", {"type": Literal["activeAssetData"], "user": str, "coin": str}
)
# If adding new subscription types that contain coin's don't forget to handle automatically rewrite name to coin in info.subscribe
Subscription = Union[
    AllMidsSubscription,
    BboSubscription,
    L2BookSubscription,
    TradesSubscription,
    UserEventsSubscription,
    UserFillsSubscription,
    CandleSubscription,
    OrderUpdatesSubscription,
    UserFundingsSubscription,
    UserNonFundingLedgerUpdatesSubscription,
    WebData2Subscription,
    ActiveAssetCtxSubscription,
    ActiveAssetDataSubscription,
]

AllMidsData = TypedDict("AllMidsData", {"mids": Dict[str, str]})
AllMidsMsg = TypedDict("AllMidsMsg", {"channel": Literal["allMids"], "data": AllMidsData})
L2Level = TypedDict("L2Level", {"px": str, "sz": str, "n": int})
L2BookData = TypedDict("L2BookData", {"coin": str, "levels": Tuple[List[L2Level], List[L2Level]], "time": int})
L2BookMsg = TypedDict("L2BookMsg", {"channel": Literal["l2Book"], "data": L2BookData})
BboData = TypedDict("BboData", {"coin": str, "time": int, "bbo": Tuple[Optional[L2Level], Optional[L2Level]]})
BboMsg = TypedDict("BboMsg", {"channel": Literal["bbo"], "data": BboData})
PongMsg = TypedDict("PongMsg", {"channel": Literal["pong"]})
Trade = TypedDict("Trade", {"coin": str, "side": Side, "px": str, "sz": int, "hash": str, "time": int})
CrossLeverage = TypedDict(
    "CrossLeverage",
    {
        "type": Literal["cross"],
        "value": int,
    },
)
IsolatedLeverage = TypedDict(
    "IsolatedLeverage",
    {
        "type": Literal["isolated"],
        "value": int,
        "rawUsd": str,
    },
)
Leverage = Union[CrossLeverage, IsolatedLeverage]
TradesMsg = TypedDict("TradesMsg", {"channel": Literal["trades"], "data": List[Trade]})
PerpAssetCtx = TypedDict(
    "PerpAssetCtx",
    {
        "funding": str,
        "openInterest": str,
        "prevDayPx": str,
        "dayNtlVlm": str,
        "premium": str,
        "oraclePx": str,
        "markPx": str,
        "midPx": Optional[str],
        "impactPxs": Optional[Tuple[str, str]],
        "dayBaseVlm": str,
    },
)
ActiveAssetCtx = TypedDict("ActiveAssetCtx", {"coin": str, "ctx": PerpAssetCtx})
ActiveSpotAssetCtx = TypedDict("ActiveSpotAssetCtx", {"coin": str, "ctx": SpotAssetCtx})
ActiveAssetCtxMsg = TypedDict("ActiveAssetCtxMsg", {"channel": Literal["activeAssetCtx"], "data": ActiveAssetCtx})
ActiveSpotAssetCtxMsg = TypedDict(
    "ActiveSpotAssetCtxMsg", {"channel": Literal["activeSpotAssetCtx"], "data": ActiveSpotAssetCtx}
)
ActiveAssetData = TypedDict(
    "ActiveAssetData",
    {
        "user": str,
        "coin": str,
        "leverage": Leverage,
        "maxTradeSzs": Tuple[str, str],
        "availableToTrade": Tuple[str, str],
        "markPx": str,
    },
)
ActiveAssetDataMsg = TypedDict("ActiveAssetDataMsg", {"channel": Literal["activeAssetData"], "data": ActiveAssetData})
Fill = TypedDict(
    "Fill",
    {
        "coin": str,
        "px": str,
        "sz": str,
        "side": Side,
        "time": int,
        "startPosition": str,
        "dir": str,
        "closedPnl": str,
        "hash": str,
        "oid": int,
        "crossed": bool,
        "fee": str,
        "tid": int,
        "feeToken": str,
    },
)
# TODO: handle other types of user events
UserEventsData = TypedDict("UserEventsData", {"fills": List[Fill]}, total=False)
UserEventsMsg = TypedDict("UserEventsMsg", {"channel": Literal["user"], "data": UserEventsData})
UserFillsData = TypedDict("UserFillsData", {"user": str, "isSnapshot": bool, "fills": List[Fill]})
UserFillsMsg = TypedDict("UserFillsMsg", {"channel": Literal["userFills"], "data": UserFillsData})
OtherWsMsg = TypedDict(
    "OtherWsMsg",
    {
        "channel": Union[
            Literal["candle"],
            Literal["orderUpdates"],
            Literal["userFundings"],
            Literal["userNonFundingLedgerUpdates"],
            Literal["webData2"],
        ],
        "data": Any,
    },
    total=False,
)
WsMsg = Union[
    AllMidsMsg,
    BboMsg,
    L2BookMsg,
    TradesMsg,
    UserEventsMsg,
    PongMsg,
    UserFillsMsg,
    OtherWsMsg,
    ActiveAssetCtxMsg,
    ActiveSpotAssetCtxMsg,
    ActiveAssetDataMsg,
]

# b is the public address of the builder, f is the amount of the fee in tenths of basis points. e.g. 10 means 1 basis point
BuilderInfo = TypedDict("BuilderInfo", {"b": str, "f": int})

PerpDexSchemaInput = TypedDict(
    "PerpDexSchemaInput", {"fullName": str, "collateralToken": int, "oracleUpdater": Optional[str]}
)


class Cloid:
    def __init__(self, raw_cloid: str):
        self._raw_cloid: str = raw_cloid
        self._validate()

    def _validate(self):
        if not self._raw_cloid[:2] == "0x":
            raise TypeError("cloid is not a hex string")
        if not len(self._raw_cloid[2:]) == 32:
            raise TypeError("cloid is not 16 bytes")

    def __str__(self):
        return str(self._raw_cloid)

    def __repr__(self):
        return str(self._raw_cloid)

    @staticmethod
    def from_int(cloid: int) -> Cloid:
        return Cloid(f"{cloid:#034x}")

    @staticmethod
    def from_str(cloid: str) -> Cloid:
        return Cloid(cloid)

    def to_raw(self):
        return self._raw_cloid
