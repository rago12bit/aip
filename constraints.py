"""Constraint checking: patient consistency and safety rules.

Two layers, kept separate from the symptom reasoning on purpose:

1. Hard consistency constraints on the profile (age range, sex/pregnancy
   compatibility).  A profile that violates one is rejected, as in a
   constraint-satisfaction problem where an assignment must satisfy every
   constraint.
2. Safety constraints that can only raise the urgency level, never lower it:
   red-flag symptom combinations, age and pregnancy risk, high or long-lasting fever.

Urgency levels: 0 self-care, 1 see a doctor soon, 2 seek urgent care now.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

URGENCY_LABELS = {0: "Self-care is reasonable", 1: "See a doctor soon", 2: "Seek urgent care now"}


class ProfileError(ValueError):
    """Raised when the patient profile breaks a hard constraint."""

    def __init__(self, problems: List[str]) -> None:
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass
class PatientProfile:
    age: int = 30
    sex: str = "female"            # "female" | "male" | "other"
    pregnant: bool = False
    duration_days: int = 1         # how long the symptoms have lasted


@dataclass
class Alert:
    level: int                     # 1 = see doctor, 2 = urgent
    message: str


def check_profile(p: PatientProfile) -> List[str]:
    """Hard constraints.  Returns the list of violated constraints (empty = valid)."""
    problems = []
    if not 0 <= p.age <= 120:
        problems.append("age must be between 0 and 120")
    if p.sex not in {"female", "male", "other"}:
        problems.append("sex must be female, male or other")
    if p.pregnant and p.sex == "male":
        problems.append("a male patient cannot be pregnant")
    if p.pregnant and not 10 <= p.age <= 60:
        problems.append("pregnancy is not plausible for this age")
    if p.duration_days < 0:
        problems.append("duration cannot be negative")
    return problems


def safety_alerts(profile: PatientProfile, present: Dict[str, float],
                  temp_f: Optional[float] = None) -> List[Alert]:
    """Safety constraints that may escalate urgency."""
    has = lambda s: present.get(s, 0.0) > 0          # noqa: E731
    fever = has("fever") or has("high_fever") or (temp_f is not None and temp_f >= 100.4)
    alerts: List[Alert] = []

    # Red-flag combinations
    if has("chest_pain") and has("shortness_of_breath"):
        alerts.append(Alert(2, "Chest pain with shortness of breath can signal a serious problem."))
    if has("stiff_neck") and fever:
        alerts.append(Alert(2, "Fever with a stiff neck needs urgent medical assessment."))
    if has("confusion"):
        alerts.append(Alert(2, "Confusion or difficulty staying awake needs urgent care."))
    if has("shortness_of_breath") and not has("chest_pain"):
        alerts.append(Alert(1, "Shortness of breath should be checked by a doctor."))
    if has("chest_pain") and not has("shortness_of_breath"):
        alerts.append(Alert(1, "Chest pain should be checked by a doctor."))

    # Temperature
    if temp_f is not None and temp_f >= 104.0:
        alerts.append(Alert(2, f"A temperature of {temp_f:.1f} F is dangerously high."))
    elif temp_f is not None and temp_f >= 102.5:
        alerts.append(Alert(1, f"A temperature of {temp_f:.1f} F is high enough to see a doctor."))

    # Who is at higher risk
    if fever and profile.age < 1:
        alerts.append(Alert(2, "Fever in a baby under one year needs urgent care."))
    elif fever and (profile.age < 5 or profile.age >= 65):
        alerts.append(Alert(1, "Fever in a young child or an older adult should be seen by a doctor."))
    if profile.pregnant and (fever or has("vomiting") or has("abdominal_pain")):
        alerts.append(Alert(1, "Fever, vomiting or belly pain during pregnancy should be checked by a doctor."))

    # Duration
    if fever and profile.duration_days >= 3:
        alerts.append(Alert(1, "Fever lasting 3 days or more should be checked by a doctor."))
    elif profile.duration_days >= 7:
        alerts.append(Alert(1, "Symptoms lasting a week or more should be checked by a doctor."))

    return alerts


def final_urgency(base: int, alerts: List[Alert]) -> Tuple[int, str]:
    """Urgency can only go up: the highest of the disease's own level and every alert."""
    level = max([base] + [a.level for a in alerts])
    return level, URGENCY_LABELS[level]
