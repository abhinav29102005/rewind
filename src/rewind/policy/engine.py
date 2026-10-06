"""Policy classifier implementation of the Classifier protocol.

Classifies incoming ActionRequests using loaded PolicyPacks, tool-specific
matchers, and precedence rules.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..contracts import ActionRequest, Classification, Classifier, RiskClass
from .matchers import PARSE_ERROR
from .matchers import aws as aws_m
from .matchers import git as git_m
from .matchers import k8s_docker as kd_m
from .matchers import shell_fs as fs_m
from .matchers import sql as sql_m
from .precedence import Fired, Verdict, evaluate_units, resolve_overrides

if TYPE_CHECKING:
    from ..config.models import RewindConfig, RuleOverride
    from .pack import PolicyPack

logger = logging.getLogger(__name__)


class PolicyClassifier(Classifier):
    """Enforces policy rules from PolicyPacks across all tools."""

    name: str = "policy_classifier"

    def __init__(
        self,
        packs: list[PolicyPack],
        overrides: list[RuleOverride] | None = None,
        escalate_reversible: bool = False,
    ) -> None:
        self.packs = list(packs)
        self.packs_by_tool: dict[str, list[PolicyPack]] = {}
        for p in self.packs:
            self.packs_by_tool.setdefault(p.tool, []).append(p)
        self.overrides = resolve_overrides(self.packs, overrides or [])
        self.escalate_reversible = escalate_reversible

    @classmethod
    def from_config(cls, cfg: RewindConfig, packs: list[PolicyPack]) -> PolicyClassifier:
        return cls(
            packs=packs,
            overrides=list(cfg.policies.overrides),
            escalate_reversible=cfg.escalate_reversible,
        )

    def supports(self, action: ActionRequest) -> bool:
        return True

    def classify(self, action: ActionRequest) -> Classification:
        tool = action.tool.lower()
        verdict = Verdict()

        try:
            if tool == "sql":
                self._classify_sql(action, verdict)
            elif tool in ("fs", "filesystem", "shell", "sh", "bash"):
                self._classify_fs_or_shell(action, verdict)
            elif tool == "git":
                self._classify_git(action, verdict)
            elif tool in ("aws_s3", "s3"):
                self._classify_aws_s3(action, verdict)
            elif tool in ("aws_iam", "iam"):
                self._classify_aws_iam(action, verdict)
            elif tool == "docker":
                self._classify_docker(action, verdict)
            elif tool in ("k8s", "kubernetes"):
                self._classify_k8s(action, verdict)
            else:
                # Unknown tool: evaluate against empty packs to trigger fail-closed default
                units = [{PARSE_ERROR: f"Unsupported or unknown tool {action.tool!r}"}]
                v = evaluate_units(tool, units, self.packs_by_tool.get(tool, []), self.overrides)
                verdict.merge(v)
        except Exception as e:
            logger.exception("Failed during classification of action %s", action.id)
            verdict.add(
                Fired(
                    rule_id=f"{tool}:classifier-error",
                    risk=RiskClass.IRREVERSIBLE,
                    reason=f"Classification error: {e}",
                )
            )

        final_risk = verdict.risk
        reasons = [f.reason for f in verdict.fired]
        rule_ids = [f.rule_id for f in verdict.fired]

        if self.escalate_reversible and final_risk == RiskClass.REVERSIBLE:
            final_risk = RiskClass.IRREVERSIBLE
            reasons.append("escalate_reversible: elevated reversible action to irreversible")
            rule_ids.append("system:escalate_reversible")

        score = 0.0 if final_risk == RiskClass.SAFE else (0.5 if final_risk == RiskClass.REVERSIBLE else 1.0)

        return Classification(
            action_id=action.id,
            risk=final_risk,
            reasons=reasons,
            rule_ids=rule_ids,
            risk_score=score,
        )

    def _classify_sql(self, action: ActionRequest, verdict: Verdict) -> None:
        packs = self.packs_by_tool.get("sql", [])
        dialect = packs[0].dialect if packs else "postgres"
        units = sql_m.extract(action.payload, dialect=dialect)
        v = evaluate_units("sql", units, packs, self.overrides)
        verdict.merge(v)

    def _classify_fs_or_shell(self, action: ActionRequest, verdict: Verdict) -> None:
        payload = action.payload
        cmd = payload.get("command") or payload.get("cmd")

        if isinstance(cmd, str):
            # Shell command execution
            fs_packs = self.packs_by_tool.get("fs", [])
            segments = fs_m.split_segments(cmd)
            for seg in segments:
                if seg.error:
                    verdict.merge(
                        evaluate_units("fs", [{PARSE_ERROR: seg.error}], fs_packs, self.overrides)
                    )
                    continue

                unwrapped_list = fs_m.unwrap(seg.argv)
                for argv in unwrapped_list:
                    if not argv:
                        continue
                    if argv[0].startswith(f"{PARSE_ERROR}:"):
                        err_msg = argv[0].split(":", 1)[1]
                        verdict.merge(
                            evaluate_units("fs", [{PARSE_ERROR: err_msg}], fs_packs, self.overrides)
                        )
                        continue

                    prog = fs_m.program_name(argv[0])
                    # Route to sub-tool matchers if applicable
                    if prog == "git" and "git" in self.packs_by_tool:
                        git_packs = self.packs_by_tool.get("git", [])
                        params = git_packs[0].params if git_packs else {}
                        git_facts = git_m.extract_argv(argv[1:], params)
                        verdict.merge(evaluate_units("git", [git_facts], git_packs, self.overrides))
                        continue
                    elif prog == "docker" and "docker" in self.packs_by_tool:
                        docker_packs = self.packs_by_tool.get("docker", [])
                        docker_facts = kd_m.docker_from_argv(prog, argv[1:])
                        verdict.merge(evaluate_units("docker", [docker_facts], docker_packs, self.overrides))
                        continue
                    elif prog in ("kubectl", "oc") and "k8s" in self.packs_by_tool:
                        k8s_packs = self.packs_by_tool.get("k8s", [])
                        params = k8s_packs[0].params if k8s_packs else {}
                        k8s_facts = kd_m.k8s_from_argv(argv[1:], params)
                        verdict.merge(evaluate_units("k8s", [k8s_facts], k8s_packs, self.overrides))
                        continue
                    elif prog == "aws":
                        aws_units = aws_m.extract_cli(argv[1:])
                        for u in aws_units:
                            svc = u.get("service")
                            target_tool = f"aws_{svc}" if svc in ("s3", "iam") else "aws_s3"
                            packs = self.packs_by_tool.get(target_tool, [])
                            verdict.merge(evaluate_units(target_tool, [u], packs, self.overrides))
                        continue
                    elif prog in ("psql", "mysql", "mariadb", "sqlite3") and "sql" in self.packs_by_tool:
                        inline_sql = fs_m.sql_from_cli(prog, argv[1:])
                        if inline_sql:
                            sql_packs = self.packs_by_tool.get("sql", [])
                            dialect = "sqlite" if prog == "sqlite3" else ("mysql" if "mysql" in prog else "postgres")
                            sql_units = sql_m.extract_sql(inline_sql, dialect=dialect)
                            verdict.merge(evaluate_units("sql", sql_units, sql_packs, self.overrides))
                            continue

                    # Standard filesystem exec
                    facts = fs_m.exec_facts(argv, cwd=payload.get("cwd"))
                    verdict.merge(evaluate_units("fs", [facts], fs_packs, self.overrides))

                for op, target in seg.redirects:
                    red_facts = fs_m.redirect_facts(op, target)
                    if red_facts:
                        verdict.merge(evaluate_units("fs", [red_facts], fs_packs, self.overrides))
        else:
            # Structured filesystem operation
            fs_packs = self.packs_by_tool.get("fs", [])
            facts = fs_m.structured_facts(action.operation, payload)
            verdict.merge(evaluate_units("fs", [facts], fs_packs, self.overrides))

    def _classify_git(self, action: ActionRequest, verdict: Verdict) -> None:
        packs = self.packs_by_tool.get("git", [])
        params = packs[0].params if packs else {}
        facts = git_m.extract(action.operation, action.payload, params)
        verdict.merge(evaluate_units("git", [facts], packs, self.overrides))

    def _classify_aws_s3(self, action: ActionRequest, verdict: Verdict) -> None:
        packs = self.packs_by_tool.get("aws_s3", [])
        units = aws_m.extract_structured("s3", action.operation, action.payload)
        verdict.merge(evaluate_units("aws_s3", units, packs, self.overrides))

    def _classify_aws_iam(self, action: ActionRequest, verdict: Verdict) -> None:
        packs = self.packs_by_tool.get("aws_iam", [])
        units = aws_m.extract_structured("iam", action.operation, action.payload)
        verdict.merge(evaluate_units("aws_iam", units, packs, self.overrides))

    def _classify_docker(self, action: ActionRequest, verdict: Verdict) -> None:
        packs = self.packs_by_tool.get("docker", [])
        args = action.payload.get("args") or [action.operation]
        facts = kd_m.docker_from_argv("docker", args)
        verdict.merge(evaluate_units("docker", [facts], packs, self.overrides))

    def _classify_k8s(self, action: ActionRequest, verdict: Verdict) -> None:
        packs = self.packs_by_tool.get("k8s", [])
        params = packs[0].params if packs else {}
        args = action.payload.get("args") or [action.operation]
        facts = kd_m.k8s_from_argv(args, params)
        verdict.merge(evaluate_units("k8s", [facts], packs, self.overrides))
