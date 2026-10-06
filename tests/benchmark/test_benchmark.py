"""Tests for benchmark runner and scenario schema validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from benchmark.models import ScenarioParseError, load_scenario
from benchmark.runner import BenchmarkRunner

SCENARIOS_DIR = Path(__file__).resolve().parents[2] / "benchmark" / "scenarios"


def test_all_shipped_scenarios_are_valid():
    scenario_files = list(SCENARIOS_DIR.glob("*.yaml")) + list(SCENARIOS_DIR.glob("*.yml"))
    assert len(scenario_files) >= 10, f"Expected at least 10 scenarios, found {len(scenario_files)}"

    for sf in scenario_files:
        try:
            sc = load_scenario(sf)
            assert sc.id, f"Missing id in {sf}"
            assert sc.name, f"Missing name in {sf}"
            assert sc.category, f"Missing category in {sf}"
            assert len(sc.steps) > 0, f"Scenario {sf} has no steps"
        except Exception as e:
            pytest.fail(f"Scenario {sf.name} failed schema validation: {e}")


def test_invalid_scenario_schema(tmp_path: Path):
    bad_file = tmp_path / "bad_scenario.yaml"
    bad_file.write_text("name: Missing ID\ncategory: invalid_cat\nsteps: []\n", encoding="utf-8")

    with pytest.raises(ScenarioParseError):
        load_scenario(bad_file)


def test_runner_executes_scenarios(tmp_path: Path):
    runner = BenchmarkRunner()
    target_scenario = SCENARIOS_DIR / "unscoped-delete.yaml"
    res = runner.run_scenario(target_scenario, target="all")

    assert res["scenario"] == "unscoped-delete"
    targets = res["targets"]
    assert "none" in targets
    assert "cooperative" in targets
    assert "rewind" in targets

    # Under none: damage occurs
    assert targets["none"]["data_loss_rows"] > 0
    # Under rewind: destructive prevented
    assert targets["rewind"]["destructive_prevented"] is True
    assert targets["rewind"]["data_loss_rows"] == 0


def test_report_generation(tmp_path: Path):
    runner = BenchmarkRunner()
    results = [
        runner.run_scenario(SCENARIOS_DIR / "tok-discovery.yaml", target="all"),
        runner.run_scenario(SCENARIOS_DIR / "safe-workload.yaml", target="all"),
    ]

    json_path, md_path = runner.generate_report(results, tmp_path)
    assert json_path.exists()
    assert md_path.exists()

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["total_scenarios"] == 2
    md_content = md_path.read_text(encoding="utf-8")
    assert "Rewind Benchmark v1 Results" in md_content
    assert "tok-discovery" in md_content
    assert "safe-workload" in md_content
