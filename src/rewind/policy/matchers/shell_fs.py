"""Shell and filesystem fact extraction (shlex based).

A command string is split into *segments* at ``;``, ``&&``, ``||``, ``|``,
``&`` and unquoted newlines. Command substitutions (``$(...)``, backticks,
``<(...)``) are extracted and classified as their own segments. Wrappers such
as ``sudo``, ``env``, ``xargs``, ``sh -c``, ``ssh host cmd``, ``docker exec``
and ``find -exec`` are unwrapped so the inner command is classified too.

Anything that cannot be tokenized yields a parse-error unit (irreversible).
"""

from __future__ import annotations

import os
import shlex
from dataclasses import dataclass, field
from typing import Any

from . import PARSE_ERROR, Facts

FACT_KEYS = {
    "kind", "program", "args", "flags", "positionals", "recursive", "force",
    "program_dynamic", "inline_code", "device_target", "overwrites_existing",
    "no_clobber", "op", "target", "operation", "path", "find_delete", "find_exec",
    "dd_output", "targets_root", "interpreter", "sql_inline", PARSE_ERROR,
}

SUBST = "__REWIND_SUBST__"
MAX_CMD_CHARS = 100_000
MAX_DEPTH = 6

_SEPARATORS = {";", "&&", "||", "|", "&", "|&", ";;", "(", ")", "{", "}", "!"}
_REDIRECTS = {">", ">>", ">|", "&>", "&>>", "<", "<<", "<<<", "<>", ">&", "<&"}
_ROOTISH = {"/", "/*", "~", "~/", "~/*", "$HOME", "${HOME}", ".", "./", "./*", "..", "*", "/.*"}
_SAFE_DEVICES = {"/dev/null", "/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/zero"}

# Interpreters that can run opaque inline code.
_INTERPRETERS = {
    "python": ("-c",), "python3": ("-c",), "python2": ("-c",), "pypy": ("-c",),
    "node": ("-e", "--eval", "-p", "--print"), "deno": ("eval",), "bun": ("-e", "--eval"),
    "perl": ("-e", "-E"), "ruby": ("-e",), "php": ("-r",), "lua": ("-e",),
    "osascript": ("-e",), "powershell": ("-c", "-command"), "pwsh": ("-c", "-command"),
}
_SHELLS = {"sh", "bash", "zsh", "dash", "ksh", "fish", "ash", "busybox"}


@dataclass
class Segment:
    argv: list[str]
    redirects: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None


class _ScanError(ValueError):
    pass


def _prescan(cmd: str, depth: int) -> tuple[str, list[str]]:
    """Quote-aware pass: strip comments, newline -> ';', extract substitutions."""
    out: list[str] = []
    subs: list[str] = []
    i, n = 0, len(cmd)
    in_s = in_d = False
    prev_is_space = True
    while i < n:
        c = cmd[i]
        if in_s:
            out.append(c)
            if c == "'":
                in_s = False
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            if cmd[i + 1] == "\n":  # line continuation
                i += 2
                continue
            out.append(cmd[i : i + 2])
            i += 2
            prev_is_space = False
            continue
        if c == '"':
            in_d = not in_d
            out.append(c)
            i += 1
            prev_is_space = False
            continue
        if not in_d and c == "'":
            in_s = True
            out.append(c)
            i += 1
            prev_is_space = False
            continue
        # Command / process substitution.
        if (c == "$" or (not in_d and c in "<>")) and i + 1 < n and cmd[i + 1] == "(":
            if c == "$" and i + 2 < n and cmd[i + 2] == "(":
                # $(( arithmetic )) - no command execution, but keep it opaque-safe.
                end = cmd.find("))", i + 3)
                if end == -1:
                    raise _ScanError("unterminated arithmetic expansion")
                out.append("0")
                i = end + 2
                continue
            j, level, q_s, q_d = i + 2, 1, False, False
            while j < n and level:
                ch = cmd[j]
                if q_s:
                    q_s = ch != "'"
                elif ch == "\\":
                    j += 1
                elif ch == "'" and not q_d:
                    q_s = True
                elif ch == '"':
                    q_d = not q_d
                elif not q_d and ch == "(":
                    level += 1
                elif not q_d and ch == ")":
                    level -= 1
                j += 1
            if level:
                raise _ScanError("unterminated command substitution")
            subs.append(cmd[i + 2 : j - 1])
            out.append(SUBST)
            i = j
            prev_is_space = False
            continue
        if c == "`":
            j = i + 1
            while j < n and cmd[j] != "`":
                j += 2 if cmd[j] == "\\" else 1
            if j >= n:
                raise _ScanError("unterminated backtick substitution")
            subs.append(cmd[i + 1 : j])
            out.append(SUBST)
            i = j + 1
            prev_is_space = False
            continue
        if not in_d and c == "#" and prev_is_space:
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        if not in_d and c in "\n\r":
            out.append(" ; ")
            i += 1
            prev_is_space = True
            continue
        out.append(c)
        prev_is_space = c.isspace() or (not in_d and c in ";&|()")
        i += 1
    if in_s or in_d:
        raise _ScanError("unbalanced quotes")
    return "".join(out), subs


