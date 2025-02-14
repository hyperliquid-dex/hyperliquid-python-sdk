from typing import Any

import argparse
import json
import os
from datetime import datetime

import lz4.frame
import msgpack


def decompress_lz4(input_file, output_file):
    with open(input_file, "rb") as f_in:
        compressed_data = f_in.read()

    decompressed_data = lz4.frame.decompress(compressed_data)

    with open(output_file, "wb") as f_out:
        f_out.write(decompressed_data)


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return "0x" + obj.hex()
        return super().default(obj)


class EthBlockIndexer:
    def __init__(self):
        self.blocks = []

    # convert a Buffer object to hex string
    def _convert_buffer(self, buffer_obj: dict[str, Any]) -> str:
        if isinstance(buffer_obj, dict) and buffer_obj.get("type") == "Buffer":
            return "0x" + "".join(f"{x:02x}" for x in buffer_obj["data"])
        return str(buffer_obj)

    # recursively process nested Buffer objects
    def _process_nested_buffers(self, data: Any) -> Any:
        if isinstance(data, dict):
            if data.get("type") == "Buffer":
                return self._convert_buffer(data)
            return {k: self._process_nested_buffers(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._process_nested_buffers(item) for item in data]
        elif isinstance(data, bytes):
            return "0x" + data.hex()
        return data

    def _bytes_to_int(self, value: Any) -> int:
        if isinstance(value, dict) and value.get("type") == "Buffer":
            raw_bytes = bytes(value["data"])
            return int.from_bytes(raw_bytes, byteorder="big")
        elif isinstance(value, bytes):
            return int.from_bytes(value, byteorder="big")
        return 0

    def _process_transaction(self, tx: dict[str, Any]) -> dict[str, Any]:
        if not tx.get("transaction"):
            return {}

        tx_data = tx["transaction"]
        tx_type = next(iter(tx_data.keys()))  # Either 'Legacy' or 'Eip1559'
        tx_content = tx_data[tx_type]

        processed = {
            "type": tx_type,
            "chainId": self._bytes_to_int(tx_content.get("chainId", {"type": "Buffer", "data": []})),
            "nonce": self._bytes_to_int(tx_content.get("nonce", {"type": "Buffer", "data": []})),
            "gas": self._bytes_to_int(tx_content.get("gas", {"type": "Buffer", "data": []})),
            "to": self._process_nested_buffers(tx_content.get("to")),
            "value": self._bytes_to_int(tx_content.get("value", {"type": "Buffer", "data": []})),
            "input": self._process_nested_buffers(tx_content.get("input")),
            "signature": [self._process_nested_buffers(sig) for sig in tx.get("signature", [])],
        }

        if tx_type == "Legacy":
            processed["gasPrice"] = self._bytes_to_int(tx_content.get("gasPrice", {"type": "Buffer", "data": []}))
        elif tx_type == "Eip1559":
            processed.update(
                {
                    "maxFeePerGas": self._bytes_to_int(tx_content.get("maxFeePerGas", {"type": "Buffer", "data": []})),
                    "maxPriorityFeePerGas": self._bytes_to_int(
                        tx_content.get("maxPriorityFeePerGas", {"type": "Buffer", "data": []})
                    ),
                    "accessList": self._process_nested_buffers(tx_content.get("accessList", [])),
                }
            )

        return processed

    def _process_block(self, block_data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(block_data, dict) or "block" not in block_data:
            raise ValueError("invalid block format")

        reth_block = block_data["block"]["Reth115"]
        header = reth_block.get("header", {}).get("header", {})

        processed_block = {
            "hash": self._process_nested_buffers(reth_block["header"].get("hash")),
            "parentHash": self._process_nested_buffers(header.get("parentHash")),
            "sha3Uncles": self._process_nested_buffers(header.get("sha3Uncles")),
            "miner": self._process_nested_buffers(header.get("miner")),
            "stateRoot": self._process_nested_buffers(header.get("stateRoot")),
            "transactionsRoot": self._process_nested_buffers(header.get("transactionsRoot")),
            "receiptsRoot": self._process_nested_buffers(header.get("receiptsRoot")),
            "number": self._bytes_to_int(header.get("number", {"type": "Buffer", "data": []})),
            "gasLimit": self._bytes_to_int(header.get("gasLimit", {"type": "Buffer", "data": []})),
            "gasUsed": self._bytes_to_int(header.get("gasUsed", {"type": "Buffer", "data": []})),
            "timestamp": self._bytes_to_int(header.get("timestamp", {"type": "Buffer", "data": []})),
            "extraData": self._process_nested_buffers(header.get("extraData")),
            "baseFeePerGas": self._bytes_to_int(header.get("baseFeePerGas", {"type": "Buffer", "data": []})),
            "transactions": [
                self._process_transaction(tx) for tx in reth_block.get("body", {}).get("transactions", [])
            ],
        }

        if processed_block["timestamp"]:
            processed_block["datetime"] = datetime.fromtimestamp(processed_block["timestamp"]).isoformat()
        else:
            processed_block["datetime"] = None

        return processed_block

    def process_msgpack_file(self, filename: str) -> None:
        with open(filename, "rb") as f:
            data = msgpack.load(f)
            if isinstance(data, list):
                for block_data in data:
                    processed_block = self._process_block(block_data)
                    self.blocks.append(processed_block)
            else:
                processed_block = self._process_block(data)
                self.blocks.append(processed_block)

    def save_to_json(self, output_filename: str) -> None:
        with open(output_filename, "w") as f:
            json.dump(
                {
                    "blocks": self.blocks,
                    "totalBlocks": len(self.blocks),
                    "totalTransactions": sum(len(block["transactions"]) for block in self.blocks),
                },
                f,
                indent=2,
                cls=BytesEncoder,
            )

    def summarize_blocks(self) -> dict[str, Any]:
        if not self.blocks:
            return {"error": "no blocks processed"}

        total_gas_used = sum(block["gasUsed"] for block in self.blocks)
        total_txs = sum(len(block["transactions"]) for block in self.blocks)

        return {
            "totalBlocks": len(self.blocks),
            "totalTransactions": total_txs,
            "averageGasUsed": total_gas_used / len(self.blocks) if self.blocks else 0,
            "blockNumbers": [block["number"] for block in self.blocks],
            "timeRange": {
                "first": next((b["datetime"] for b in self.blocks if b["datetime"]), None),
                "last": next((b["datetime"] for b in reversed(self.blocks) if b["datetime"]), None),
            },
        }


if __name__ == "__main__":
    # Download ethereum block files from s3://hl-[testnet|mainnet]-evm-blocks
    # and input them into the indexer
    parser = argparse.ArgumentParser(description="index evm blocks")
    parser.add_argument("--data-dir", type=str, required=True)
    parser.add_argument("--start-height", type=int, required=True)
    parser.add_argument("--end-height", type=int, required=True)
    args = parser.parse_args()

    data_dir = args.data_dir
    start_height = args.start_height
    end_height = args.end_height
    mp_flns = []
    for height in range(start_height, end_height + 1):
        lz4_fln = f"{data_dir}/{height}.rmp.lz4"
        if not os.path.exists(lz4_fln):
            raise Exception(
                f"block with height {height} not found - download missing block file(s) using 'aws s3 cp s3://hl-[testnet | mainnet]-evm-blocks/<block_object_path> --request-payer requester'"
            )
        mp_fln = f"{data_dir}/{height}.rmp"
        decompress_lz4(lz4_fln, mp_fln)
        mp_flns.append(mp_fln)

    indexer = EthBlockIndexer()
    for mp_fln in mp_flns:
        indexer.process_msgpack_file(mp_fln)
    print(indexer.summarize_blocks())
    indexer.save_to_json(f"{data_dir}/processed_blocks.json")
