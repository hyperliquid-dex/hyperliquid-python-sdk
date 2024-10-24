from hyperliquid.utils import constants
from hyperliquid.utils.signing import sign_usd_transfer_action, get_timestamp_ms
from hyperliquid.utils.types import Any, List
import example_utils


def main():
    address, info, exchange = example_utils.setup(constants.TESTNET_API_URL, skip_ws=True)
    multi_sig_wallets = example_utils.setup_multi_sig_wallets()

    multi_sig_user = "0x0000000000000000000000000000000000000005"

    timestamp = get_timestamp_ms()
    action = {
        "type": "usdSend",
        "signatureChainId": "0x66eee",
        "hyperliquidChain": "Testnet",
        "destination": "0x0000000000000000000000000000000000000000",
        "amount": "100.0",
        "time": timestamp,
    }
    signatures: List[Any] = []
    for wallet in multi_sig_wallets:
        signature = sign_usd_transfer_action(wallet, action, False)
        signatures.append(signature)

    multi_sig_result = exchange.multi_sig(multi_sig_user, action, signatures, timestamp)
    print(multi_sig_result)


if __name__ == "__main__":
    main()
