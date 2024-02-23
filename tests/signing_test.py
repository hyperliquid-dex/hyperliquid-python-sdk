import eth_account
import pytest
from eth_utils import to_hex

from hyperliquid.utils.signing import (
    action_hash,
    OrderRequest,
    construct_phantom_agent,
    float_to_int_for_hashing,
    order_request_to_order_wire,
    order_wires_to_order_action,
    sign_l1_action,
    sign_usd_transfer_action,
    sign_withdraw_from_bridge_action,
)
from hyperliquid.utils.types import Cloid


def test_phantom_agent_creation_matches_production():
    timestamp = 1677777606040
    order_request: OrderRequest = {
        "coin": "ETH",
        "is_buy": True,
        "sz": 0.0147,
        "limit_px": 1670.1,
        "reduce_only": False,
        "order_type": {"limit": {"tif": "Ioc"}},
        "cloid": None,
    }
    order_action = order_wires_to_order_action([order_request_to_order_wire(order_request, 4)])
    hash = action_hash(order_action, None, timestamp)
    phantom_agent = construct_phantom_agent(hash, True)
    assert to_hex(phantom_agent["connectionId"]) == "0x0fcbeda5ae3c4950a548021552a4fea2226858c4453571bf3f24ba017eac2908"


def test_l1_action_signing_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    action = {"type": "dummy", "num": float_to_int_for_hashing(1000)}
    signature_mainnet = sign_l1_action(wallet, action, None, 0, True)
    assert signature_mainnet["r"] == "0x53749d5b30552aeb2fca34b530185976545bb22d0b3ce6f62e31be961a59298"
    assert signature_mainnet["s"] == "0x755c40ba9bf05223521753995abb2f73ab3229be8ec921f350cb447e384d8ed8"
    assert signature_mainnet["v"] == 27
    signature_testnet = sign_l1_action(wallet, action, None, 0, False)
    assert signature_testnet["r"] == "0x542af61ef1f429707e3c76c5293c80d01f74ef853e34b76efffcb57e574f9510"
    assert signature_testnet["s"] == "0x17b8b32f086e8cdede991f1e2c529f5dd5297cbe8128500e00cbaf766204a613"
    assert signature_testnet["v"] == 28


def test_l1_action_signing_order_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    order_request: OrderRequest = {
        "coin": "ETH",
        "is_buy": True,
        "sz": 100,
        "limit_px": 100,
        "reduce_only": False,
        "order_type": {"limit": {"tif": "Gtc"}},
        "cloid": None,
    }
    order_action = order_wires_to_order_action([order_request_to_order_wire(order_request, 1)])
    timestamp = 0

    signature_mainnet = sign_l1_action(
        wallet,
        order_action,
        None,
        timestamp,
        True,
    )
    assert signature_mainnet["r"] == "0xd65369825a9df5d80099e513cce430311d7d26ddf477f5b3a33d2806b100d78e"
    assert signature_mainnet["s"] == "0x2b54116ff64054968aa237c20ca9ff68000f977c93289157748a3162b6ea940e"
    assert signature_mainnet["v"] == 28

    signature_testnet = sign_l1_action(
        wallet,
        order_action,
        None,
        timestamp,
        False,
    )
    assert signature_testnet["r"] == "0x82b2ba28e76b3d761093aaded1b1cdad4960b3af30212b343fb2e6cdfa4e3d54"
    assert signature_testnet["s"] == "0x6b53878fc99d26047f4d7e8c90eb98955a109f44209163f52d8dc4278cbbd9f5"
    assert signature_testnet["v"] == 27


def test_l1_action_signing_order_with_cloid_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    order_request: OrderRequest = {
        "coin": "ETH",
        "is_buy": True,
        "sz": 100,
        "limit_px": 100,
        "reduce_only": False,
        "order_type": {"limit": {"tif": "Gtc"}},
        "cloid": Cloid.from_str("0x00000000000000000000000000000001"),
    }
    order_action = order_wires_to_order_action([order_request_to_order_wire(order_request, 1)])
    timestamp = 0

    signature_mainnet = sign_l1_action(
        wallet,
        order_action,
        None,
        timestamp,
        True,
    )
    assert signature_mainnet["r"] == "0x41ae18e8239a56cacbc5dad94d45d0b747e5da11ad564077fcac71277a946e3"
    assert signature_mainnet["s"] == "0x3c61f667e747404fe7eea8f90ab0e76cc12ce60270438b2058324681a00116da"
    assert signature_mainnet["v"] == 27

    signature_testnet = sign_l1_action(
        wallet,
        order_action,
        None,
        timestamp,
        False,
    )
    assert signature_testnet["r"] == "0xeba0664bed2676fc4e5a743bf89e5c7501aa6d870bdb9446e122c9466c5cd16d"
    assert signature_testnet["s"] == "0x7f3e74825c9114bc59086f1eebea2928c190fdfbfde144827cb02b85bbe90988"
    assert signature_testnet["v"] == 28


