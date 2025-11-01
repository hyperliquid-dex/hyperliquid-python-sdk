from typing import Any

import time
from decimal import Decimal

import msgpack
from eth_account import Account
from eth_account.messages import encode_typed_data
from eth_utils import keccak, to_hex

from hyperliquid.utils.types import Cloid, Literal, NotRequired, Optional, TypedDict, Union

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
OidOrCloid = Union[int, Cloid]
ModifyRequest = TypedDict(
    "ModifyRequest",
    {
        "oid": OidOrCloid,
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

ScheduleCancelAction = TypedDict(
    "ScheduleCancelAction",
    {
        "type": Literal["scheduleCancel"],
        "time": NotRequired[Optional[int]],
    },
)

USD_SEND_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "destination", "type": "string"},
    {"name": "amount", "type": "string"},
    {"name": "time", "type": "uint64"},
]

SPOT_TRANSFER_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "destination", "type": "string"},
    {"name": "token", "type": "string"},
    {"name": "amount", "type": "string"},
    {"name": "time", "type": "uint64"},
]

WITHDRAW_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "destination", "type": "string"},
    {"name": "amount", "type": "string"},
    {"name": "time", "type": "uint64"},
]

USD_CLASS_TRANSFER_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "amount", "type": "string"},
    {"name": "toPerp", "type": "bool"},
    {"name": "nonce", "type": "uint64"},
]

SEND_ASSET_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "destination", "type": "string"},
    {"name": "sourceDex", "type": "string"},
    {"name": "destinationDex", "type": "string"},
    {"name": "token", "type": "string"},
    {"name": "amount", "type": "string"},
    {"name": "fromSubAccount", "type": "string"},
    {"name": "nonce", "type": "uint64"},
]

USER_DEX_ABSTRACTION_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "user", "type": "address"},
    {"name": "enabled", "type": "bool"},
    {"name": "nonce", "type": "uint64"},
]

TOKEN_DELEGATE_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "validator", "type": "address"},
    {"name": "wei", "type": "uint64"},
    {"name": "isUndelegate", "type": "bool"},
    {"name": "nonce", "type": "uint64"},
]

CONVERT_TO_MULTI_SIG_USER_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "signers", "type": "string"},
    {"name": "nonce", "type": "uint64"},
]

MULTI_SIG_ENVELOPE_SIGN_TYPES = [
    {"name": "hyperliquidChain", "type": "string"},
    {"name": "multiSigActionHash", "type": "bytes32"},
    {"name": "nonce", "type": "uint64"},
]


def order_type_to_wire(order_type: OrderType) -> OrderTypeWire:
    if "limit" in order_type:
        return {"limit": order_type["limit"]}
    elif "trigger" in order_type:
        return {
            "trigger": {
                "isMarket": order_type["trigger"]["isMarket"],
                "triggerPx": float_to_wire(order_type["trigger"]["triggerPx"]),
                "tpsl": order_type["trigger"]["tpsl"],
            }
        }
    raise ValueError("Invalid order type", order_type)


def address_to_bytes(address):
    return bytes.fromhex(address[2:] if address.startswith("0x") else address)


def action_hash(action, vault_address, nonce, expires_after):
    data = msgpack.packb(action)
    data += nonce.to_bytes(8, "big")
    if vault_address is None:
        data += b"\x00"
    else:
        data += b"\x01"
        data += address_to_bytes(vault_address)
    if expires_after is not None:
        data += b"\x00"
        data += expires_after.to_bytes(8, "big")
    return keccak(data)


def construct_phantom_agent(hash, is_mainnet):
    return {"source": "a" if is_mainnet else "b", "connectionId": hash}


