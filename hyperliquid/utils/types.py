from __future__ import annotations

import sys

if sys.version_info >= (3, 8):
    from typing import Literal, TypedDict
    from typing_extensions import NotRequired
else:
    from typing_extensions import TypedDict, Literal, NotRequired

from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple, Union, cast

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

AllMidsSubscription = TypedDict("AllMidsSubscription", {"type": Literal["allMids"]})
L2BookSubscription = TypedDict("L2BookSubscription", {"type": Literal["l2Book"], "coin": str})
TradesSubscription = TypedDict("TradesSubscription", {"type": Literal["trades"], "coin": str})
UserEventsSubscription = TypedDict("UserEventsSubscription", {"type": Literal["userEvents"], "user": str})
Subscription = Union[AllMidsSubscription, L2BookSubscription, TradesSubscription, UserEventsSubscription]

AllMidsData = TypedDict("AllMidsData", {"mids": Dict[str, str]})
AllMidsMsg = TypedDict("AllMidsMsg", {"channel": Literal["allMids"], "data": AllMidsData})
L2Level = TypedDict("L2Level", {"px": str, "sz": str, "n": int})
L2BookData = TypedDict("L2BookData", {"coin": str, "levels": Tuple[List[L2Level]], "time": int})
L2BookMsg = TypedDict("L2BookMsg", {"channel": Literal["l2Book"], "data": L2BookData})
PongMsg = TypedDict("PongMsg", {"channel": Literal["pong"]})
Trade = TypedDict("Trade", {"coin": str, "side": Side, "px": str, "sz": int, "hash": str, "time": int})
TradesMsg = TypedDict("TradesMsg", {"channel": Literal["trades"], "data": List[Trade]})
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
    },
)
# TODO: handle other types of user events
UserEventsData = TypedDict("UserEventsData", {"fills": List[Fill]}, total=False)
UserEventsMsg = TypedDict("UserEventsMsg", {"channel": Literal["user"], "data": UserEventsData})
WsMsg = Union[AllMidsMsg, L2BookMsg, TradesMsg, UserEventsMsg, PongMsg]


class Cloid:
    def __init__(self, raw_cloid: str):
        self._raw_cloid: str = raw_cloid
        self._validate()

    def _validate(self):
        assert self._raw_cloid[:2] == "0x", "cloid is not a hex string"
        assert len(self._raw_cloid[2:]) == 32, "cloid is not 16 bytes"

    @staticmethod
    def from_int(cloid: int) -> Cloid:
        return Cloid(f"{cloid:#034x}")

    @staticmethod
    def from_str(cloid: str) -> Cloid:
        return Cloid(cloid)

    def to_raw(self):
        return self._raw_cloid
