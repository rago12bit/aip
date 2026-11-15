"""MYCIN-style certainty factors (Shortliffe & Buchanan, 1975).

A certainty factor (CF) lies in [-1, 1]: +1 is certainly true, -1 certainly
false, 0 no evidence.  Several rules can support or oppose the same
hypothesis; their CFs are merged with the standard MYCIN combination formula.
"""
from __future__ import annotations

from typing import Dict, List, Tuple


def combine(cf1: float, cf2: float) -> float:
    """Merge two CFs for the same hypothesis.  Order does not matter."""
    if cf1 >= 0 and cf2 >= 0:
        return cf1 + cf2 * (1 - cf1)
    if cf1 <= 0 and cf2 <= 0:
        return cf1 + cf2 * (1 + cf1)
    return (cf1 + cf2) / (1 - min(abs(cf1), abs(cf2)))


def label(cf: float) -> str:
    """Plain-language confidence band for a positive CF."""
    if cf >= 0.80:
        return "very high"
    if cf >= 0.60:
        return "high"
    if cf >= 0.40:
        return "moderate"
    if cf >= 0.20:
        return "low"
    return "very low"


def rank_diseases(facts: Dict[str, float], min_cf: float = 0.0) -> List[Tuple[str, float]]:
    """Disease hypotheses with CF above `min_cf`, best first."""
    ranked = [
        (fact[8:], cf) for fact, cf in facts.items()
        if fact.startswith("disease:") and cf > min_cf
    ]
    return sorted(ranked, key=lambda item: (-item[1], item[0]))
