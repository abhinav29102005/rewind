"""Scenario models and schema validation for Rewind Benchmark v1."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ScenarioCategory(StrEnum):
    INCIDENT_REPLAY = "incident_replay"
    ADVERSARIAL = "adversarial"
    SAFE_CONTROL = "safe_control"
    INTEGRITY = "integrity"


class ScenarioStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str  # "fs" | "sql" | "git" | "aws_s3" | "docker" | ...
    op: str | None = None
    path: str | None = None
    statement: str | None = None
    command: str | None = None
    use: str | None = None
    description: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)


class VerifyCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str  # "table_checksum_equal" | "table_exists" | "bypass_attempted_and_failed" | "file_intact" | ...
    table: str | None = None
    path: str | None = None
    expected_rows: int | None = None


class VerifyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    independent: bool = True
    checks: list[VerifyCheck] = Field(default_factory=list)


class TargetExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destructive_prevented: bool
    data_loss_rows: int | None = None
    false_blocks: int | None = None


class ScenarioSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str | None = None
    files: dict[str, str] = Field(default_factory=dict)


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=3)
    inspired_by: str | None = None
    category: ScenarioCategory
    seed: ScenarioSeed = Field(default_factory=ScenarioSeed)
    steps: list[ScenarioStep]
    verify: VerifyConfig = Field(default_factory=VerifyConfig)
    expect: dict[str, TargetExpectation] = Field(default_factory=dict)


class ScenarioParseError(Exception):
    """Raised when a scenario YAML fails schema validation."""


def load_scenario(path: Path | str) -> Scenario:
    p = Path(path)
    if not p.is_file():
        raise ScenarioParseError(f"Scenario file not found: {p}")
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        raise ScenarioParseError(f"Invalid YAML syntax in {p}: {e}") from e
    if not isinstance(data, dict):
        raise ScenarioParseError(f"Scenario in {p} must be a dictionary at top level")

    try:
        return Scenario.model_validate(data)
    except ValidationError as e:
        msgs = [f"  - {'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in e.errors()]
        raise ScenarioParseError(f"Scenario validation error in {p.name}:\n" + "\n".join(msgs)) from e
