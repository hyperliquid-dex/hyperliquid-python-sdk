from typing import Literal

import eth_account
import pytest
from eth_utils import to_hex

from hyperliquid.utils.signing import (
    ZERO_ADDRESS,
    OrderSpec,
    construct_phantom_agent,
    float_to_int_for_hashing,
    order_grouping_to_number,
    order_spec_preprocessing,
    sign_l1_action,
    sign_usd_transfer_action,
    sign_withdraw_from_bridge_action,
)
from hyperliquid.utils.types import Cloid


def test_phantom_agent_creation_matches_production():
    timestamp = 1677777606040
    order_spec: OrderSpec = {
        "order": {
            "asset": 4,
            "isBuy": True,
            "reduceOnly": False,
            "limitPx": 1670.1,
            "sz": 0.0147,
            "cloid": None,
        },
        "orderType": {"limit": {"tif": "Ioc"}},
    }
    grouping: Literal["na"] = "na"

    phantom_agent = construct_phantom_agent(
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8", "address", "uint64"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping), ZERO_ADDRESS, timestamp],
        True,
    )
    assert to_hex(phantom_agent["connectionId"]) == "0xd16723c8d7aab4b768e2060b763165f256825690ed246e6788264b27f6c929b9"


def test_l1_action_signing_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    signature_mainnet = sign_l1_action(wallet, ["uint64"], [float_to_int_for_hashing(1000)], None, 0, True)
    assert signature_mainnet["r"] == "0xfd19b1e1f8ff9c4b8bd95f3522dee21783e02e381ba34624796d4f579a9fff74"
    assert signature_mainnet["s"] == "0x671f4cd60fa998ef5f1a841ca97dc47ad390915c230745cd3c371b0ef07a723b"
    assert signature_mainnet["v"] == 27
    signature_testnet = sign_l1_action(wallet, ["uint64"], [float_to_int_for_hashing(1000)], None, 0, False)
    assert signature_testnet["r"] == "0x641b70a067c62d3286b85145a3975d6c7205654223ee29892cdeeb46dea73df2"
    assert signature_testnet["s"] == "0x7089f33a1b78c1dbbbd83d95398cc9e2b87739fb70a967ab903b62d39050b5cf"
    assert signature_testnet["v"] == 27


def test_l1_action_signing_order_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    order_spec: OrderSpec = {
        "order": {
            "asset": 1,
            "isBuy": True,
            "reduceOnly": False,
            "limitPx": 100,
            "sz": 100,
            "cloid": None,
        },
        "orderType": {"limit": {"tif": "Gtc"}},
    }
    timestamp = 0
    grouping: Literal["na"] = "na"

    signature_mainnet = sign_l1_action(
        wallet,
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
        ZERO_ADDRESS,
        timestamp,
        True,
    )
    assert signature_mainnet["r"] == "0xc7249fd2e6483b2ab8fb0a80ac5201c4d36c8ed52bea5896012de499cdb78f4f"
    assert signature_mainnet["s"] == "0x235a525be1a3b3c5186a241763a47f4e1db463dbba64a3c4abad3696852cd6ff"
    assert signature_mainnet["v"] == 27

    signature_testnet = sign_l1_action(
        wallet,
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
        ZERO_ADDRESS,
        timestamp,
        False,
    )
    assert signature_testnet["r"] == "0x28d9e3237c12a7b07c357ce224a683ac5b947f03da209907ea264d10bb3a4311"
    assert signature_testnet["s"] == "0x556c333b8572886be4dc637792384f19e1d920ab6356982d5bf6d98205e6978b"
    assert signature_testnet["v"] == 27


def test_l1_action_signing_order_with_cloid_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    order_spec: OrderSpec = {
        "order": {
            "asset": 1,
            "isBuy": True,
            "reduceOnly": False,
            "limitPx": 100,
            "sz": 100,
            "cloid": Cloid.from_str("0x00000000000000000000000000000001"),
        },
        "orderType": {"limit": {"tif": "Gtc"}},
    }
    timestamp = 0
    grouping: Literal["na"] = "na"

    signature_mainnet = sign_l1_action(
        wallet,
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64,bytes16)[]", "uint8"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
        ZERO_ADDRESS,
        timestamp,
        True,
    )
    assert signature_mainnet["r"] == "0x8518bb4fbdb9ed4bda8d9ea984bc963d73d203ae2c0523f366855ac042d11ee5"
    assert signature_mainnet["s"] == "0x235c634764f08b4b98762de579ed13bbed731cc1e8574b8a3044cd4eff03ed76"
    assert signature_mainnet["v"] == 28

    signature_testnet = sign_l1_action(
        wallet,
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64,bytes16)[]", "uint8"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
        ZERO_ADDRESS,
        timestamp,
        False,
    )
    assert signature_testnet["r"] == "0x83bf34efdce3ee70bfff7ec8e45a1c547aa7ea950646bd599c4bc990bc1e87d8"
    assert signature_testnet["s"] == "0x5ac67572090d73a15538734b72e8c7037c6cbe363424e623501184ebb5b68d55"
    assert signature_testnet["v"] == 28


