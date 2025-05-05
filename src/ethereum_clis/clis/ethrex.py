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
        TransactionException.TYPE_3_TX_INVALID_BLOB_VERSIONED_HASH: "blob version not supported",
        TransactionException.TYPE_4_EMPTY_AUTHORIZATION_LIST: "empty authorization list",
        TransactionException.TYPE_4_TX_CONTRACT_CREATION: "unexpected length",
        TransactionException.TYPE_4_TX_PRE_FORK: (
            "eip 7702 transactions present in pre-prague payload"
        ),
        TransactionException.INVALID_DEPOSIT_EVENT_LAYOUT: (
            "failed to decode deposit requests from receipts"
        ),
        TransactionException.TYPE_3_TX_PRE_FORK: (
            "blob versioned hashes not supported"
        ),
        TransactionException.TYPE_3_TX_INVALID_BLOB_VERSIONED_HASH: (
            "blob version not supported"
        ),
        BlockException.INVALID_REQUESTS: "Requests hash does not match the one in the header after executing",
        BlockException.INVALID_RECEIPTS_ROOT: "Receipts Root does not match the one in the header after executing",
        BlockException.INVALID_STATE_ROOT: "World State Root does not match the one in the header after executing",
        BlockException.INVALID_GAS_USED: "Gas used doesn't match value in header",
        BlockException.INCORRECT_BLOB_GAS_USED: "Blob gas used doesn't match value in header"
    }
    mapping_regex = {
        TransactionException.NONCE_MISMATCH_TOO_LOW: r"nonce \d+ too low, expected \d+",
        TransactionException.TYPE_3_TX_MAX_BLOB_GAS_ALLOWANCE_EXCEEDED: (
            r"blob gas used \d+ exceeds maximum allowance \d+"
        ),
        TransactionException.TYPE_3_TX_ZERO_BLOBS: (
            r"blob transactions present in pre-cancun payload|empty blobs"
        ),
        TransactionException.INSUFFICIENT_ACCOUNT_FUNDS: (
            r"lack of funds \(\d+\) for max fee \(\d+\)"
        ),
        TransactionException.INTRINSIC_GAS_TOO_LOW: (
            r"gas floor exceeds the gas limit|call gas cost exceeds the gas limit|Intrinsic gas too low"
        ),
        BlockException.SYSTEM_CONTRACT_CALL_FAILED: (
            r"failed to apply .* requests contract call"
        ),
        BlockException.INCORRECT_BLOB_GAS_USED: (
            r"Blob gas used doesn't match value in header"
        ),
        BlockException.RLP_STRUCTURES_ENCODING: (
            r"Error decoding field '\D+' of type \w+.*"
        ),
        BlockException.INCORRECT_EXCESS_BLOB_GAS: (
            r".* Excess blob gas is incorrect"
        ),
        BlockException.INVALID_BLOCK_HASH: (
            r"Invalid block hash. Expected \w+, got \w+"
        )
    }
