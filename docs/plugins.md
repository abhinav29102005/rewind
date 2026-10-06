# Plugin Authoring Guide

Rewind features an extensible plugin architecture allowing developers to provide custom classifiers, snapshot backends, and approval channels.

---

## 1. Plugin Interface Contract

All plugins must declare metadata with `rewind_api_version = "1.0"`:

```python
from rewind.contracts import ActionRequest, Classification, RiskClass
from rewind.plugins.base import PluginKind, PluginMeta

class CustomClassifier:
    plugin_meta = PluginMeta(
        name="company_classifier",
        version="1.0.0",
        kind=PluginKind.CLASSIFIER,
        rewind_api_version="1.0",
        description="Company internal policy classifier",
    )

    def classify(self, action: ActionRequest) -> Classification:
        if action.tool == "company_api" and action.operation == "wipe_data":
            return Classification(
                risk=RiskClass.IRREVERSIBLE,
                rule_id="company_wipe",
                pack="company_classifier",
                reason="Wiping company data is irreversible.",
            )
        return Classification(
            risk=RiskClass.SAFE,
            rule_id="company_default",
            pack="company_classifier",
            reason="Standard operation.",
        )
```

---

## 2. Registering Plugins

Plugins can be registered in two ways:

### Entry Points (Distribution via PyPI/wheel)
Add your plugin to `pyproject.toml` under the `rewind.plugins` entry point group:

```toml
[project.entry-points."rewind.plugins"]
company_classifier = "my_package.plugins:CustomClassifier"
```

### In-Process Manual Registration (Testing)
```python
from rewind.plugins.loader import register_manual_plugin

register_manual_plugin(CustomClassifier.plugin_meta, CustomClassifier)
```

### Enabling in `rewind.yaml`
By default, installed plugins are not loaded unless explicitly listed in `plugins.enabled` in `rewind.yaml`:

```yaml
plugins:
  enabled:
    - company_classifier
  classifier_timeout_seconds: 2.0
```

---

## 3. Conformance Test Suite

Rewind provides an automated conformance test kit (`rewind.plugins.testing`) to verify your plugin meets interface requirements, handles timeouts, and fails closed under errors:

```python
import pytest
from rewind.plugins.testing import PluginConformanceSuite
from my_package.plugins import CustomClassifier

def test_custom_classifier_conformance():
    suite = PluginConformanceSuite(CustomClassifier)
    suite.run_all()
```

The conformance suite verifies:
1. Valid metadata and matching `rewind_api_version`.
2. Clean `classify()` execution on standard `ActionRequest` inputs.
3. Fail-closed error handling when exceptions are thrown.
4. Enforcement of the execution timeout wrapper.

---

## 4. CLI Plugin Commands

Inspect discovered and enabled plugins using the Rewind CLI:

```bash
rewind plugin list
```
