"""Policy pack model and YAML loader. Unreadable or invalid packs fail closed."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..contracts import RiskClass
from .matchers import PARSE_ERROR, split_key
from .matchers import aws as aws_m
from .matchers import git as git_m
from .matchers import k8s_docker as kd_m
from .matchers import shell_fs as fs_m
from .matchers import sql as sql_m

if TYPE_CHECKING:
    from pathlib import Path


class PolicyError(Exception):
    """A policy pack is missing, unreadable, invalid, or an override is unsafe."""


#: Fact keys each tool's rules may reference (typo protection).
TOOL_FACT_KEYS: dict[str, set[str]] = {
    "sql": sql_m.FACT_KEYS,
    "fs": fs_m.FACT_KEYS,
    "git": git_m.FACT_KEYS,
    "aws_s3": aws_m.FACT_KEYS,
    "aws_iam": aws_m.FACT_KEYS,
    "docker": kd_m.DOCKER_FACT_KEYS,
    "k8s": kd_m.K8S_FACT_KEYS,
}


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$", max_length=128)
    match: dict[str, Any]
    risk: RiskClass
    reason: str = Field(min_length=3, max_length=300)


class PolicyPack(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pack: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    version: Literal[1]
    tool: Literal["sql", "fs", "git", "aws_s3", "aws_iam", "docker", "k8s"]
    dialect: str | None = None
    description: str = ""
    default_risk: RiskClass = RiskClass.IRREVERSIBLE
    params: dict[str, Any] = Field(default_factory=dict)
    rules: list[Rule]
    source: str | None = None  # file the pack was loaded from (set by the loader)

    @model_validator(mode="after")
    def _check(self) -> PolicyPack:
        ids = [r.id for r in self.rules]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"duplicate rule ids: {dupes}")
        allowed = TOOL_FACT_KEYS[self.tool]
        for r in self.rules:
            if not r.match:
                raise ValueError(f"rule {r.id}: match must not be empty")
            for key in r.match:
                base, _ = split_key(key)
                if base not in allowed or base == PARSE_ERROR:
                    raise ValueError(
                        f"rule {r.id}: unknown match key {key!r} for tool {self.tool!r} "
                        f"(allowed: {sorted(allowed - {PARSE_ERROR})})"
                    )
        if self.tool == "sql" and not self.dialect:
            raise ValueError("sql packs must declare a dialect")
        return self


def load_pack_file(path: Path) -> PolicyPack:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise PolicyError(f"Cannot read policy pack {path}: {e.strerror or e}") from e
    except yaml.YAMLError as e:
        raise PolicyError(f"Policy pack {path} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise PolicyError(f"Policy pack {path} must be a mapping")
    data["source"] = str(path)
    try:
        return PolicyPack.model_validate(data)
    except ValidationError as e:
        msgs = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '<root>'}: {err['msg']}" for err in e.errors()
        )
        raise PolicyError(f"Invalid policy pack {path}: {msgs}") from e


def load_packs(names: list[str], search_paths: list[Path]) -> list[PolicyPack]:
    """Load the named packs. Later search paths override earlier ones by pack name.

    Every requested pack must be found and valid, otherwise PolicyError.
    """
    found: dict[str, PolicyPack] = {}
    for d in search_paths:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.y*ml")):
            if f.suffix not in (".yaml", ".yml"):
                continue
            pack = load_pack_file(f)
            found[pack.pack] = pack
    missing = [n for n in names if n not in found]
    if missing:
        raise PolicyError(
            f"Policy packs not found: {missing}. Searched: {[str(p) for p in search_paths]}"
        )
    return [found[n] for n in names]