def test_l1_action_signing_matches_with_vault():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    signature_mainnet = sign_l1_action(
        wallet, ["uint64"], [float_to_int_for_hashing(1000)], "0x1719884eb866cb12b2287399b15f7db5e7d775ea", 0, True
    )
    assert signature_mainnet["r"] == "0x9358ee731732877d9a6d1a761fb6db43f93cb7c69ca74ecb382bd0773ac9b093"
    assert signature_mainnet["s"] == "0x2879b3d8384b80664346c4286c34f947fc970c3a84c2f3995555f68493adf60b"
    assert signature_mainnet["v"] == 27
    signature_testnet = sign_l1_action(
        wallet, ["uint64"], [float_to_int_for_hashing(1000)], "0x1719884eb866cb12b2287399b15f7db5e7d775ea", 0, False
    )
    assert signature_testnet["r"] == "0x42fc8e25437f795c701e73d4a21e4ee668f0f89c7ee9581adba915341dae82a3"
    assert signature_testnet["s"] == "0x27c6a515b1e0f755a0c357e961b16f8acdf89a2ffdd4a50ca1df2c85e70ab0b3"
    assert signature_testnet["v"] == 28


def test_l1_action_signing_tpsl_order_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    order_spec: OrderSpec = {
        "order": {
            "asset": 1,
            "isBuy": True,
            "reduceOnly": False,
            "limitPx": 100,
            "sz": 100,
            "cloid": None,
        },
        "orderType": {"trigger": {"triggerPx": 103, "isMarket": True, "tpsl": "sl"}},
    }
    timestamp = 0
    grouping: Literal["na"] = "na"

    signature_mainnet = sign_l1_action(
        wallet,
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
        ZERO_ADDRESS,
        timestamp,
        True,
    )
    assert signature_mainnet["r"] == "0xac0669959d0031e822c0aac9569f256ed66adfc409ab0bc3349f3006b794daf"
    assert signature_mainnet["s"] == "0x25e31fba6a324b13f1b1960142b9af31bfc4cc73796ac988aef434d693f865ea"
    assert signature_mainnet["v"] == 28

    signature_testnet = sign_l1_action(
        wallet,
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping)],
        ZERO_ADDRESS,
        timestamp,
        False,
    )
    assert signature_testnet["r"] == "0x1d353477289b3beb1b776cb80086d4f768f95e850c80abd394e0383c9f7d4be0"
    assert signature_testnet["s"] == "0x665fe43c4321bb8c2450817ad54b424758688f5542fc13b16e8e1db22e9c68ea"
    assert signature_testnet["v"] == 28


def test_float_to_int_for_hashing():
    assert float_to_int_for_hashing(123123123123) == 12312312312300000000
    assert float_to_int_for_hashing(0.00001231) == 1231
    assert float_to_int_for_hashing(1.033) == 103300000
    with pytest.raises(ValueError):
        float_to_int_for_hashing(0.000012312312)


def test_sign_usd_transfer_action():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    message = {
        "destination": "0x5e9ee1089755c3435139848e47e6635505d5a13a",
        "amount": "1",
        "time": 1687816341423,
    }
    signature = sign_usd_transfer_action(wallet, message, False)
    assert signature["r"] == "0x283ca602ac69be536bd2272f050eddf8d250ed3eef083d1fc26989e57f891759"
    assert signature["s"] == "0x9bc743cf95042269236bc7f48c06ab8a6a9ee53e04f3336c6cfd1b22783aa74"
    assert signature["v"] == 28


def test_sign_withdraw_from_bridge_action():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    message = {
        "destination": "0x5e9ee1089755c3435139848e47e6635505d5a13a",
        "usd": "1",
        "time": 1687816341423,
    }
    signature = sign_withdraw_from_bridge_action(wallet, message, False)
    assert signature["r"] == "0xd60816bf99a00645aa81b9ade23f03bf15994cd2c6d06fc3740a4c74530e36d9"
    assert signature["s"] == "0x4552f30419166a6e9d8dbd49b14aeef1e7606fe9e0caec8c0211608d79ce43a3"
    assert signature["v"] == 28
