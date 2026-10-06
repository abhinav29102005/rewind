"""AWS fact extraction: service + API action name, from structured calls or the AWS CLI."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from .shell_fs import parse_flags

if TYPE_CHECKING:
    from . import Facts

FACT_KEYS = {
    "service", "api_action", "grants_admin", "policy_unknown", "versioning_status",
    "lifecycle_expiration", "public_principal", "recursive", "bucket", "params",
}

ADMIN_POLICY_SUFFIXES = ("/AdministratorAccess", "/IAMFullAccess", "/PowerUserAccess")

# High-level `aws s3 <cmd>` to API actions it performs.
_S3_HIGH_LEVEL: dict[str, list[str]] = {
    "ls": ["ListObjectsV2"],
    "cp": ["PutObject"],
    "mv": ["PutObject", "DeleteObject"],
    "rm": ["DeleteObject"],
    "sync": ["PutObject"],
    "mb": ["CreateBucket"],
    "rb": ["DeleteBucket"],
    "presign": ["GetObject"],
    "website": ["PutBucketWebsite"],
}

_GLOBAL_WITH_VALUE = {"--profile", "--region", "--output", "--endpoint-url", "--query",
                      "--cli-read-timeout", "--cli-connect-timeout", "--color", "--ca-bundle"}


def kebab_to_pascal(s: str) -> str:
    return "".join(p[:1].upper() + p[1:] for p in s.split("-") if p)


def _load_doc(v: Any) -> tuple[Any, bool]:
    """Return (parsed_document, unknown)."""
    if isinstance(v, dict | list):
        return v, False
    if isinstance(v, str):
        if v.startswith(("file://", "fileb://", "http://", "https://")):
            return None, True
        try:
            return json.loads(v), False
        except ValueError:
            return None, True
    return None, v is not None


def _walk_statements(doc: Any) -> list[dict[str, Any]]:
    if not isinstance(doc, dict):
        return []
    st = doc.get("Statement", [])
    if isinstance(st, dict):
        st = [st]
    return [s for s in st if isinstance(s, dict)]


def _as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else [v]


def _derive(service: str, api: str, params: dict[str, Any]) -> Facts:
    facts: Facts = {"service": service, "api_action": api, "params": sorted(params)}
    lower = {k.lower(): v for k, v in params.items()}
    bucket = lower.get("bucket")
    if bucket:
        facts["bucket"] = str(bucket)
    arn = str(lower.get("policyarn") or "")
    doc_raw = lower.get("policydocument", lower.get("policy"))
    doc, unknown = _load_doc(doc_raw)
    grants_admin = arn.endswith(ADMIN_POLICY_SUFFIXES)
    public = False
    for s in _walk_statements(doc):
        if str(s.get("Effect", "Allow")) != "Allow":
            continue
        actions = [str(a) for a in _as_list(s.get("Action", []))]
        if any(a == "*" or a.endswith(":*") and a.split(":")[0] in ("iam", "*") for a in actions):
            grants_admin = True
        principal = s.get("Principal")
        if principal == "*" or (isinstance(principal, dict) and "*" in _as_list(principal.get("AWS", []))):
            public = True
    facts["grants_admin"] = grants_admin
    facts["policy_unknown"] = unknown
    facts["public_principal"] = public
    vc = lower.get("versioningconfiguration")
    if isinstance(vc, str) and vc.strip().startswith("{"):
        vc, _ = _load_doc(vc)
    if isinstance(vc, dict):
        facts["versioning_status"] = str(vc.get("Status", ""))
    elif isinstance(vc, str):  # shorthand "Status=Suspended"
        for part in vc.split(","):
            k, _, v = part.partition("=")
            if k.strip().lower() == "status":
                facts["versioning_status"] = v.strip()
    lc = lower.get("lifecycleconfiguration")
    lc_doc, lc_unknown = _load_doc(lc)
    if lc is not None:
        rules = lc_doc.get("Rules", []) if isinstance(lc_doc, dict) else []
        facts["lifecycle_expiration"] = lc_unknown or any(
            isinstance(r, dict) and ("Expiration" in r or "NoncurrentVersionExpiration" in r)
            for r in rules
        )
    return facts


def extract_structured(service: str, operation: str, payload: dict[str, Any]) -> list[Facts]:
    api = str(payload.get("action") or operation)
    if "-" in api or api[:1].islower():
        api = kebab_to_pascal(api)
    params = payload.get("params") or {k: v for k, v in payload.items() if k not in ("action", "service")}
    if not isinstance(params, dict):
        params = {}
    return [_derive(service, api, params)]


def extract_cli(args: list[str]) -> list[Facts]:
    """``args`` excludes the leading ``aws``. Returns one unit per API action performed."""
    i = 0
    while i < len(args) and args[i].startswith("-"):
        i += 2 if (args[i] in _GLOBAL_WITH_VALUE and "=" not in args[i]) else 1
    if i + 1 >= len(args):
        return [{"service": args[i] if i < len(args) else "", "api_action": ""}]
    service, cmd, rest = args[i].lower(), args[i + 1], args[i + 2 :]
    flags, pos = parse_flags(rest)
    params: dict[str, Any] = {}
    j = 0
    while j < len(rest):
        a = rest[j]
        if a.startswith("--"):
            key = kebab_to_pascal(a[2:].split("=", 1)[0])
            if "=" in a:
                params[key] = a.split("=", 1)[1]
            elif j + 1 < len(rest) and not rest[j + 1].startswith("--"):
                params[key] = rest[j + 1]
                j += 1
            else:
                params[key] = True
        j += 1
    if service == "s3" and cmd in _S3_HIGH_LEVEL:
        apis = list(_S3_HIGH_LEVEL[cmd])
        recursive = "recursive" in flags
        if cmd == "rm" and recursive:
            apis = ["DeleteObjects"]
        if cmd == "sync" and "delete" in flags:
            apis.append("DeleteObjects")
        if cmd == "rb" and "force" in flags:
            apis = ["DeleteObjects", "DeleteBucket"]
        out = []
        for api in apis:
            f = _derive("s3", api, params)
            f["recursive"] = recursive
            if pos and pos[0].startswith("s3://"):
                f["bucket"] = pos[0][5:].split("/", 1)[0]
            out.append(f)
        return out
    if service == "s3":
        return [{"service": "s3", "api_action": kebab_to_pascal(cmd)}]
    if service == "s3api":
        service = "s3"
    return [_derive(service, kebab_to_pascal(cmd), params)]
