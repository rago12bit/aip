"""Forward chaining (data-driven inference).

Start from the facts the user supplied, repeatedly fire every rule whose
conditions are satisfied, add its conclusion to working memory, and stop when
no new rule can fire.  Chains are short here: symptoms -> syndrome -> disease.

Certainty handling
    premise certainty = min over `if_all` conditions (and the best `if_any`)
    conclusion CF     = rule.cf * premise certainty
    if the conclusion already has a CF, the two are merged with MYCIN's formula.
Each rule fires at most once, so evidence is never counted twice.  Syndrome
facts always have CF 1.0, so a rule that depends on one never needs re-firing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from certainty import combine
from knowledge_base import KnowledgeBase, Rule


@dataclass
class Firing:
    rule: Rule
    premise_cf: float
    contribution: float          # rule.cf * premise_cf
    pass_no: int


@dataclass
class ForwardResult:
    facts: Dict[str, float]      # final working memory: fact -> CF
    firings: List[Firing]
    passes: int


def premise_certainty(rule: Rule, facts: Dict[str, float]) -> Optional[float]:
    """CF of a rule's premise, or None if the rule cannot fire yet."""
    values = []
    for cond in rule.if_all:
        cf = facts.get(cond, 0.0)
        if cf <= 0:
            return None
        values.append(cf)
    if rule.if_any:
        best = max((facts.get(cond, 0.0) for cond in rule.if_any), default=0.0)
        if best <= 0:
            return None
        values.append(best)
    return min(values)


def forward_chain(kb: KnowledgeBase, initial_facts: Dict[str, float]) -> ForwardResult:
    facts = dict(initial_facts)
    fired: set = set()
    firings: List[Firing] = []
    pass_no = 0
    changed = True
    while changed:                       # until a full pass fires nothing new
        changed = False
        pass_no += 1
        for rule in kb.rules:
            if rule.id in fired:
                continue
            pc = premise_certainty(rule, facts)
            if pc is None:
                continue
            contribution = rule.cf * pc
            facts[rule.then] = (
                combine(facts[rule.then], contribution) if rule.then in facts else contribution
            )
            fired.add(rule.id)
            firings.append(Firing(rule, pc, contribution, pass_no))
            changed = True
    return ForwardResult(facts=facts, firings=firings, passes=pass_no - 1 if firings else 0)