def test_l1_action_signing_matches_with_vault():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    action = {"type": "dummy", "num": float_to_int_for_hashing(1000)}
    signature_mainnet = sign_l1_action(wallet, action, "0x1719884eb866cb12b2287399b15f7db5e7d775ea", 0, True)
    assert signature_mainnet["r"] == "0x3c548db75e479f8012acf3000ca3a6b05606bc2ec0c29c50c515066a326239"
    assert signature_mainnet["s"] == "0x4d402be7396ce74fbba3795769cda45aec00dc3125a984f2a9f23177b190da2c"
    assert signature_mainnet["v"] == 28
    signature_testnet = sign_l1_action(wallet, action, "0x1719884eb866cb12b2287399b15f7db5e7d775ea", 0, False)
    assert signature_testnet["r"] == "0xe281d2fb5c6e25ca01601f878e4d69c965bb598b88fac58e475dd1f5e56c362b"
    assert signature_testnet["s"] == "0x7ddad27e9a238d045c035bc606349d075d5c5cd00a6cd1da23ab5c39d4ef0f60"
    assert signature_testnet["v"] == 27


def test_l1_action_signing_tpsl_order_matches():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    order_request: OrderRequest = {
        "coin": "ETH",
        "is_buy": True,
        "sz": 100,
        "limit_px": 100,
        "reduce_only": False,
        "order_type": {"trigger": {"triggerPx": 103, "isMarket": True, "tpsl": "sl"}},
        "cloid": None,
    }
    order_action = order_wires_to_order_action([order_request_to_order_wire(order_request, 1)])
    timestamp = 0

    signature_mainnet = sign_l1_action(
        wallet,
        order_action,
        None,
        timestamp,
        True,
    )
    assert signature_mainnet["r"] == "0x98343f2b5ae8e26bb2587daad3863bc70d8792b09af1841b6fdd530a2065a3f9"
    assert signature_mainnet["s"] == "0x6b5bb6bb0633b710aa22b721dd9dee6d083646a5f8e581a20b545be6c1feb405"
    assert signature_mainnet["v"] == 27

    signature_testnet = sign_l1_action(
        wallet,
        order_action,
        None,
        timestamp,
        False,
    )
    assert signature_testnet["r"] == "0x971c554d917c44e0e1b6cc45d8f9404f32172a9d3b3566262347d0302896a2e4"
    assert signature_testnet["s"] == "0x206257b104788f80450f8e786c329daa589aa0b32ba96948201ae556d5637eac"
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


def test_create_sub_account_action():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    action = {
        "type": "createSubAccount",
        "name": "example",
    }
    signature_mainnet = sign_l1_action(wallet, action, None, 0, True)
    assert signature_mainnet["r"] == "0x51096fe3239421d16b671e192f574ae24ae14329099b6db28e479b86cdd6caa7"
    assert signature_mainnet["s"] == "0xb71f7d293af92d3772572afb8b102d167a7cef7473388286bc01f52a5c5b423"
    assert signature_mainnet["v"] == 27
    signature_testnet = sign_l1_action(wallet, action, None, 0, False)
    assert signature_testnet["r"] == "0xa699e3ed5c2b89628c746d3298b5dc1cca604694c2c855da8bb8250ec8014a5b"
    assert signature_testnet["s"] == "0x53f1b8153a301c72ecc655b1c315d64e1dcea3ee58921fd7507e35818fcc1584"
    assert signature_testnet["v"] == 28


def test_sub_account_transfer_action():
    wallet = eth_account.Account.from_key("0x0123456789012345678901234567890123456789012345678901234567890123")
    action = {
        "type": "subAccountTransfer",
        "subAccountUser": "0x1d9470d4b963f552e6f671a81619d395877bf409",
        "isDeposit": True,
        "usd": 10,
    }
    signature_mainnet = sign_l1_action(wallet, action, None, 0, True)
    assert signature_mainnet["r"] == "0x43592d7c6c7d816ece2e206f174be61249d651944932b13343f4d13f306ae602"
    assert signature_mainnet["s"] == "0x71a926cb5c9a7c01c3359ec4c4c34c16ff8107d610994d4de0e6430e5cc0f4c9"
    assert signature_mainnet["v"] == 28
    signature_testnet = sign_l1_action(wallet, action, None, 0, False)
    assert signature_testnet["r"] == "0xe26574013395ad55ee2f4e0575310f003c5bb3351b5425482e2969fa51543927"
    assert signature_testnet["s"] == "0xefb08999196366871f919fd0e138b3a7f30ee33e678df7cfaf203e25f0a4278"
    assert signature_testnet["v"] == 28
