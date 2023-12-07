import time

from eth_abi import encode
from eth_account.messages import encode_structured_data
from eth_utils import keccak, to_hex

from hyperliquid.utils.types import Any, Literal, Optional, Tuple, TypedDict, Union, Cloid

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

Tif = Union[Literal["Alo"], Literal["Ioc"], Literal["Gtc"]]
Tpsl = Union[Literal["tp"], Literal["sl"]]
LimitOrderType = TypedDict("LimitOrderType", {"tif": Tif})
TriggerOrderType = TypedDict("TriggerOrderType", {"triggerPx": float, "isMarket": bool, "tpsl": Tpsl})
TriggerOrderTypeWire = TypedDict("TriggerOrderTypeWire", {"triggerPx": str, "isMarket": bool, "tpsl": Tpsl})
OrderType = TypedDict("OrderType", {"limit": LimitOrderType, "trigger": TriggerOrderType}, total=False)
OrderTypeWire = TypedDict("OrderTypeWire", {"limit": LimitOrderType, "trigger": TriggerOrderTypeWire}, total=False)
OrderRequest = TypedDict(
    "OrderRequest",
    {
        "coin": str,
        "is_buy": bool,
        "sz": float,
        "limit_px": float,
        "order_type": OrderType,
        "reduce_only": bool,
        "cloid": Optional[Cloid],
    },
    total=False,
)
ModifyRequest = TypedDict(
    "ModifyRequest",
    {
        "oid": int,
        "order": OrderRequest,
    },
    total=False,
)
CancelRequest = TypedDict("CancelRequest", {"coin": str, "oid": int})
CancelByCloidRequest = TypedDict("CancelByCloidRequest", {"coin": str, "cloid": Cloid})


def order_type_to_tuple(order_type: OrderType) -> Tuple[int, float]:
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


Order = TypedDict(
    "Order", {"asset": int, "isBuy": bool, "limitPx": float, "sz": float, "reduceOnly": bool, "cloid": Optional[Cloid]}
)
OrderSpec = TypedDict("OrderSpec", {"order": Order, "orderType": OrderType})
ModifySpec = TypedDict("ModifySpec", {"oid": int, "order": OrderSpec, "orderType": OrderType})


def order_spec_preprocessing(order_spec: OrderSpec) -> Any:
    order = order_spec["order"]
    order_type_array = order_type_to_tuple(order_spec["orderType"])
    res: Any = (
        order["asset"],
        order["isBuy"],
        float_to_int_for_hashing(order["limitPx"]),
        float_to_int_for_hashing(order["sz"]),
        order["reduceOnly"],
        order_type_array[0],
        float_to_int_for_hashing(order_type_array[1]),
    )
    if "cloid" in order and order["cloid"] is not None:
        res += (str_to_bytes16(order["cloid"].to_raw()),)
    return res


def modify_spec_preprocessing(modify_spec: ModifySpec) -> Any:
    res: Any = (modify_spec["oid"],)
    res += order_spec_preprocessing(modify_spec["order"])
    order = modify_spec["order"]["order"]
    if "cloid" not in order or order["cloid"] is None:
        res += (bytearray(16),)
    return res


OrderWire = TypedDict(
    "OrderWire",
    {
        "asset": int,
        "isBuy": bool,
        "limitPx": str,
        "sz": str,
        "reduceOnly": bool,
        "orderType": OrderTypeWire,
        "cloid": Optional[Cloid],
    },
)

ModifyWire = TypedDict(
    "ModifyWire",
    {
        "oid": int,
        "order": OrderWire,
    },
)


def order_type_to_wire(order_type: OrderType) -> OrderTypeWire:
    if "limit" in order_type:
        return {"limit": order_type["limit"]}
    elif "trigger" in order_type:
        return {
            "trigger": {
                "triggerPx": float_to_wire(order_type["trigger"]["triggerPx"]),
                "tpsl": order_type["trigger"]["tpsl"],
                "isMarket": order_type["trigger"]["isMarket"],
            }
        }
    raise ValueError("Invalid order type", order_type)