def l1_payload(phantom_agent):
    return {
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


def user_signed_payload(primary_type, payload_types, action):
    chain_id = int(action["signatureChainId"], 16)
    return {
        "domain": {
            "name": "HyperliquidSignTransaction",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": "0x0000000000000000000000000000000000000000",
        },
        "types": {
            primary_type: payload_types,
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
        },
        "primaryType": primary_type,
        "message": action,
    }


def sign_l1_action(wallet, action, active_pool, nonce, expires_after, is_mainnet):
    hash = action_hash(action, active_pool, nonce, expires_after)
    phantom_agent = construct_phantom_agent(hash, is_mainnet)
    data = l1_payload(phantom_agent)
    return sign_inner(wallet, data)


def sign_user_signed_action(wallet, action, payload_types, primary_type, is_mainnet):
    # signatureChainId is the chain used by the wallet to sign and can be any chain.
    # hyperliquidChain determines the environment and prevents replaying an action on a different chain.
    action["signatureChainId"] = "0x66eee"
    action["hyperliquidChain"] = "Mainnet" if is_mainnet else "Testnet"
    data = user_signed_payload(primary_type, payload_types, action)
    return sign_inner(wallet, data)


def add_multi_sig_types(sign_types):
    enriched_sign_types = []
    enriched = False
    for sign_type in sign_types:
        enriched_sign_types.append(sign_type)
        if sign_type["name"] == "hyperliquidChain":
            enriched = True
            enriched_sign_types.append(
                {
                    "name": "payloadMultiSigUser",
                    "type": "address",
                }
            )
            enriched_sign_types.append(
                {
                    "name": "outerSigner",
                    "type": "address",
                }
            )
    if not enriched:
        print('"hyperliquidChain" missing from sign_types. sign_types was not enriched with multi-sig signing types')
    return enriched_sign_types


def add_multi_sig_fields(action, payload_multi_sig_user, outer_signer):
    action = action.copy()
    action["payloadMultiSigUser"] = payload_multi_sig_user.lower()
    action["outerSigner"] = outer_signer.lower()
    return action


def sign_multi_sig_user_signed_action_payload(
    wallet, action, is_mainnet, sign_types, tx_type, payload_multi_sig_user, outer_signer
):
    envelope = add_multi_sig_fields(action, payload_multi_sig_user, outer_signer)
    sign_types = add_multi_sig_types(sign_types)
    return sign_user_signed_action(
        wallet,
        envelope,
        sign_types,
        tx_type,
        is_mainnet,
    )


def sign_multi_sig_l1_action_payload(
    wallet, action, is_mainnet, vault_address, timestamp, expires_after, payload_multi_sig_user, outer_signer
):
    envelope = [payload_multi_sig_user.lower(), outer_signer.lower(), action]
    return sign_l1_action(
        wallet,
        envelope,
        vault_address,
        timestamp,
        expires_after,
        is_mainnet,
    )


def sign_multi_sig_action(wallet, action, is_mainnet, vault_address, nonce, expires_after):
    action_without_tag = action.copy()
    del action_without_tag["type"]
    multi_sig_action_hash = action_hash(action_without_tag, vault_address, nonce, expires_after)
    envelope = {
        "multiSigActionHash": multi_sig_action_hash,
        "nonce": nonce,
    }
    return sign_user_signed_action(
        wallet,
        envelope,
        MULTI_SIG_ENVELOPE_SIGN_TYPES,
        "HyperliquidTransaction:SendMultiSig",
        is_mainnet,
    )


def sign_usd_transfer_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        USD_SEND_SIGN_TYPES,
        "HyperliquidTransaction:UsdSend",
        is_mainnet,
    )


def sign_spot_transfer_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        SPOT_TRANSFER_SIGN_TYPES,
        "HyperliquidTransaction:SpotSend",
        is_mainnet,
    )


def sign_withdraw_from_bridge_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        WITHDRAW_SIGN_TYPES,
        "HyperliquidTransaction:Withdraw",
        is_mainnet,
    )


def sign_usd_class_transfer_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        USD_CLASS_TRANSFER_SIGN_TYPES,
        "HyperliquidTransaction:UsdClassTransfer",
        is_mainnet,
    )


def sign_send_asset_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        SEND_ASSET_SIGN_TYPES,
        "HyperliquidTransaction:SendAsset",
        is_mainnet,
    )


def sign_user_dex_abstraction_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        USER_DEX_ABSTRACTION_SIGN_TYPES,
        "HyperliquidTransaction:UserDexAbstraction",
        is_mainnet,
    )


def sign_convert_to_multi_sig_user_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        CONVERT_TO_MULTI_SIG_USER_SIGN_TYPES,
        "HyperliquidTransaction:ConvertToMultiSigUser",
        is_mainnet,
    )


def sign_agent(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        [
            {"name": "hyperliquidChain", "type": "string"},
            {"name": "agentAddress", "type": "address"},
            {"name": "agentName", "type": "string"},
            {"name": "nonce", "type": "uint64"},
        ],
        "HyperliquidTransaction:ApproveAgent",
        is_mainnet,
    )


def sign_approve_builder_fee(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        [
            {"name": "hyperliquidChain", "type": "string"},
            {"name": "maxFeeRate", "type": "string"},
            {"name": "builder", "type": "address"},
            {"name": "nonce", "type": "uint64"},
        ],
        "HyperliquidTransaction:ApproveBuilderFee",
        is_mainnet,
    )


def sign_token_delegate_action(wallet, action, is_mainnet):
    return sign_user_signed_action(
        wallet,
        action,
        TOKEN_DELEGATE_TYPES,
        "HyperliquidTransaction:TokenDelegate",
        is_mainnet,
    )


def sign_inner(wallet, data):
    structured_data = encode_typed_data(full_message=data)
    signed = wallet.sign_message(structured_data)
    return {"r": to_hex(signed["r"]), "s": to_hex(signed["s"]), "v": signed["v"]}


def recover_agent_or_user_from_l1_action(action, signature, active_pool, nonce, expires_after, is_mainnet):
    hash = action_hash(action, active_pool, nonce, expires_after)
    phantom_agent = construct_phantom_agent(hash, is_mainnet)
    data = l1_payload(phantom_agent)
    structured_data = encode_typed_data(full_message=data)
    address = Account.recover_message(structured_data, vrs=[signature["v"], signature["r"], signature["s"]])
    return address


def recover_user_from_user_signed_action(action, signature, payload_types, primary_type, is_mainnet):
    action["hyperliquidChain"] = "Mainnet" if is_mainnet else "Testnet"
    data = user_signed_payload(primary_type, payload_types, action)
    structured_data = encode_typed_data(full_message=data)
    address = Account.recover_message(structured_data, vrs=[signature["v"], signature["r"], signature["s"]])
    return address


def float_to_wire(x: float) -> str:
    rounded = f"{x:.8f}"
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


def order_wires_to_order_action(order_wires: list[OrderWire], builder: Any = None, grouping: Grouping = "na") -> Any:
    action = {
        "type": "order",
        "orders": order_wires,
        "grouping": grouping,
    }
    if builder:
        action["builder"] = builder
    return action
