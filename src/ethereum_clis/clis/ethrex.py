"""Ethrex execution client transition tool."""

from ethereum_test_exceptions import BlockException, ExceptionMapper, TransactionException


class EthrexExceptionMapper(ExceptionMapper):
    """Ethrex exception mapper."""

    mapping_substring = {
        TransactionException.SENDER_NOT_EOA: (
            "reject transactions from senders with deployed code"
        ),
        TransactionException.INITCODE_SIZE_EXCEEDED: "create initcode size limit",
        TransactionException.INSUFFICIENT_MAX_FEE_PER_GAS: "gas price is less than basefee",
        TransactionException.INSUFFICIENT_MAX_FEE_PER_BLOB_GAS: (
            "blob gas price is greater than max fee per blob gas"
        ),
        TransactionException.PRIORITY_GREATER_THAN_MAX_FEE_PER_GAS: (
            "priority fee is greater than max fee"
        ),
        TransactionException.TYPE_3_TX_MAX_BLOB_GAS_ALLOWANCE_EXCEEDED: "Exceeded MAX_BLOB_GAS_PER_BLOCK",
        TransactionException.TYPE_4_EMPTY_AUTHORIZATION_LIST: "empty authorization list",
        TransactionException.TYPE_4_TX_CONTRACT_CREATION: "unexpected length",
        TransactionException.TYPE_4_TX_PRE_FORK: (
            "eip 7702 transactions present in pre-prague payload"
        ),
        TransactionException.INVALID_DEPOSIT_EVENT_LAYOUT: (
            "failed to decode deposit requests from receipts"
        ),
        BlockException.INVALID_REQUESTS: "mismatched block requests hash",
        BlockException.INVALID_RECEIPTS_ROOT: "receipt root mismatch",
        BlockException.INVALID_STATE_ROOT: "mismatched block state root",
        BlockException.INVALID_BLOCK_HASH: "block hash mismatch",
        BlockException.INVALID_GAS_USED: "block gas used mismatch",
        BlockException.INCORRECT_BLOB_GAS_USED: "Blob gas used doesn't match value in header"
    }
    mapping_regex = {
        TransactionException.NONCE_MISMATCH_TOO_LOW: r"nonce \d+ too low, expected \d+",
        TransactionException.INTRINSIC_GAS_TOO_LOW: (
            r"(call gas cost|gas floor) \(\d+\) exceeds the gas limit \(\d+\)"
        ),
        TransactionException.TYPE_3_TX_MAX_BLOB_GAS_ALLOWANCE_EXCEEDED: (
            r"blob gas used \d+ exceeds maximum allowance \d+"
        ),
        TransactionException.TYPE_3_TX_ZERO_BLOBS: (
            r"blob transactions present in pre-cancun payload|empty blobs"
        ),
        TransactionException.INSUFFICIENT_ACCOUNT_FUNDS: (
            r"Invalid Transaction: lack of funds (\d+) for max fee (\d+)"
        ),
        BlockException.SYSTEM_CONTRACT_CALL_FAILED: (
            r"failed to apply .* requests contract call"
        ),
        BlockException.INCORRECT_BLOB_GAS_USED: (
            r"Blob gas used doesn't match value in header"
        ),
        BlockException.INCORRECT_EXCESS_BLOB_GAS: (
            r"excess blob gas \d+ is not a multiple of blob gas per blob|invalid excess blob gas"
        ),
        BlockException.RLP_STRUCTURES_ENCODING: (
            r"Error decoding field `\D+` of type \w+"),
        BlockException.INCORRECT_EXCESS_BLOB_GAS: (
            r".* Excess blob gas is incorrect"
        )
    }
