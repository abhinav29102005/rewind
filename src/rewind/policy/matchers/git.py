"""Git fact extraction from argv (``git ...``)."""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING, Any

from .shell_fs import parse_flags

if TYPE_CHECKING:
    from . import Facts

FACT_KEYS = {
    "subcommand", "subsubcommand", "flags", "positionals", "force", "delete", "delete_force",
    "mirror", "protected", "target_unknown", "targets", "hard", "dry_run", "prune_now",
    "release_tag", "discard", "staged_only", "args",
}

DEFAULT_PROTECTED = ["main", "master", "production", "prod", "release/*", "release-*"]
DEFAULT_RELEASE_TAGS = ["v[0-9]*", "release-*", "release/*"]

_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path",
                      "--config-env", "--super-prefix"}


def _strip_ref(r: str) -> str:
    r = r.lstrip("+")
    for p in ("refs/heads/", "refs/tags/", "heads/"):
        if r.startswith(p):
            r = r[len(p):]
    return r


def _matches_any(name: str, globs: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, g) for g in globs)


def extract_argv(args: list[str], params: dict[str, Any] | None = None) -> Facts:
    """``args`` excludes the leading ``git``."""
    params = params or {}
    protected = list(params.get("protected_branches") or DEFAULT_PROTECTED)
    release = list(params.get("release_tag_patterns") or DEFAULT_RELEASE_TAGS)

    i = 0
    while i < len(args) and args[i].startswith("-"):
        a = args[i]
        i += 2 if (a in _GLOBAL_WITH_VALUE and "=" not in a) else 1
    if i >= len(args):
        return {"subcommand": "", "args": args, "flags": [], "positionals": []}
    sub = args[i].lower()
    rest = args[i + 1 :]
    flags, pos = parse_flags(rest)
    facts: Facts = {
        "subcommand": sub,
        "subsubcommand": pos[0].lower() if pos else "",
        "args": rest,
        "flags": sorted(flags),
        "positionals": pos,
    }

    if sub == "push":
        refspecs = pos[1:] if pos else []
        force = bool({"f", "force", "force-with-lease", "force-if-includes"} & flags) or any(
            r.startswith("+") for r in refspecs
        )
        delete = bool({"d", "delete"} & flags) or any(r.startswith(":") for r in refspecs)
        targets = []
        for r in refspecs:
            dst = r.split(":", 1)[1] if ":" in r else r
            if dst:
                targets.append(_strip_ref(dst))
        facts.update(
            force=force,
            delete=delete,
            mirror="mirror" in flags,
            targets=targets,
            target_unknown=not targets,
            # DECISION: an unknown push target counts as protected (fail closed).
            protected=(not targets) or any(_matches_any(t, protected) for t in targets),
        )
    elif sub == "branch":
        names = pos
        delete = bool({"d", "delete", "D"} & flags)
        delete_force = "D" in flags or (delete and bool({"f", "force"} & flags))
        facts.update(
            delete=delete,
            delete_force=delete_force,
            targets=names,
            protected=any(_matches_any(n, protected) for n in names),
            force=bool({"f", "force", "M", "C"} & flags),
        )
    elif sub == "tag":
        delete = bool({"d", "delete"} & flags)
        facts.update(
            delete=delete,
            targets=pos,
            release_tag=any(_matches_any(t, release) for t in pos),
            force=bool({"f", "force"} & flags),
        )
    elif sub == "reset":
        facts["hard"] = bool({"hard", "merge", "keep"} & flags)
    elif sub == "clean":
        facts.update(
            force=bool({"f", "force"} & flags),
            dry_run=bool({"n", "dry-run"} & flags),
        )
    elif sub == "gc":
        facts["prune_now"] = any(
            a in ("--prune=now", "--prune=all") for a in rest
        ) or ("prune" in flags and "now" in pos)
    elif sub in ("checkout", "switch"):
        facts["discard"] = "--" in rest or bool({"f", "force", "discard-changes"} & flags) or (
            sub == "checkout" and pos[:1] == ["."]
        )
        facts["force"] = bool({"f", "force"} & flags)
    elif sub == "restore":
        facts["staged_only"] = bool({"staged", "S"} & flags) and not bool({"worktree", "W"} & flags)
        facts["discard"] = not facts["staged_only"]
    elif sub == "update-ref":
        facts["delete"] = "d" in flags
    elif sub == "stash":
        facts["delete"] = facts["subsubcommand"] in ("drop", "clear")
    return facts


def extract(operation: str, payload: dict[str, Any], params: dict[str, Any]) -> Facts:
    """Structured git action: payload has ``args`` (list) or ``command`` (string)."""
    args = payload.get("args")
    if isinstance(args, list) and all(isinstance(a, str) for a in args):
        if args and args[0] == "git":
            args = args[1:]
        return extract_argv(list(args), params)
    return extract_argv([operation, *[str(a) for a in payload.get("argv", [])]], params)
