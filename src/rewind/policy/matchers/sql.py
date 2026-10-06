"""SQL fact extraction using sqlglot. Never regex SQL.

Each top-level statement becomes a unit. Writes nested anywhere inside a
statement (data-modifying CTEs, ``EXPLAIN ANALYZE <write>``) become extra
units, so the strictest one wins. Any parse failure yields a parse-error unit,
which the engine always classifies ``irreversible``.
"""

from __future__ import annotations

import logging
from typing import Any

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from . import PARSE_ERROR, Facts

logging.getLogger("sqlglot").setLevel(logging.CRITICAL)

FACT_KEYS = {
    "statement_type", "where", "object", "action", "functions", "into", "parsed",
    "nested_in", "returning", "limit", PARSE_ERROR,
}

MAX_SQL_CHARS = 200_000

_DIALECTS = {"postgres", "postgresql", "mysql", "sqlite", "tsql", "bigquery", "snowflake"}

_STATEMENT_TYPES: list[tuple[type[exp.Expression], str]] = [
    (exp.Select, "SELECT"), (exp.Union, "SELECT"), (exp.Insert, "INSERT"),
    (exp.Update, "UPDATE"), (exp.Delete, "DELETE"), (exp.TruncateTable, "TRUNCATE"),
    (exp.Drop, "DROP"), (exp.Alter, "ALTER"), (exp.Create, "CREATE"),
    (exp.Grant, "GRANT"), (exp.Merge, "MERGE"), (exp.Copy, "COPY"), (exp.Set, "SET"),
    (exp.Transaction, "BEGIN"), (exp.Commit, "COMMIT"), (exp.Rollback, "ROLLBACK"),
    (exp.Describe, "DESCRIBE"), (exp.Use, "USE"), (exp.Pragma, "PRAGMA"),
]
_REVOKE = getattr(exp, "Revoke", None)
if _REVOKE is not None:
    _STATEMENT_TYPES.append((_REVOKE, "REVOKE"))

_WRITE_NODES: tuple[type[exp.Expression], ...] = (
    exp.Insert, exp.Update, exp.Delete, exp.TruncateTable, exp.Drop, exp.Alter,
    exp.Merge, exp.Create,
)


def _dialect(d: str | None) -> str:
    d = (d or "postgres").lower()
    if d == "postgresql":
        d = "postgres"
    if d not in _DIALECTS:
        raise ValueError(f"unsupported SQL dialect {d!r}")
    return d


def _statement_type(node: exp.Expression) -> str:
    for cls, name in _STATEMENT_TYPES:
        if isinstance(node, cls):
            return name
    return type(node).__name__.upper()


def _alter_action(node: exp.Alter) -> str | None:
    actions = node.args.get("actions") or []
    names = []
    for a in actions:
        if isinstance(a, exp.Drop):
            names.append(f"DROP_{(a.args.get('kind') or 'OBJECT').upper()}")
        elif isinstance(a, exp.ColumnDef):
            names.append("ADD_COLUMN")
        elif type(a).__name__ == "AlterRename":
            names.append("RENAME")
        elif type(a).__name__ == "RenameColumn":
            names.append("RENAME_COLUMN")
        elif isinstance(a, exp.AlterColumn):
            names.append("ALTER_COLUMN")
        else:
            names.append(type(a).__name__.upper())
    return names[0] if len(names) == 1 else ("MULTI:" + ",".join(names) if names else None)


def _functions(node: exp.Expression) -> list[str]:
    out = []
    for f in node.find_all(exp.Func):
        name = f.name if isinstance(f, exp.Anonymous) else (f.sql_name() or "")
        if name:
            out.append(name.lower())
    return out


def _facts_for(node: exp.Expression, nested_in: str | None = None) -> Facts:
    st = _statement_type(node)
    facts: Facts = {"statement_type": st, "parsed": True}
    if nested_in:
        facts["nested_in"] = nested_in
    if isinstance(node, exp.Update | exp.Delete):
        facts["where"] = node.args.get("where") is not None
        facts["returning"] = node.args.get("returning") is not None
        facts["limit"] = node.args.get("limit") is not None
    if isinstance(node, exp.Drop | exp.Create):
        facts["object"] = str(node.args.get("kind") or "").upper() or None
    if isinstance(node, exp.Alter):
        facts["object"] = str(node.args.get("kind") or "TABLE").upper()
        facts["action"] = _alter_action(node)
    if isinstance(node, exp.Select):
        facts["into"] = node.args.get("into") is not None
    if isinstance(node, exp.Copy):
        # COPY ... FROM loads data (write); COPY ... TO exports (read).
        facts["action"] = "FROM" if node.args.get("kind") else "TO"
    facts["functions"] = _functions(node)
    return facts


