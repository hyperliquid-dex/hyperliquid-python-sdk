import time
from eth_abi import encode
from eth_account.messages import encode_structured_data
from eth_utils import keccak, to_hex

from hyperliquid.utils.types import TypedDict, Literal, Union, Any, Tuple

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

Tif = Union[Literal["Alo"], Literal["Ioc"], Literal["Gtc"]]
Tpsl = Union[Literal["tp"], Literal["sl"]]
LimitOrderType = TypedDict("LimitOrderType", {"tif": Tif})
TriggerOrderType = TypedDict("TriggerOrderType", {"triggerPx": int, "isMarket": bool, "tpsl": Tpsl})
OrderType = TypedDict("OrderType", {"limit": LimitOrderType, "trigger": TriggerOrderType}, total=False)


def order_type_to_tuple(order_type: OrderType) -> Tuple[int, int]:
    if "limit" in order_type:
        tif = order_type["limit"]["tif"]
        if tif == "Gtc":
            return 2, 0
        elif tif == "Alo":
            return 1, 0
        elif tif == "Ioc":
            return 3, 0
    elif "trigger" in order_type:
        trigger = order_type["trigger"]
        trigger_px = trigger["triggerPx"]
        if trigger["isMarket"] and trigger["tpsl"] == "tp":
            return 4, trigger_px
        elif not trigger["isMarket"] and trigger["tpsl"] == "tp":
            return 5, trigger_px
        elif trigger["isMarket"] and trigger["tpsl"] == "sl":
            return 6, trigger_px
        elif not trigger["isMarket"] and trigger["tpsl"] == "sl":
            return 7, trigger_px
    raise ValueError("Invalid order type", order_type)


Grouping = Union[Literal["na"], Literal["normalTpsl"], Literal["positionTpsl"]]


def order_grouping_to_number(grouping: Grouping) -> int:
    if grouping == "na":
        return 0
    elif grouping == "normalTpsl":
        return 1
    elif grouping == "positionTpsl":
        return 2


Order = TypedDict("Order", {"asset": int, "isBuy": bool, "limitPx": float, "sz": float, "reduceOnly": bool})
OrderSpec = TypedDict("OrderSpec", {"order": Order, "orderType": OrderType})


def order_spec_preprocessing(order_spec: OrderSpec) -> Any:
    order = order_spec["order"]
    order_type_array = order_type_to_tuple(order_spec["orderType"])
    return (
        order["asset"],
        order["isBuy"],
        float_to_int_for_hashing(order["limitPx"]),
        float_to_int_for_hashing(order["sz"]),
        order["reduceOnly"],
        order_type_array[0],
        float_to_int_for_hashing(order_type_array[1]),
    )


OrderWire = TypedDict(
    "OrderWire", {"asset": int, "isBuy": bool, "limitPx": str, "sz": str, "reduceOnly": bool, "orderType": OrderType}
)


def order_spec_to_order_wire(order_spec: OrderSpec) -> OrderWire:
    order = order_spec["order"]
    return {
        "asset": order["asset"],
        "isBuy": order["isBuy"],
        "limitPx": float_to_wire(order["limitPx"]),
        "sz": float_to_wire(order["sz"]),
        "reduceOnly": order["reduceOnly"],
        "orderType": order_spec["orderType"],
    }


def construct_phantom_agent(signature_types, signature_data):
    connection_id = encode(signature_types, signature_data)

    return {"source": "a", "connectionId": keccak(connection_id)}


def sign_l1_action(wallet, signature_types, signature_data, active_pool, nonce):
    signature_types.append("address")
    signature_types.append("uint64")
    if active_pool is None:
        signature_data.append(ZERO_ADDRESS)
    else:
        signature_data.append(active_pool)
    signature_data.append(nonce)

    phantom_agent = construct_phantom_agent(signature_types, signature_data)

    data = {
        "domain": {
            "chainId": 1337,
            "name": "Exchange",
            "verifyingContract": "0x0000000000000000000000000000000000000000",
            "version": "1",
        },
        "types": {
            "Agent": [
                {"name": "source", "type": "string"},
                {"name": "connectionId", "type": "bytes32"},
            ],
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        },
        "primaryType": "Agent",
        "message": phantom_agent,
    }

    structured_data = encode_structured_data(data)
    signed = wallet.sign_message(structured_data)
    return {"r": to_hex(signed["r"]), "s": to_hex(signed["s"]), "v": signed["v"]}


def float_to_wire(x: float) -> str:
    rounded = "{:.8f}".format(x)
    if abs(float(rounded) - x) >= 1e-12:
        raise ValueError("float_to_wire causes rounding", x)
    return rounded


def float_to_int_for_hashing(x: float) -> int:
    with_decimals = x * 10**8
    if abs(round(with_decimals) - with_decimals) >= 1e-4:
        raise ValueError("float_to_int_for_hashing causes rounding", x)
    return round(with_decimals)


def get_timestamp_ms() -> int:
    return int(time.time() * 1000)
