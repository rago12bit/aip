"""Small fuzzy-logic helper (Zadeh, 1965) for fever and pain readings.

Instead of a hard rule such as "fever if temperature > 100.4 F", a reading
belongs to several overlapping fuzzy sets (normal / low-grade / moderate /
high) with a degree between 0 and 1.  The degrees are turned into
certainty-factor inputs for the rule engine.  Only the standard library is used.
"""
from __future__ import annotations

from typing import Dict


def trapezoid(x: float, a: float, b: float, c: float, d: float) -> float:
    """Trapezoidal membership: 0 below a, rises to 1 at b, flat to c, falls to 0 at d."""
    if x < a or x > d:
        return 0.0
    if b <= x <= c:
        return 1.0
    if x < b:
        return (x - a) / (b - a) if b > a else 1.0
    return (d - x) / (d - c) if d > c else 1.0


# (a, b, c, d) in degrees Fahrenheit.  "normal" fades out between 99.5 and 100.4 F (the usual fever
# line); "high" starts at 101 F and is fully true from 102.5 F, so the 102 F label used in the
# knowledge base ("high fever") is already mostly true.
_TEMP_SETS = {
    "normal":    (90.0, 90.0, 99.5, 100.4),
    "low_grade": (99.5, 100.4, 100.8, 101.8),
    "moderate":  (100.8, 101.8, 102.0, 103.0),
    "high":      (101.0, 102.5, 108.0, 108.0),
}
_TEMP_SCORE = {"normal": 0.0, "low_grade": 0.35, "moderate": 0.7, "high": 1.0}

# (a, b, c, d) on a 0-10 pain scale
_PAIN_SETS = {
    "mild":     (0.0, 0.0, 2.0, 4.0),
    "moderate": (2.0, 4.0, 6.0, 8.0),
    "severe":   (6.0, 8.0, 10.0, 10.0),
}
_PAIN_SCORE = {"mild": 0.2, "moderate": 0.6, "severe": 1.0}


def _fuzzify(x: float, sets: Dict[str, tuple]) -> Dict[str, float]:
    return {name: round(trapezoid(x, *abcd), 3) for name, abcd in sets.items()}


def _defuzzify(memberships: Dict[str, float], scores: Dict[str, float]) -> float:
    """Weighted average of set scores (a Sugeno-style defuzzification)."""
    total = sum(memberships.values())
    if total == 0:
        return 0.0
    return sum(memberships[name] * scores[name] for name in memberships) / total


def fever_profile(temp_f: float) -> Dict[str, float]:
    """Memberships plus derived rule inputs for a body temperature in F.

    Returns the set memberships, a 0-1 `severity`, and two certainty values:
      fever       = how strongly this counts as "has a fever"  (1 - normal)
      high_fever  = membership of the "high" set
    """
    m = _fuzzify(temp_f, _TEMP_SETS)
    return {
        **m,
        "severity": round(_defuzzify(m, _TEMP_SCORE), 3),
        "fever": round(1.0 - m["normal"], 3),
        "high_fever": m["high"],
    }


def pain_profile(score: float) -> Dict[str, float]:
    """Memberships and a 0-1 `severity` for a 0-10 pain rating."""
    m = _fuzzify(score, _PAIN_SETS)
    return {**m, "severity": round(_defuzzify(m, _PAIN_SCORE), 3)}


def pain_certainty(score: float) -> float:
    """Certainty given to a pain-type symptom: mild pain counts for less."""
    return round(0.4 + 0.6 * pain_profile(score)["severity"], 3)