def _command_units(node: exp.Command, dialect: str, depth: int) -> list[Facts]:
    """Statements sqlglot could not parse fully. Treated as unparsed."""
    keyword = str(node.this or "").upper().strip()
    rest = node.expression
    body = rest.this if isinstance(rest, exp.Literal) else (str(rest) if rest is not None else "")
    body = str(body).strip()
    words = body.split()
    facts: Facts = {"statement_type": keyword or "UNKNOWN", "parsed": False}
    if keyword in ("DROP", "ALTER", "CREATE") and words:
        facts["object"] = words[0].upper()
    if keyword == "EXPLAIN":
        opts: set[str] = set()
        i = 0
        while i < len(words):
            w = words[i].upper()
            if w.startswith("("):
                # Option list form: EXPLAIN (ANALYZE, FORMAT JSON) <stmt>
                j = i
                chunk = []
                while j < len(words):
                    chunk.append(words[j])
                    if words[j].endswith(")"):
                        break
                    j += 1
                for part in " ".join(chunk).strip("()").split(","):
                    tokens = part.strip().split()
                    if tokens and (len(tokens) == 1 or tokens[1].upper() not in ("FALSE", "OFF", "0")):
                        opts.add(tokens[0].upper())
                i = j + 1
                continue
            if w in ("ANALYZE", "ANALYSE", "VERBOSE", "COSTS", "BUFFERS", "TIMING", "SUMMARY"):
                opts.add("ANALYZE" if w == "ANALYSE" else w)
                i += 1
                continue
            break
        inner = " ".join(words[i:])
        facts["statement_type"] = "EXPLAIN"
        facts["parsed"] = True
        if "ANALYZE" in opts:
            facts["action"] = "ANALYZE"
            # EXPLAIN ANALYZE executes the statement: classify it too.
            return [facts, *(
                {**u, "nested_in": "EXPLAIN_ANALYZE"} for u in extract_sql(inner, dialect, depth + 1)
            )]
        return [facts]
    return [facts]


def extract_sql(sql: Any, dialect: str | None = None, depth: int = 0) -> list[Facts]:
    """Return one or more fact units for a SQL string. Never raises."""
    if not isinstance(sql, str) or not sql.strip():
        return [{PARSE_ERROR: "empty or non-string statement"}]
    if len(sql) > MAX_SQL_CHARS or depth > 4:
        return [{PARSE_ERROR: "statement too large or too deeply nested"}]
    try:
        d = _dialect(dialect)
        statements = sqlglot.parse(sql, dialect=d)
    except (SqlglotError, ValueError, RecursionError, TypeError, KeyError, IndexError,
            AttributeError) as e:
        return [{PARSE_ERROR: f"could not parse statement ({type(e).__name__})"}]
    except Exception as e:  # noqa: BLE001 - fail closed on any parser bug
        return [{PARSE_ERROR: f"could not parse statement ({type(e).__name__})"}]

    units: list[Facts] = []
    for stmt in statements:
        if stmt is None or not isinstance(stmt, exp.Expression):
            continue  # empty statement between semicolons
        try:
            if isinstance(stmt, exp.Command):
                units.extend(_command_units(stmt, d, depth))
                continue
            units.append(_facts_for(stmt))
            top_type = _statement_type(stmt)
            for node in stmt.find_all(*_WRITE_NODES):
                if node is stmt:
                    continue
                units.append(_facts_for(node, nested_in=top_type))
        except Exception as e:  # noqa: BLE001
            units.append({PARSE_ERROR: f"could not analyse statement ({type(e).__name__})"})
    if not units:
        return [{PARSE_ERROR: "no statements found"}]
    return units


def extract(payload: dict[str, Any], dialect: str | None) -> list[Facts]:
    sql = payload.get("statement", payload.get("sql", payload.get("query")))
    d = payload.get("dialect") or dialect
    return extract_sql(sql, d)
