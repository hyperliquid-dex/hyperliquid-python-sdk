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
)


def test_phantom_agent_creation_matches_production():
    timestamp = 1677777606040
    order_spec: OrderSpec = {
        "order": {
            "asset": 4,
            "isBuy": True,
            "reduceOnly": False,
            "limitPx": 1670.1,
            "sz": 0.0147,
        },
        "orderType": {"limit": {"tif": "Ioc"}},
    }
    grouping: Literal["na"] = "na"

    phantom_agent = construct_phantom_agent(
        ["(uint32,bool,uint64,uint64,bool,uint8,uint64)[]", "uint8", "address", "uint64"],
        [[order_spec_preprocessing(order_spec)], order_grouping_to_number(grouping), ZERO_ADDRESS, timestamp],
    )
    assert to_hex(phantom_agent["connectionId"]) == "0xd16723c8d7aab4b768e2060b763165f256825690ed246e6788264b27f6c929b9"


def test_l1_action_signing_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    signature = sign_l1_action(wallet, ["uint64"], [float_to_int_for_hashing(1000)], None, 0)
    assert signature["r"] == "0xfd19b1e1f8ff9c4b8bd95f3522dee21783e02e381ba34624796d4f579a9fff74"
    assert signature["s"] == "0x671f4cd60fa998ef5f1a841ca97dc47ad390915c230745cd3c371b0ef07a723b"
    assert signature["v"] == 27


def test_l1_action_signing_matches_with_vault():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    signature = sign_l1_action(
        wallet, ["uint64"], [float_to_int_for_hashing(1000)], "0x1719884eb866cb12b2287399b15f7db5e7d775ea", 0
    )
    assert signature["r"] == "0x9358ee731732877d9a6d1a761fb6db43f93cb7c69ca74ecb382bd0773ac9b093"
    assert signature["s"] == "0x2879b3d8384b80664346c4286c34f947fc970c3a84c2f3995555f68493adf60b"
    assert signature["v"] == 27


def test_float_to_int_for_hashing():
    assert float_to_int_for_hashing(123123123123) == 12312312312300000000
    assert float_to_int_for_hashing(0.00001231) == 1231
    assert float_to_int_for_hashing(1.033) == 103300000
    with pytest.raises(ValueError):
        float_to_int_for_hashing(0.000012312312)