def split_segments(cmd: str, depth: int = 0) -> list[Segment]:
    """Tokenize a shell command into segments. Never raises."""
    if not isinstance(cmd, str) or not cmd.strip():
        return [Segment([], error="empty command")]
    if len(cmd) > MAX_CMD_CHARS or depth > MAX_DEPTH:
        return [Segment([], error="command too large or too deeply nested")]
    try:
        cleaned, subs = _prescan(cmd, depth)
        lx = shlex.shlex(cleaned, posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        lx.commenters = ""  # comments handled (quote-aware) in _prescan
        tokens = list(lx)
    except (ValueError, _ScanError) as e:
        return [Segment([], error=f"could not parse command ({e})")]

    segments: list[Segment] = []
    cur = Segment([])
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in _SEPARATORS:
            if cur.argv or cur.redirects:
                segments.append(cur)
            cur = Segment([])
            i += 1
            continue
        if t in _REDIRECTS:
            # Drop a lone fd number immediately preceding the operator (e.g. "2>").
            if cur.argv and cur.argv[-1].isdigit() and len(cur.argv) > 1:
                cur.argv.pop()
            target = tokens[i + 1] if i + 1 < len(tokens) else ""
            cur.redirects.append((t, target))
            i += 2
            continue
        cur.argv.append(t)
        i += 1
    if cur.argv or cur.redirects:
        segments.append(cur)
    for s in subs:
        segments.extend(split_segments(s, depth + 1))
    if not segments:
        return [Segment([], error="no command found")]
    return segments


def _is_assignment(tok: str) -> bool:
    if "=" not in tok or tok.startswith("="):
        return False
    name = tok.split("=", 1)[0]
    return name.replace("_", "a").isalnum() and not name[0].isdigit()


def program_name(tok: str) -> str:
    base = tok.replace("\\", "/").rsplit("/", 1)[-1]
    if base.lower().endswith(".exe"):
        base = base[:-4]
    return base


def _skip_opts(args: list[str], with_value: set[str]) -> list[str]:
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            return args[i + 1 :]
        if not a.startswith("-") or a == "-":
            return args[i:]
        i += 2 if (a in with_value and "=" not in a) else 1
    return []


_WRAPPER_OPTS: dict[str, set[str]] = {
    "sudo": {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-T"},
    "doas": {"-u", "-C"},
    "nice": {"-n"},
    "ionice": {"-c", "-n", "-p"},
    "stdbuf": {"-i", "-o", "-e"},
    "nohup": set(),
    "time": {"-f", "-o"},
    "command": set(),
    "builtin": set(),
    "exec": {"-a"},
    "chroot": set(),
    "setsid": set(),
    "unbuffer": set(),
    "caffeinate": set(),
    "watch": {"-n", "-d", "--interval"},
    "flock": {"-w", "-E", "--timeout"},
}


def unwrap(argv: list[str], depth: int = 0) -> list[list[str]]:
    """Return the argv itself plus any inner commands it will execute."""
    if not argv or depth > MAX_DEPTH:
        return [argv] if argv else []
    # Leading VAR=value assignments.
    k = 0
    while k < len(argv) and _is_assignment(argv[k]):
        k += 1
    argv = argv[k:]
    if not argv:
        return []
    prog = program_name(argv[0])
    rest = argv[1:]
    if prog in _WRAPPER_OPTS:
        inner = _skip_opts(rest, _WRAPPER_OPTS[prog])
        if prog == "chroot" and inner:
            inner = inner[1:]
        return unwrap(inner, depth + 1) if inner else [argv]
    if prog == "env":
        inner = _skip_opts(rest, {"-u", "-C", "-S", "--unset", "--chdir"})
        while inner and _is_assignment(inner[0]):
            inner = inner[1:]
        return unwrap(inner, depth + 1) if inner else [argv]
    if prog == "timeout":
        inner = _skip_opts(rest, {"-s", "-k", "--signal", "--kill-after"})
        return unwrap(inner[1:], depth + 1) if len(inner) > 1 else [argv]
    if prog == "xargs":
        inner = _skip_opts(
            rest, {"-I", "-i", "-L", "-l", "-n", "-P", "-s", "-d", "-E", "-a", "--max-args",
                   "--max-procs", "--delimiter", "--arg-file", "--replace"}
        )
        return [argv, *unwrap(inner, depth + 1)] if inner else [argv]
    if prog in _SHELLS:
        for idx, a in enumerate(rest):
            if a == "-c" or (a.startswith("-") and not a.startswith("--") and "c" in a[1:]):
                if idx + 1 < len(rest):
                    return [argv] + _nested(rest[idx + 1], depth + 1)
                return [argv]
        return [argv]
    if prog == "eval":
        return [argv] + _nested(" ".join(rest), depth + 1)
    if prog == "ssh":
        inner = _skip_opts(
            rest, {"-i", "-p", "-l", "-o", "-F", "-J", "-L", "-R", "-D", "-b", "-c", "-E",
                   "-e", "-m", "-O", "-Q", "-S", "-W", "-w", "-B"}
        )
        if len(inner) > 1:
            return [argv] + _nested(" ".join(inner[1:]), depth + 1)
        return [argv]
    if prog in ("docker", "podman") and rest[:1] == ["exec"]:
        inner = _skip_opts(rest[1:], {"-e", "--env", "-u", "--user", "-w", "--workdir",
                                      "--env-file", "--detach-keys"})
        if len(inner) > 1:
            return [argv, *unwrap(inner[1:], depth + 1)]
        return [argv]
    if prog in ("kubectl", "oc") and "exec" in rest and "--" in rest:
        inner = rest[rest.index("--") + 1 :]
        return [argv, *unwrap(inner, depth + 1)] if inner else [argv]
    if prog == "find":
        out = [argv]
        for idx, a in enumerate(rest):
            if a in ("-exec", "-execdir", "-ok", "-okdir"):
                end = idx + 1
                while end < len(rest) and rest[end] not in (";", "+", "\\;"):
                    end += 1
                if idx + 1 < end:
                    out.extend(unwrap(rest[idx + 1 : end], depth + 1))
        return out
    return [argv]


def _nested(cmd: str, depth: int) -> list[list[str]]:
    out: list[list[str]] = []
    for seg in split_segments(cmd, depth):
        if seg.error:
            out.append([f"{PARSE_ERROR}:{seg.error}"])
            continue
        out.extend(unwrap(seg.argv, depth))
        for op, target in seg.redirects:
            out.append(["__redirect__", op, target])
    return out


def parse_flags(args: list[str]) -> tuple[set[str], list[str]]:
    """Normalize flags: ``-rf`` -> {r, f}; ``--force`` -> {force}; returns positionals too."""
    flags: set[str] = set()
    pos: list[str] = []
    end_opts = False
    for a in args:
        if end_opts or a == "-" or not a.startswith("-"):
            pos.append(a)
            continue
        if a == "--":
            end_opts = True
            continue
        if a.startswith("--"):
            flags.add(a[2:].split("=", 1)[0].lower())
        else:
            flags.update(a[1:])
            flags.add(a)  # keep the raw form too, e.g. "-delete" for find
    return flags, pos


def exec_facts(argv: list[str], cwd: str | None = None) -> Facts:
    """Facts for a single (unwrapped) generic program invocation."""
    if argv and argv[0].startswith(f"{PARSE_ERROR}:"):
        return {PARSE_ERROR: argv[0].split(":", 1)[1]}
    prog_tok = argv[0]
    prog = program_name(prog_tok)
    args = argv[1:]
    flags, pos = parse_flags(args)
    facts: Facts = {
        "kind": "exec",
        "program": prog,
        "args": args,
        "flags": sorted(flags),
        "positionals": pos,
        "program_dynamic": ("$" in prog_tok or SUBST in prog_tok or "*" in prog_tok
                            or "?" in prog_tok),
        "recursive": bool({"r", "R", "recursive"} & flags),
        "force": bool({"f", "force"} & flags),
        "targets_root": any(p.rstrip("/") in {r.rstrip("/") for r in _ROOTISH} or p in _ROOTISH
                            for p in pos),
    }
    if prog in _INTERPRETERS:
        facts["interpreter"] = True
        facts["inline_code"] = any(
            a in _INTERPRETERS[prog] or (a.startswith("-") and not a.startswith("--")
                                         and any(o.lstrip("-") in a[1:] for o in _INTERPRETERS[prog]
                                                 if len(o) == 2))
            for a in args
        )
    if prog in _SHELLS:
        facts["interpreter"] = True
    if prog == "find":
        facts["find_delete"] = "-delete" in args
        facts["find_exec"] = any(a in ("-exec", "-execdir", "-ok", "-okdir") for a in args)
    if prog == "dd":
        outs = [a.split("=", 1)[1] for a in args if a.startswith("of=")]
        facts["dd_output"] = bool(outs)
        facts["device_target"] = any(o.startswith("/dev/") and o not in _SAFE_DEVICES for o in outs)
    if prog in ("mv", "cp", "ln", "install", "rsync"):
        facts["no_clobber"] = bool({"n", "no-clobber"} & flags) and "f" not in flags
        if cwd and len(pos) >= 2:
            target = os.path.join(cwd, pos[-1])
            facts["overwrites_existing"] = os.path.isfile(target)
    if prog in ("psql", "mysql", "mariadb", "sqlite3"):
        facts["sql_inline"] = sql_from_cli(prog, args) is not None
    return facts


def redirect_facts(op: str, target: str) -> Facts | None:
    if op in ("<", "<<", "<<<", "<&", ">&") or not target or target.isdigit() or target == "-":
        return None
    if target in _SAFE_DEVICES:
        return None
    return {
        "kind": "redirect",
        "op": op,
        "target": target,
        "device_target": target.startswith("/dev/"),
    }


def sql_from_cli(prog: str, args: list[str]) -> str | None:
    """Extract inline SQL from psql -c / mysql -e / sqlite3 db 'SQL'."""
    if prog == "psql":
        for i, a in enumerate(args):
            if a in ("-c", "--command") and i + 1 < len(args):
                return args[i + 1]
            if a.startswith("--command="):
                return a.split("=", 1)[1]
        return None
    if prog in ("mysql", "mariadb"):
        for i, a in enumerate(args):
            if a in ("-e", "--execute") and i + 1 < len(args):
                return args[i + 1]
            if a.startswith("--execute="):
                return a.split("=", 1)[1]
        return None
    if prog == "sqlite3":
        _, pos = parse_flags([a for a in args if a not in ("-cmd",)])
        return pos[1] if len(pos) >= 2 else None
    return None


def structured_facts(operation: str, payload: dict[str, Any]) -> Facts:
    """Facts for structured filesystem operations (e.g. MCP filesystem tools)."""
    path = payload.get("path") or payload.get("source") or ""
    return {
        "kind": "op",
        "operation": operation.lower(),
        "path": str(path),
        "recursive": bool(payload.get("recursive")),
        "targets_root": str(path).rstrip("/") in {r.rstrip("/") for r in _ROOTISH} or path == "/",
    }
