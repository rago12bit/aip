"""Backward chaining (goal-driven inference).

Begin with a goal such as "disease:influenza" and work backwards: find the
rules that conclude it, then try to prove each premise, recursing through
syndromes down to symptoms.  A symptom the user has neither reported nor
denied becomes an *open question*.  This gives two things:

  * prove()          - a proof tree showing why a hypothesis does or does not hold
  * suggest_questions() - which unanswered symptom is most worth asking next
                          (goal-directed questioning, in the spirit of
                          means-end analysis: ask what closes the biggest gap)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from certainty import combine
from knowledge_base import KnowledgeBase

PROVED, FAILED, UNKNOWN = "proved", "failed", "unknown"


@dataclass
class ProofNode:
    goal: str                    # fact name, or rule id for rule nodes
    kind: str                    # "symptom" | "derived" | "rule"
    status: str                  # PROVED / FAILED / UNKNOWN
    cf: float = 0.0
    weight: float = 0.0          # |rule cf| for rule nodes (importance of the evidence)
    children: List["ProofNode"] = field(default_factory=list)


def prove(kb: KnowledgeBase, goal: str, present: Dict[str, float], absent: Set[str],
          _memo: Dict[str, ProofNode] | None = None) -> ProofNode:
    """Try to prove `goal` from the user's answers so far."""
    memo = {} if _memo is None else _memo
    if goal in memo:
        return memo[goal]

    # --- leaf: a symptom (or its negation) the user may or may not have answered
    base = goal[4:] if goal.startswith("not:") else goal
    if base in kb.symptoms:
        negated = goal.startswith("not:")
        if base in present and present[base] > 0:
            node = ProofNode(goal, "symptom", FAILED if negated else PROVED, 0.0 if negated else present[base])
        elif base in absent:
            node = ProofNode(goal, "symptom", PROVED if negated else FAILED, 1.0 if negated else 0.0)
        else:
            node = ProofNode(goal, "symptom", UNKNOWN)
        memo[goal] = node
        return node

    # --- derived fact: try every rule that concludes it
    rule_nodes: List[ProofNode] = []
    total, any_unknown = None, False
    for rule in kb.rules_for(goal):
        kids = [prove(kb, c, present, absent, memo) for c in rule.conditions]
        all_kids = kids[: len(rule.if_all)]
        any_kids = kids[len(rule.if_all):]
        if any(k.status == FAILED for k in all_kids) or (any_kids and all(k.status == FAILED for k in any_kids)):
            status = FAILED
        elif all(k.status == PROVED for k in all_kids) and (not any_kids or any(k.status == PROVED for k in any_kids)):
            status = PROVED
        else:
            status = UNKNOWN
        cf = 0.0
        if status == PROVED:
            proven = [k.cf for k in all_kids] + ([max(k.cf for k in any_kids if k.status == PROVED)] if any_kids else [])
            cf = rule.cf * min(proven)
            total = cf if total is None else combine(total, cf)
        elif status == UNKNOWN:
            any_unknown = True
        rule_nodes.append(ProofNode(rule.id, "rule", status, cf, abs(rule.cf), kids))
    if total is not None:
        node = ProofNode(goal, "derived", PROVED, total, children=rule_nodes)
    elif any_unknown:
        node = ProofNode(goal, "derived", UNKNOWN, children=rule_nodes)
    else:
        node = ProofNode(goal, "derived", FAILED, children=rule_nodes)
    memo[goal] = node
    return node


def open_questions(node: ProofNode, weight: float = 1.0) -> Dict[str, float]:
    """Unanswered symptoms under `node`, each with the weight of the strongest rule needing it."""
    found: Dict[str, float] = {}
    if node.kind == "symptom":
        if node.status == UNKNOWN:
            found[node.goal.replace("not:", "")] = weight
        return found
    if node.kind == "derived" and node.status == PROVED and node.cf >= 0.999:
        return found                      # already certain: more answers change nothing
    for child in node.children:
        w = weight * child.weight if child.kind == "rule" else weight   # weights multiply along the chain
        if child.kind == "rule" and child.status != UNKNOWN:
            continue                      # rule already settled: asking more cannot change it
        for sym, sw in open_questions(child, w).items():
            found[sym] = max(found.get(sym, 0.0), sw)
    return found


def _candidates(kb: KnowledgeBase, ranked: List[Tuple[str, float]], facts: Dict[str, float],
                top_n: int) -> List[Tuple[str, float]]:
    """Ranked hypotheses, topped up with diseases that share evidence but have no CF yet.

    A lone symptom may not complete any rule, so `ranked` can be empty; such diseases
    still deserve questions.  Their nominal CF is small and grows with the overlap.
    """
    cands = list(ranked)
    have = {d for d, _ in ranked}
    for did in kb.diseases:
        if did in have:
            continue
        overlap = sum(1 for r in kb.rules_for(f"disease:{did}")
                      for c in r.conditions if facts.get(c, 0.0) > 0)
        if overlap:
            cands.append((did, 0.05 * overlap))
    cands.sort(key=lambda item: (-item[1], item[0]))
    return cands[:top_n]


def suggest_questions(kb: KnowledgeBase, ranked: List[Tuple[str, float]],
                      present: Dict[str, float], absent: Set[str],
                      facts: Dict[str, float] | None = None,
                      top_n: int = 3, k: int = 3,
                      exclude: Set[str] = frozenset()) -> List[Tuple[str, float]]:
    """Pick the next symptoms to ask about, best first.

    score = sum over the top-N hypotheses of (hypothesis CF * weight of the rule
            that needs the symptom)
          + 0.5 * (sum of those CFs) * (largest - smallest weight)
    The first term chases the most likely diagnoses; the second prefers a symptom
    that helps tell the leading candidates apart.  Rule weights are multiplied
    along the chain, so evidence two steps away counts for less.
    """
    per_hyp: List[Tuple[float, Dict[str, float]]] = []
    memo: Dict[str, ProofNode] = {}
    for did, cf in _candidates(kb, ranked, facts or present, top_n):
        node = prove(kb, f"disease:{did}", present, absent, memo)
        per_hyp.append((cf, open_questions(node)))
    symptoms = {s for _, qs in per_hyp for s in qs} - set(exclude)
    if "fever" not in present:                 # ask about fever before asking how high it is
        symptoms.discard("high_fever")
    scored = []
    for sym in symptoms:
        weights = [qs.get(sym, 0.0) for _, qs in per_hyp]
        mass = sum(cf for cf, _ in per_hyp)
        score = sum(cf * w for (cf, _), w in zip(per_hyp, weights)) + 0.5 * mass * (max(weights) - min(weights))
        scored.append((sym, round(score, 3)))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored[:k]
