import example_utils

from hyperliquid.utils import constants


def main():
    address, info, _ = example_utils.setup(constants.TESTNET_API_URL)
    # An example showing how to subscribe to the different subscription types and prints the returned messages
    # Some subscriptions do not return snapshots, so you will not receive a message until something happens
    info.subscribe({"type": "allMids"}, print)
    info.subscribe({"type": "l2Book", "coin": "ETH"}, print)
    info.subscribe({"type": "trades", "coin": "PURR/USDC"}, print)
    info.subscribe({"type": "userEvents", "user": address}, print)
    info.subscribe({"type": "userFills", "user": address}, print)
    info.subscribe({"type": "candle", "coin": "ETH", "interval": "1m"}, print)
    info.subscribe({"type": "orderUpdates", "user": address}, print)
    info.subscribe({"type": "userFundings", "user": address}, print)
    info.subscribe({"type": "userNonFundingLedgerUpdates", "user": address}, print)
    info.subscribe({"type": "webData2", "user": address}, print)
    info.subscribe({"type": "bbo", "coin": "ETH"}, print)


if __name__ == "__main__":
    main()
