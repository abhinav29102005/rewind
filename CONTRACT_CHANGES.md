# Contract Changes Log

This document tracks all changes made to `src/rewind/contracts.py`. Changes must remain strictly additive.

---

## Initial Phase 2 & 3 Specification Baseline

### Status: Compliant (Additive Only)

All interfaces and protocols from Section 2 of the Phase 2/3 specification are implemented as specified:
- `RiskClass`: Enum with `SAFE`, `REVERSIBLE`, `IRREVERSIBLE`.
- `ActionRequest`: Pydantic model with canonical serialization.
- `Classification`: Pydantic model with `risk`, `rule_id`, `pack`, `reason`, `needs_snapshot`.
- `action_hash()`: Deterministic SHA-256 canonical hash function for action request binding.
- `Classifier`, `SnapshotBackend`, `ApprovalChannel`, `AuditLog`, `TokenBroker`: Runtime-checkable protocols.
- `NotificationEvent` and `NotificationEventType`: Event data structures for multi-channel dispatch.

### Additive Helpers
- Added `risk_rank(r: RiskClass) -> int`: Strict numerical ordering helper (`safe=0`, `reversible=1`, `irreversible=2`).
- Added `stricter(a: RiskClass, b: RiskClass) -> RiskClass`: Helper to select the stricter of two risk classes.
- Added `REWIND_API_VERSION = "1.0"`: Version string for plugin compatibility checking.
