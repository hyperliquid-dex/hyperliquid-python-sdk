import time

from decimal import Decimal
from eth_account.messages import encode_structured_data
from eth_utils import keccak, to_hex
import msgpack

from hyperliquid.utils.types import Literal, Optional, TypedDict, Union, Cloid, NotRequired

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
        "cloid": NotRequired[Optional[Cloid]],
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

Grouping = Union[Literal["na"], Literal["normalTpsl"], Literal["positionTpsl"]]
Order = TypedDict(
    "Order", {"asset": int, "isBuy": bool, "limitPx": float, "sz": float, "reduceOnly": bool, "cloid": Optional[Cloid]}
)


OrderWire = TypedDict(
    "OrderWire",
    {
        "a": int,
        "b": bool,
        "p": str,
        "s": str,
        "r": bool,
        "t": OrderTypeWire,
        "c": NotRequired[Optional[str]],
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


def address_to_bytes(address):
    return bytes.fromhex(address[2:] if address.startswith("0x") else address)


def action_hash(action, vault_address, nonce):
    data = msgpack.packb(action)
    data += nonce.to_bytes(8, "big")
    if vault_address is None:
        data += b"\x00"
    else:
        data += b"\x01"
        data += address_to_bytes(vault_address)
    return keccak(data)


def construct_phantom_agent(hash, is_mainnet):
    return {"source": "a" if is_mainnet else "b", "connectionId": hash}


def sign_l1_action(wallet, action, active_pool, nonce, is_mainnet):
    hash = action_hash(action, active_pool, nonce)
    phantom_agent = construct_phantom_agent(hash, is_mainnet)
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
    if rounded == "-0":
        rounded = "0"
    normalized = Decimal(rounded).normalize()
    return f"{normalized:f}"


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


def get_timestamp_ms() -> int:
    return int(time.time() * 1000)


def order_request_to_order_wire(order: OrderRequest, asset: int) -> OrderWire:
    order_wire: OrderWire = {
        "a": asset,
        "b": order["is_buy"],
        "p": float_to_wire(order["limit_px"]),
        "s": float_to_wire(order["sz"]),
        "r": order["reduce_only"],
        "t": order_type_to_wire(order["order_type"]),
    }
    if "cloid" in order and order["cloid"] is not None:
        order_wire["c"] = order["cloid"].to_raw()
    return order_wire


def order_wires_to_order_action(order_wires):
    return {
        "type": "order",
        "orders": order_wires,
        "grouping": "na",
    }
