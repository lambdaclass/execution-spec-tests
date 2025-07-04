"""Hyperledger Besu Transition tool frontend."""

import json
import os
import re
import subprocess
import tempfile
import textwrap
from pathlib import Path
from typing import ClassVar, Dict, Optional

import requests  # type: ignore

from ethereum_test_exceptions import (
    BlockException,
    ExceptionBase,
    ExceptionMapper,
    TransactionException,
)
from ethereum_test_forks import Fork

from ..transition_tool import TransitionTool, dump_files_to_directory, model_dump_config
from ..types import TransitionToolOutput


class BesuTransitionTool(TransitionTool):
    """Besu EvmTool Transition tool frontend wrapper class."""

    default_binary = Path("evm")
    detect_binary_pattern = re.compile(r"^Besu evm .*$")
    binary: Path
    cached_version: Optional[str] = None
    trace: bool
    process: Optional[subprocess.Popen] = None
    server_url: str
    besu_trace_dir: Optional[tempfile.TemporaryDirectory]

    def __init__(
        self,
        *,
        binary: Optional[Path] = None,
        trace: bool = False,
    ):
        """Initialize the BesuTransitionTool class."""
        super().__init__(exception_mapper=BesuExceptionMapper(), binary=binary, trace=trace)
        args = [str(self.binary), "t8n", "--help"]
        try:
            result = subprocess.run(args, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            raise Exception(
                f"evm process unexpectedly returned a non-zero status code: {e}."
            ) from e
        except Exception as e:
            raise Exception(f"Unexpected exception calling evm tool: {e}.") from e
        self.help_string = result.stdout
        self.besu_trace_dir = tempfile.TemporaryDirectory() if self.trace else None

    def start_server(self):
        """
        Start the t8n-server process, extract the port, and leave it running
        for future reuse.
        """
        args = [
            str(self.binary),
            "t8n-server",
            "--port=0",  # OS assigned server port
        ]

        if self.trace:
            args.append("--trace")
            args.append(f"--output.basedir={self.besu_trace_dir.name}")

        self.process = subprocess.Popen(
            args=args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        while True:
            line = str(self.process.stdout.readline())

            if not line or "Failed to start transition server" in line:
                raise Exception("Failed starting Besu subprocess\n" + line)
            if "Transition server listening on" in line:
                port = re.search("Transition server listening on (\\d+)", line).group(1)
                self.server_url = f"http://localhost:{port}/"
                break

    def shutdown(self):
        """Stop the t8n-server process if it was started."""
        if self.process:
            self.process.kill()
        if self.besu_trace_dir:
            self.besu_trace_dir.cleanup()

    def evaluate(
        self,
        *,
        transition_tool_data: TransitionTool.TransitionToolData,
        debug_output_path: str = "",
        slow_request: bool = False,
    ) -> TransitionToolOutput:
        """Execute `evm t8n` with the specified arguments."""
        if not self.process:
            self.start_server()

        input_json = transition_tool_data.to_input().model_dump(mode="json", **model_dump_config)

        state_json = {
            "fork": transition_tool_data.fork_name,
            "chainid": transition_tool_data.chain_id,
            "reward": transition_tool_data.reward,
        }

        post_data = {"state": state_json, "input": input_json}

        if debug_output_path:
            post_data_string = json.dumps(post_data, indent=4)
            additional_indent = " " * 16  # for pretty indentation in t8n.sh
            indented_post_data_string = "{\n" + "\n".join(
                additional_indent + line for line in post_data_string[1:].splitlines()
            )
            t8n_script = textwrap.dedent(
                f"""\
                #!/bin/bash
                # Use $1 as t8n-server port if provided, else default to 3000
                PORT=${{1:-3000}}
                curl http://localhost:${{PORT}}/ -X POST -H "Content-Type: application/json" \\
                --data '{indented_post_data_string}'
                """
            )
            dump_files_to_directory(
                debug_output_path,
                {
                    "state.json": state_json,
                    "input/alloc.json": input_json["alloc"],
                    "input/env.json": input_json["env"],
                    "input/txs.json": input_json["txs"],
                    "t8n.sh+x": t8n_script,
                },
            )

        response = requests.post(self.server_url, json=post_data, timeout=5)
        response.raise_for_status()  # exception visible in pytest failure output
        output: TransitionToolOutput = TransitionToolOutput.model_validate(
            response.json(), context={"exception_mapper": self.exception_mapper}
        )

        if debug_output_path:
            dump_files_to_directory(
                debug_output_path,
                {
                    "response.txt": response.text,
                    "status_code.txt": response.status_code,
                    "time_elapsed_seconds.txt": response.elapsed.total_seconds(),
                },
            )

        if response.status_code != 200:
            raise Exception(
                f"t8n-server returned status code {response.status_code}, "
                f"response: {response.text}"
            )

        if debug_output_path:
            dump_files_to_directory(
                debug_output_path,
                {
                    "output/alloc.json": output.alloc.model_dump(mode="json", **model_dump_config),
                    "output/result.json": output.result.model_dump(
                        mode="json", **model_dump_config
                    ),
                    "output/txs.rlp": str(output.body),
                },
            )

        if self.trace and self.besu_trace_dir:
            self.collect_traces(output.result.receipts, self.besu_trace_dir, debug_output_path)
            for i, r in enumerate(output.result.receipts):
                trace_file_name = f"trace-{i}-{r.transaction_hash}.jsonl"
                os.remove(os.path.join(self.besu_trace_dir.name, trace_file_name))

        return output

    def is_fork_supported(self, fork: Fork) -> bool:
        """Return True if the fork is supported by the tool."""
        return fork.transition_tool_name() in self.help_string


class BesuExceptionMapper(ExceptionMapper):
    """Translate between EEST exceptions and error strings returned by Besu."""

    mapping_substring: ClassVar[Dict[ExceptionBase, str]] = {
        TransactionException.NONCE_IS_MAX: "invalid Nonce must be less than",
        TransactionException.INSUFFICIENT_MAX_FEE_PER_BLOB_GAS: (
            "transaction invalid tx max fee per blob gas less than block blob gas fee"
        ),
        TransactionException.GASLIMIT_PRICE_PRODUCT_OVERFLOW: (
            "invalid Upfront gas cost cannot exceed 2^256 Wei"
        ),
        TransactionException.INSUFFICIENT_MAX_FEE_PER_GAS: (
            "transaction invalid gasPrice is less than the current BaseFee"
        ),
        TransactionException.GAS_ALLOWANCE_EXCEEDED: "provided gas insufficient",
        TransactionException.PRIORITY_GREATER_THAN_MAX_FEE_PER_GAS: (
            "transaction invalid max priority fee per gas cannot be greater than max fee per gas"
        ),
        TransactionException.TYPE_3_TX_INVALID_BLOB_VERSIONED_HASH: "Invalid versionedHash",
        TransactionException.TYPE_3_TX_CONTRACT_CREATION: (
            "transaction invalid transaction blob transactions must have a to address"
        ),
        TransactionException.TYPE_3_TX_WITH_FULL_BLOBS: (
            "Failed to decode transactions from block parameter"
        ),
        TransactionException.TYPE_3_TX_ZERO_BLOBS: (
            "Failed to decode transactions from block parameter"
        ),
        TransactionException.TYPE_3_TX_MAX_BLOB_GAS_ALLOWANCE_EXCEEDED: "Invalid Blob Count",
        TransactionException.TYPE_3_TX_BLOB_COUNT_EXCEEDED: "Invalid Blob Count",
        TransactionException.TYPE_3_TX_PRE_FORK: (
            "Transaction type BLOB is invalid, accepted transaction types are"
        ),
        TransactionException.TYPE_4_EMPTY_AUTHORIZATION_LIST: (
            "transaction invalid transaction code delegation transactions must have a "
            "non-empty code delegation list"
        ),
        TransactionException.TYPE_4_TX_CONTRACT_CREATION: (
            "transaction invalid transaction code delegation transactions must have a to address"
        ),
        TransactionException.TYPE_4_TX_PRE_FORK: (
            "transaction invalid Transaction type DELEGATE_CODE is invalid"
        ),
        BlockException.RLP_STRUCTURES_ENCODING: (
            "Failed to decode transactions from block parameter"
        ),
        BlockException.INCORRECT_EXCESS_BLOB_GAS: (
            "Payload excessBlobGas does not match calculated excessBlobGas"
        ),
        BlockException.BLOB_GAS_USED_ABOVE_LIMIT: (
            "Payload BlobGasUsed does not match calculated BlobGasUsed"
        ),
        BlockException.INCORRECT_BLOB_GAS_USED: (
            "Payload BlobGasUsed does not match calculated BlobGasUsed"
        ),
        BlockException.INVALID_GAS_USED_ABOVE_LIMIT: "Header validation failed (FULL)",
    }
    mapping_regex = {
        BlockException.INVALID_REQUESTS: (
            r"Invalid execution requests|Requests hash mismatch, calculated: 0x[0-9a-f]+ header: "
            r"0x[0-9a-f]+"
        ),
        BlockException.INVALID_BLOCK_HASH: (
            r"Computed block hash 0x[0-9a-f]+ does not match block hash parameter 0x[0-9a-f]+"
        ),
        BlockException.SYSTEM_CONTRACT_CALL_FAILED: (
            r"System call halted|System call did not execute to completion"
        ),
        BlockException.SYSTEM_CONTRACT_EMPTY: (
            r"(Invalid system call, no code at address)|" r"(Invalid system call address:)"
        ),
        BlockException.INVALID_DEPOSIT_EVENT_LAYOUT: (
            r"Invalid (amount|index|pubKey|signature|withdrawalCred) (offset|size): "
            r"expected (\d+), but got (-?\d+)|"
            r"Invalid deposit log length\. Must be \d+ bytes, but is \d+ bytes"
        ),
        BlockException.RLP_BLOCK_LIMIT_EXCEEDED: (
            r"Block size of \d+ bytes exceeds limit of \d+ bytes"
        ),
        TransactionException.INITCODE_SIZE_EXCEEDED: (
            r"transaction invalid Initcode size of \d+ exceeds maximum size of \d+"
        ),
        TransactionException.INSUFFICIENT_ACCOUNT_FUNDS: (
            r"transaction invalid transaction up-front cost 0x[0-9a-f]+ exceeds transaction "
            r"sender account balance 0x[0-9a-f]+"
        ),
        TransactionException.INTRINSIC_GAS_TOO_LOW: (
            r"transaction invalid intrinsic gas cost \d+ exceeds gas limit \d+"
        ),
        TransactionException.INTRINSIC_GAS_BELOW_FLOOR_GAS_COST: (
            r"transaction invalid intrinsic gas cost \d+ exceeds gas limit \d+"
        ),
        TransactionException.SENDER_NOT_EOA: (
            r"transaction invalid Sender 0x[0-9a-f]+ has deployed code and so is not authorized "
            r"to send transactions"
        ),
        TransactionException.NONCE_MISMATCH_TOO_LOW: (
            r"transaction invalid transaction nonce \d+ below sender account nonce \d+"
        ),
        TransactionException.GAS_LIMIT_EXCEEDS_MAXIMUM: (
            r"transaction invalid Transaction gas limit must be at most \d+"
        ),
    }
