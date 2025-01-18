from hyperliquid.utils import constants
import example_utils

TOKEN_ID = 1169
IS_MAINNET = False

def main():
    
    _, _, exchange = example_utils.setup(constants.MAINNET_API_URL if IS_MAINNET else constants.TESTNET_API_URL, skip_ws=True)

    user_and_wei = [["0xffffffffffffffffffffffffffffffffffffffff","0"]]
    existing_token_and_wei = []
    
    response = exchange.spot_deploy(TOKEN_ID, user_and_wei, existing_token_and_wei)

    print(response)

if __name__ == "__main__":
    main()