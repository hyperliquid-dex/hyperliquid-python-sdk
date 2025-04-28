import argparse
import json
import os
from collections import defaultdict

import lz4.frame

from hyperliquid.utils.signing import TOKEN_DELEGATE_TYPES, recover_user_from_user_signed_action

REPLICA_CMD_BATCH_SIZE = 10000


def decompress_lz4(input_file, output_file):
    with open(input_file, "rb") as f_in:
        compressed_data = f_in.read()

    decompressed_data = lz4.frame.decompress(compressed_data)

    with open(output_file, "wb") as f_out:
        f_out.write(decompressed_data)


def main():
    parser = argparse.ArgumentParser(description="parse token delegate actions from replica cmds")
    parser.add_argument("--data-dir", type=str, required=True)
    parser.add_argument("--start-height", type=int, required=True)
    parser.add_argument("--end-height", type=int, required=True)
    args = parser.parse_args()

    data_dir = args.data_dir
    start_height = args.start_height
    end_height = args.end_height

    if start_height % REPLICA_CMD_BATCH_SIZE == 0:
        raise Exception("start height is not aligned with replica cmd batch size")
    if end_height % REPLICA_CMD_BATCH_SIZE == 0:
        raise Exception("end height is not aligned with replica cmd batch size")

    flns = []
    for height in range(start_height, end_height, REPLICA_CMD_BATCH_SIZE):
        lz4_fln = f"{data_dir}/{height}.lz4"
        if not os.path.exists(lz4_fln):
            raise Exception(
                f"replica cmds file at {height} not found - download missing block files(s) using 'aws s3 cp s3://hl-[testnet | mainnet]-replica-cmds/<block_object_path> --request-payer requester'"
            )
        fln = f"{data_dir}/{height}"
        decompress_lz4(lz4_fln, fln)
        flns.append(fln)

    user_to_validator_to_amount: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for fln in flns:
        f = open(fln)
        lines = f.readlines()
        for line in lines:
            if "tokenDelegate" not in line:
                continue
            data = json.loads(line)
            bundles = data["abci_block"]["signed_action_bundles"]
            for bundle in bundles:
                for signed_action in bundle[1]["signed_actions"]:
                    action = signed_action["action"]
                    if action["type"] != "tokenDelegate":
                        continue
                    validator = action["validator"]
                    wei = action["wei"]
                    is_delegate = not action["isUndelegate"]
                    user = recover_user_from_user_signed_action(
                        action,
                        signed_action["signature"],
                        TOKEN_DELEGATE_TYPES,
                        "HyperliquidTransaction:TokenDelegate",
                        True,
                    )
                    if not is_delegate:
                        wei = -wei
                    user_to_validator_to_amount[user][validator] += wei / 100_000_000  # native token wei decimals

    print("user to validator to wei amount delegated", user_to_validator_to_amount)


if __name__ == "__main__":
    main()
