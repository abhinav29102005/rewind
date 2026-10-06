"""Plugin base definitions, interfaces, and version validation.

Three plugin kinds are supported:
- classifier: implements Classifier
- snapshot_backend: implements SnapshotBackend
- approval_channel: implements ApprovalChannel

Plugins run in-process and are fully trusted code.
"""

from __future__ import annotations

import concurrent.futures
import logging
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from ..contracts import (
    REWIND_API_VERSION,
    ActionRequest,
    Classification,
    Classifier,
    RiskClass,
)

logger = logging.getLogger(__name__)


class PluginKind(StrEnum):
    CLASSIFIER = "classifier"
    SNAPSHOT_BACKEND = "snapshot_backend"
    APPROVAL_CHANNEL = "approval_channel"


class PluginMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$")
    version: str
    rewind_api_version: str = REWIND_API_VERSION
    kind: PluginKind
    description: str = ""

    def validate_api_version(self) -> None:
        target_major = REWIND_API_VERSION.split(".")[0]
        plugin_major = self.rewind_api_version.split(".")[0]
        if target_major != plugin_major:
            raise ValueError(
                f"Plugin {self.name!r} requires Rewind API major version {plugin_major}, "
                f"but current system version is {target_major}"
            )


class PluginClassifierWrapper(Classifier):
    """Wraps a plugin classifier with additive strictness, timeouts, and fail-closed handling."""

    def __init__(self, classifier: Classifier, timeout_seconds: float = 2.0) -> None:
        self.underlying = classifier
        self.name = getattr(classifier, "name", type(classifier).__name__)
        self.timeout_seconds = timeout_seconds

    def supports(self, action: ActionRequest) -> bool:
        try:
            return self.underlying.supports(action)
        except Exception:
            return True

    def classify(self, action: ActionRequest) -> Classification:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.underlying.classify, action)
            try:
                res = future.result(timeout=self.timeout_seconds)
                return res
            except concurrent.futures.TimeoutError:
                logger.error("Classifier plugin %s timed out (>%ss); failing closed to irreversible", self.name, self.timeout_seconds)
                return Classification(
                    action_id=action.id,
                    risk=RiskClass.IRREVERSIBLE,
                    reasons=[f"Plugin {self.name} timed out after {self.timeout_seconds}s"],
                    rule_ids=[f"plugin:{self.name}:timeout"],
                    risk_score=1.0,
                )
            except Exception as e:
                logger.exception("Classifier plugin %s raised an exception; failing closed to irreversible", self.name)
                return Classification(
                    action_id=action.id,
                    risk=RiskClass.IRREVERSIBLE,
                    reasons=[f"Plugin {self.name} error: {e}"],
                    rule_ids=[f"plugin:{self.name}:error"],
                    risk_score=1.0,
                )
