import json
import time

import example_utils

from hyperliquid.utils import constants

PURR = "PURR/USDC"


def main():
    address, info, exchange = example_utils.setup(base_url=constants.TESTNET_API_URL, skip_ws=True)

    # Get the user state and print out spot balance information
    spot_user_state = info.spot_user_state(address)
    if len(spot_user_state["balances"]) > 0:
        print("spot balances:")
        for balance in spot_user_state["balances"]:
            print(json.dumps(balance, indent=2))
    else:
        print("no available token balances")

    # Place a TWAP order
    # TWAP orders spread the total size over the specified duration in minutes
    # is_buy=True for buy, False for sell
    # sz=total size to execute over the duration
    # minutes=duration in minutes to spread the order
    # reduce_only=False (can only reduce position if True)
    # randomize=False (randomize execution timing if True)
    twap_result = exchange.twap_order(PURR, True, 20, 5, reduce_only=False, randomize=False)
    print("TWAP order result:")
    print(json.dumps(twap_result, indent=2))

    # Extract TWAP ID from the response
    twap_id = None
    if twap_result["status"] == "ok":
        response_data = twap_result.get("response", {}).get("data", {})
        status_info = response_data.get("status", {})
        if "running" in status_info:
            twap_id = status_info["running"]["twapId"]
            print(f"\n✅ TWAP order placed successfully! TWAP ID: {twap_id}")
            print(f"Order will execute 20 {PURR} over 5 minutes")
        else:
            print(f"\n⚠️ Unexpected TWAP status: {status_info}")
    else:
        print(f"\n❌ TWAP order failed: {twap_result}")
        return

    # Wait a moment to let the TWAP start executing
    print("\nWaiting 15 seconds before cancelling...")
    time.sleep(15)

    # Cancel the TWAP order
    if twap_id is not None:
        print(f"\nCancelling TWAP order ID: {twap_id}")
        cancel_result = exchange.cancel_twap(PURR, twap_id)
        print("TWAP cancel result:")
        print(json.dumps(cancel_result, indent=2))

        if cancel_result["status"] == "ok":
            response_data = cancel_result.get("response", {}).get("data", {})
            if response_data.get("status") == "success":
                print(f"\n✅ TWAP order {twap_id} cancelled successfully!")
            else:
                print(f"\n⚠️ TWAP cancel response: {response_data}")
        else:
            print(f"\n❌ TWAP cancel failed: {cancel_result}")


if __name__ == "__main__":
    main()
