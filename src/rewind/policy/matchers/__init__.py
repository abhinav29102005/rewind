"""Fact extractors and the generic rule-matching language.

Each matcher turns an action (or a shell segment routed to it) into one or more
*units*: flat dicts of facts. Rules in policy packs match against facts using:

- ``key: value``        equality (case-insensitive for strings); a list means "any of"
- ``key: present``      fact is truthy; ``key: absent`` fact is falsy/missing
- ``key_in: [...]``     same as a list value (kept for readability, e.g. ``object_in``)
- ``key_any: [...]``    fact is a list containing at least one of the values
- ``key_all: [...]``    fact is a list containing all of the values
- ``key_prefix: [...]`` fact (string) starts with any of the values
- ``key_glob: [...]``   fact (string) matches any fnmatch glob

Every key in a rule must match for the rule to fire. A missing fact never matches
(except ``absent``).
"""

from __future__ import annotations

import fnmatch
from typing import Any

Facts = dict[str, Any]

PARSE_ERROR = "parse_error"

_OPS = ("_in", "_any", "_all", "_prefix", "_glob")


def split_key(key: str) -> tuple[str, str]:
    for op in _OPS:
        if key.endswith(op):
            return key[: -len(op)], op
    return key, ""


def _norm(v: Any) -> Any:
    return v.lower() if isinstance(v, str) else v


def _as_list(v: Any) -> list[Any]:
    return list(v) if isinstance(v, list | tuple | set | frozenset) else [v]


def _cond(fact: Any, op: str, expected: Any) -> bool:
    if expected == "present" and op == "":
        return bool(fact)
    if expected == "absent" and op == "":
        return not fact
    if fact is None:
        return False
    if op in ("", "_in"):
        wanted = {_norm(x) for x in _as_list(expected)}
        if isinstance(fact, list | tuple | set | frozenset):
            return any(_norm(f) in wanted for f in fact)
        return _norm(fact) in wanted
    facts = {_norm(f) for f in _as_list(fact)}
    if op == "_any":
        return any(_norm(x) in facts for x in _as_list(expected))
    if op == "_all":
        return all(_norm(x) in facts for x in _as_list(expected))
    if op == "_prefix":
        return isinstance(fact, str) and any(
            fact.lower().startswith(str(p).lower()) for p in _as_list(expected)
        )
    if op == "_glob":
        return isinstance(fact, str) and any(
            fnmatch.fnmatchcase(fact.lower(), str(p).lower()) for p in _as_list(expected)
        )
    return False


def rule_matches(match: dict[str, Any], facts: Facts) -> bool:
    if not match:
        return False  # DECISION: an empty match never fires (prevents catch-all typos).
    for key, expected in match.items():
        base, op = split_key(key)
        if not _cond(facts.get(base), op, expected):
            return False
    return True
