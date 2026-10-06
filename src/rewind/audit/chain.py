"""
Hash-chain verification for tamper-evident audit logs.

Each log entry includes a SHA-256 hash of the previous entry, forming
a chain that can be verified at any time. If any entry has been modified,
the chain breaks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ChainEntry:
    """An entry in the hash chain."""

    index: int
    data_hash: str
    prev_hash: str
    chain_hash: str  # SHA-256(index + data_hash + prev_hash)

    def to_dict(self) -> dict[str, str | int]:
        return {
            "index": self.index,
            "data_hash": self.data_hash,
            "prev_hash": self.prev_hash,
            "chain_hash": self.chain_hash,
        }


GENESIS_HASH = "0" * 64  # The "previous hash" for the first entry


def compute_data_hash(data: dict[str, object]) -> str:
    """Compute a deterministic SHA-256 hash of a data dict."""
    canonical = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def compute_chain_hash(index: int, data_hash: str, prev_hash: str) -> str:
    """Compute the chain hash for a single entry."""
    payload = f"{index}:{data_hash}:{prev_hash}"
    return hashlib.sha256(payload.encode()).hexdigest()


def create_entry(index: int, data: dict[str, object], prev_hash: str) -> ChainEntry:
    """Create a new chain entry from raw data and the previous hash."""
    data_hash = compute_data_hash(data)
    chain_hash = compute_chain_hash(index, data_hash, prev_hash)
    return ChainEntry(
        index=index,
        data_hash=data_hash,
        prev_hash=prev_hash,
        chain_hash=chain_hash,
    )


def verify_entry(entry: ChainEntry, data: dict[str, object], expected_prev_hash: str) -> bool:
    """Verify a single entry against its data and expected previous hash."""
    if entry.prev_hash != expected_prev_hash:
        return False
    if entry.data_hash != compute_data_hash(data):
        return False
    expected_chain_hash = compute_chain_hash(entry.index, entry.data_hash, entry.prev_hash)
    return entry.chain_hash == expected_chain_hash
