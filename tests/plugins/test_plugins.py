"""Tests for plugin architecture, loading, timeout and fail-closed handling."""

from __future__ import annotations

import time
from datetime import datetime

import pytest

from rewind.contracts import ActionRequest, Classification, Classifier, RiskClass
from rewind.plugins import (
    PluginClassifierWrapper,
    PluginKind,
    PluginMeta,
    assert_classifier_conformance,
    clear_manual_plugins,
    load_enabled_plugins,
    register_manual_plugin,
)


class MockSafeClassifier(Classifier):
    name = "mock_safe"

    def supports(self, action: ActionRequest) -> bool:
        return True

    def classify(self, action: ActionRequest) -> Classification:
        return Classification(
            action_id=action.id,
            risk=RiskClass.SAFE,
            reasons=["always safe"],
            rule_ids=["mock:safe"],
        )


class MockHangingClassifier(Classifier):
    name = "mock_hang"

    def supports(self, action: ActionRequest) -> bool:
        return True

    def classify(self, action: ActionRequest) -> Classification:
        time.sleep(1.0)
        return Classification(
            action_id=action.id,
            risk=RiskClass.SAFE,
            reasons=["hang done"],
            rule_ids=["mock:hang"],
        )


class MockErrorClassifier(Classifier):
    name = "mock_error"

    def supports(self, action: ActionRequest) -> bool:
        return True

    def classify(self, action: ActionRequest) -> Classification:
        raise RuntimeError("Bug in plugin code")


@pytest.fixture(autouse=True)
def cleanup_plugins():
    clear_manual_plugins()
    yield
    clear_manual_plugins()


def test_plugin_version_validation():
    # Compatible version
    meta_ok = PluginMeta(
        name="test_ok",
        version="1.0.0",
        rewind_api_version="1.0",
        kind=PluginKind.CLASSIFIER,
    )
    meta_ok.validate_api_version()

    # Incompatible major version
    meta_bad = PluginMeta(
        name="test_bad",
        version="1.0.0",
        rewind_api_version="2.0",
        kind=PluginKind.CLASSIFIER,
    )
    with pytest.raises(ValueError, match="requires Rewind API major version 2"):
        meta_bad.validate_api_version()


def test_explicit_enable_only():
    meta = PluginMeta(
        name="my_plugin",
        version="1.0.0",
        kind=PluginKind.CLASSIFIER,
    )
    register_manual_plugin(meta, MockSafeClassifier)

    # Empty enabled list loads nothing
    loaded = load_enabled_plugins([])
    assert "my_plugin" not in loaded

    # Explicitly enabled loads successfully
    loaded = load_enabled_plugins(["my_plugin"])
    assert "my_plugin" in loaded


def test_uninstalled_plugin_raises():
    with pytest.raises(ValueError, match="not installed or found"):
        load_enabled_plugins(["nonexistent_plugin"])


def test_plugin_conformance_kit():
    classifier = MockSafeClassifier()
    assert_classifier_conformance(classifier)


def test_plugin_timeout_fails_closed():
    hanging = MockHangingClassifier()
    wrapper = PluginClassifierWrapper(hanging, timeout_seconds=0.1)

    act = ActionRequest(
        id="act_hang",
        agent_id="test",
        tool="sql",
        operation="exec",
        payload={},
        created_at=datetime.now(),
    )
    res = wrapper.classify(act)
    # Must fail closed to IRREVERSIBLE
    assert res.risk == RiskClass.IRREVERSIBLE
    assert "timed out" in " ".join(res.reasons).lower()


def test_plugin_exception_fails_closed():
    buggy = MockErrorClassifier()
    wrapper = PluginClassifierWrapper(buggy, timeout_seconds=1.0)

    act = ActionRequest(
        id="act_err",
        agent_id="test",
        tool="sql",
        operation="exec",
        payload={},
        created_at=datetime.now(),
    )
    res = wrapper.classify(act)
    # Must fail closed to IRREVERSIBLE
    assert res.risk == RiskClass.IRREVERSIBLE
    assert "error" in " ".join(res.reasons).lower()
