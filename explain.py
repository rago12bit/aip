"""Explanation: turns the engine's trace into a readable report."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import certainty
from forward_chaining import Firing
from knowledge_base import KnowledgeBase


@dataclass
class Explanation:
    headline: str
    confidence: str
    supporting: List[Tuple[str, str, float]] = field(default_factory=list)   # (rule id, reason, CF)
    against: List[Tuple[str, str, float]] = field(default_factory=list)
    alternatives: List[Tuple[str, float]] = field(default_factory=list)      # (label, CF)

    def to_text(self) -> str:
        lines = [self.headline, f"Confidence: {self.confidence}"]
        if self.supporting:
            lines.append("Why:")
            lines += [f"  + [{rid}] {why} (+{cf:.2f})" for rid, why, cf in self.supporting]
        if self.against:
            lines.append("Against:")
            lines += [f"  - [{rid}] {why} ({cf:.2f})" for rid, why, cf in self.against]
        if self.alternatives:
            lines.append("Other possibilities:")
            lines += [f"  * {name} ({cf:.0%})" for name, cf in self.alternatives]
        return "\n".join(lines)


def build_explanation(kb: KnowledgeBase, ranked: List[Tuple[str, float]],
                      firings: List[Firing]) -> Explanation:
    if not ranked:
        return Explanation("No clear match found for these symptoms.", "none")
    top_id, top_cf = ranked[0]
    goal = f"disease:{top_id}"
    supporting, against = [], []
    for f in firings:
        if f.rule.then != goal:
            continue
        item = (f.rule.id, f.rule.why, f.contribution)
        (supporting if f.contribution > 0 else against).append(item)
    supporting.sort(key=lambda x: -x[2])
    against.sort(key=lambda x: x[2])
    alternatives = [(kb.diseases[d]["label"], cf) for d, cf in ranked[1:4]]
    return Explanation(
        headline=f"Most likely: {kb.diseases[top_id]['label']}",
        confidence=f"{certainty.label(top_cf)} ({top_cf:.0%})",
        supporting=supporting, against=against, alternatives=alternatives,
    )