def order_spec_to_order_wire(order_spec: OrderSpec) -> OrderWire:
    order = order_spec["order"]
    cloid = None
    if "cloid" in order and order["cloid"] is not None:
        cloid = order["cloid"].to_raw()
    return {
        "asset": order["asset"],
        "isBuy": order["isBuy"],
        "limitPx": float_to_wire(order["limitPx"]),
        "sz": float_to_wire(order["sz"]),
        "reduceOnly": order["reduceOnly"],
        "orderType": order_type_to_wire(order_spec["orderType"]),
        "cloid": cloid,
    }


def modify_spec_to_modify_wire(modify_spec: ModifySpec) -> ModifyWire:
    return {
        "oid": modify_spec["oid"],
        "order": order_spec_to_order_wire(modify_spec["order"]),
    }


def construct_phantom_agent(signature_types, signature_data, is_mainnet):
    connection_id = encode(signature_types, signature_data)

    return {"source": "a" if is_mainnet else "b", "connectionId": keccak(connection_id)}


def sign_l1_action(wallet, signature_types, signature_data, active_pool, nonce, is_mainnet, action_type_code=None):
    signature_types.append("address")
    signature_types.append("uint64")
    if active_pool is None:
        signature_data.append(ZERO_ADDRESS)
    else:
        signature_data.append(active_pool)
    signature_data.append(nonce)

    if action_type_code is not None:
        signature_types.append("uint16")
        signature_data.append(action_type_code)

    phantom_agent = construct_phantom_agent(signature_types, signature_data, is_mainnet)

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
    return sign_inner(wallet, data)


def sign_usd_transfer_action(wallet, message, is_mainnet):
    data = {
        "domain": {
            "name": "Exchange",
            "version": "1",
            "chainId": 42161 if is_mainnet else 421614,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
        },
        "types": {
            "UsdTransferSignPayload": [
                {"name": "destination", "type": "string"},
                {"name": "amount", "type": "string"},
                {"name": "time", "type": "uint64"},
            ],
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        },
        "primaryType": "UsdTransferSignPayload",
        "message": message,
    }
    return sign_inner(wallet, data)


def sign_withdraw_from_bridge_action(wallet, message, is_mainnet):
    data = {
        "domain": {
            "name": "Exchange",
            "version": "1",
            "chainId": 42161 if is_mainnet else 421614,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
        },
        "types": {
            "WithdrawFromBridge2SignPayload": [
                {"name": "destination", "type": "string"},
                {"name": "usd", "type": "string"},
                {"name": "time", "type": "uint64"},
            ],
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        },
        "primaryType": "WithdrawFromBridge2SignPayload",
        "message": message,
    }
    return sign_inner(wallet, data)


def sign_agent(wallet, agent, is_mainnet):
    data = {
        "domain": {
            "name": "Exchange",
            "version": "1",
            "chainId": 42161 if is_mainnet else 421614,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
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
        "message": agent,
    }
    return sign_inner(wallet, data)


def sign_inner(wallet, data):
    structured_data = encode_structured_data(data)
    signed = wallet.sign_message(structured_data)
    return {"r": to_hex(signed["r"]), "s": to_hex(signed["s"]), "v": signed["v"]}


def float_to_wire(x: float) -> str:
    rounded = "{:.8f}".format(x)
    if abs(float(rounded) - x) >= 1e-12:
        raise ValueError("float_to_wire causes rounding", x)
    return rounded


def float_to_int_for_hashing(x: float) -> int:
    return float_to_int(x, 8)


def float_to_usd_int(x: float) -> int:
    return float_to_int(x, 6)


def float_to_int(x: float, power: int) -> int:
    with_decimals = x * 10**power
    if abs(round(with_decimals) - with_decimals) >= 1e-3:
        raise ValueError("float_to_int causes rounding", x)
    res: int = round(with_decimals)
    return res


def str_to_bytes16(x: str) -> bytearray:
    assert x.startswith("0x")
    return bytearray.fromhex(x[2:])


def get_timestamp_ms() -> int:
    return int(time.time() * 1000)


def order_request_to_order_spec(order: OrderRequest, asset: int) -> OrderSpec:
    cloid = None
    if "cloid" in order:
        cloid = order["cloid"]
    return {
        "order": {
            "asset": asset,
            "isBuy": order["is_buy"],
            "reduceOnly": order["reduce_only"],
            "limitPx": order["limit_px"],
            "sz": order["sz"],
            "cloid": cloid,
        },
        "orderType": order["order_type"],
    }
