"""Knowledge base: loads data/kb.json and checks that it is consistent.

Facts are plain strings:
    "cough"                  a symptom the user reported present
    "not:cough"              a symptom the user said is absent
    "syndrome:respiratory"   an intermediate fact derived by a rule
    "disease:influenza"      a hypothesis derived by a rule

A rule fires when ALL of `if_all` hold and, if `if_any` is given, at least one
of those holds too.  Its conclusion gets certainty `cf * premise certainty`.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

DEFAULT_PATH = Path(__file__).parent / "data" / "kb.json"


@dataclass(frozen=True)
class Rule:
    id: str
    if_all: Tuple[str, ...]
    if_any: Tuple[str, ...]
    then: str
    cf: float
    why: str

    @property
    def conditions(self) -> Tuple[str, ...]:
        return self.if_all + self.if_any


class KnowledgeBase:
    def __init__(self, path: Path | str = DEFAULT_PATH) -> None:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        self.meta: Dict = raw.get("meta", {})
        self.symptoms: Dict[str, Dict] = raw["symptoms"]
        self.diseases: Dict[str, Dict] = raw["diseases"]
        self.rules: List[Rule] = [
            Rule(
                id=r["id"],
                if_all=tuple(r.get("if", ())),
                if_any=tuple(r.get("if_any", ())),
                then=r["then"],
                cf=float(r["cf"]),
                why=r.get("why", ""),
            )
            for r in raw["rules"]
        ]
        self._by_goal: Dict[str, List[Rule]] = {}
        for rule in self.rules:
            self._by_goal.setdefault(rule.then, []).append(rule)
        self.validate()

    # ------------------------------------------------------------------ lookup
    def rules_for(self, goal: str) -> List[Rule]:
        return self._by_goal.get(goal, [])

    def is_symptom(self, fact: str) -> bool:
        return fact in self.symptoms

    def is_negated_symptom(self, fact: str) -> bool:
        return fact.startswith("not:") and fact[4:] in self.symptoms

    def label(self, fact: str) -> str:
        if fact in self.symptoms:
            return self.symptoms[fact]["label"]
        if fact.startswith("not:") and fact[4:] in self.symptoms:
            return "no " + self.symptoms[fact[4:]]["label"].lower()
        if fact.startswith("disease:"):
            return self.diseases[fact[8:]]["label"]
        return fact.split(":", 1)[-1].replace("_", " ")

    def symptom_groups(self) -> Dict[str, List[str]]:
        groups: Dict[str, List[str]] = {}
        for sid, info in self.symptoms.items():
            groups.setdefault(info["group"], []).append(sid)
        return groups

    # -------------------------------------------------------------- validation
    def validate(self) -> None:
        """Fail early on typos: unknown symptoms, unreachable facts, bad CFs."""
        derived = set(self._by_goal)
        ids = [r.id for r in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate rule ids in knowledge base")
        for rule in self.rules:
            if not -1.0 <= rule.cf <= 1.0:
                raise ValueError(f"rule {rule.id}: cf {rule.cf} outside [-1, 1]")
            if not rule.if_all and not rule.if_any:
                raise ValueError(f"rule {rule.id}: no conditions")
            for cond in rule.conditions:
                known = (
                    cond in self.symptoms
                    or self.is_negated_symptom(cond)
                    or cond in derived
                )
                if not known:
                    raise ValueError(f"rule {rule.id}: unknown condition '{cond}'")
            if rule.then.startswith("disease:") and rule.then[8:] not in self.diseases:
                raise ValueError(f"rule {rule.id}: unknown disease '{rule.then}'")
        for did in self.diseases:
            if f"disease:{did}" not in derived:
                raise ValueError(f"disease '{did}' has no rules")
