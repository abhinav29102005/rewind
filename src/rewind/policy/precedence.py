"""Merging rule results across packs and applying user overrides.

1. All packs for a tool are evaluated; the strictest matching rule wins.
2. Overrides tighten freely; a relaxing override needs ``override_reason``
   and is reported so the caller can audit it at startup.
3. No rule matched: the strictest ``default_risk`` of the packs evaluated.
   No pack covers the tool: the global default, ``irreversible``.
4. Every fired rule id is returned.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..contracts import RiskClass, risk_rank, stricter
from .matchers import PARSE_ERROR, Facts, rule_matches
from .pack import PolicyError, PolicyPack, Rule

if TYPE_CHECKING:
    from ..config.models import RuleOverride

GLOBAL_DEFAULT = RiskClass.IRREVERSIBLE


@dataclass
class Fired:
    rule_id: str
    risk: RiskClass
    reason: str


@dataclass
class Verdict:
    risk: RiskClass = RiskClass.SAFE
    fired: list[Fired] = field(default_factory=list)

    def add(self, f: Fired) -> None:
        self.risk = stricter(self.risk, f.risk)
        self.fired.append(f)

    def merge(self, other: Verdict) -> None:
        for f in other.fired:
            self.add(f)


@dataclass(frozen=True)
class ResolvedOverrides:
    risk_by_rule: dict[str, RiskClass]
    relaxed: list[tuple[str, RiskClass, RiskClass, str]]  # (rule_id, from, to, reason)


def resolve_overrides(packs: list[PolicyPack], overrides: list[RuleOverride]) -> ResolvedOverrides:
    rules = {r.id: r for p in packs for r in p.rules}
    out: dict[str, RiskClass] = {}
    relaxed: list[tuple[str, RiskClass, RiskClass, str]] = []
    for o in overrides:
        rule = rules.get(o.rule_id)
        if rule is None:
            # DECISION: an override for an unknown rule is an error; a typo would
            # otherwise silently drop an intended tightening.
            raise PolicyError(f"Override references unknown rule id {o.rule_id!r}")
        if risk_rank(o.risk) < risk_rank(rule.risk):
            if not o.override_reason:
                raise PolicyError(
                    f"Override for {o.rule_id} relaxes {rule.risk.value} -> {o.risk.value} "
                    "and requires override_reason"
                )
            relaxed.append((o.rule_id, rule.risk, o.risk, o.override_reason))
        out[o.rule_id] = o.risk
    return ResolvedOverrides(out, relaxed)


def _effective(rule: Rule, ov: ResolvedOverrides) -> RiskClass:
    return ov.risk_by_rule.get(rule.id, rule.risk)


def evaluate_units(
    tool: str, units: list[Facts], packs: list[PolicyPack], ov: ResolvedOverrides
) -> Verdict:
    v = Verdict()
    for unit in units:
        if PARSE_ERROR in unit:
            v.add(Fired(f"{tool}:parse-error", RiskClass.IRREVERSIBLE,
                        str(unit[PARSE_ERROR]) or "could not parse statement"))
            continue
        if not packs:
            v.add(Fired(f"{tool}:no-pack", GLOBAL_DEFAULT,
                        f"No policy pack covers tool {tool!r}; default is irreversible"))
            continue
        matched = False
        for pack in packs:
            for rule in pack.rules:
                if rule_matches(rule.match, unit):
                    matched = True
                    v.add(Fired(rule.id, _effective(rule, ov), rule.reason))
        if not matched:
            strictest = max(packs, key=lambda p: risk_rank(p.default_risk))
            v.add(Fired(f"{strictest.pack}:default", strictest.default_risk,
                        f"No rule in pack {strictest.pack!r} matched; pack default applies"))
    return v
