"""Facade that runs the whole pipeline.

    inputs -> fuzzy fever/pain -> forward chaining (+ certainty factors)
           -> ranking -> constraint checks -> explanation
    follow-up: backward chaining picks the next question to ask
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

import certainty
from backward_chaining import ProofNode, prove, suggest_questions
from constraints import Alert, PatientProfile, ProfileError, check_profile, final_urgency, safety_alerts
from explain import Explanation, build_explanation
from forward_chaining import Firing, forward_chain
from fuzzy import fever_profile, pain_certainty
from knowledge_base import KnowledgeBase

MIN_CF = 0.10            # hypotheses below this are not reported
MIN_TOP_CF = 0.30        # below this the top match is too weak to set the urgency


@dataclass
class Diagnosis:
    ranked: List[Tuple[str, float]]
    urgency: int
    urgency_label: str
    alerts: List[Alert]
    explanation: Explanation
    present: Dict[str, float]
    absent: Set[str]
    facts: Dict[str, float]
    firings: List[Firing]
    advice: List[str] = field(default_factory=list)
    see_doctor_if: str = ""
    temperature: Optional[Dict[str, float]] = None

    @property
    def top(self) -> Optional[str]:
        return self.ranked[0][0] if self.ranked else None

    @property
    def top_cf(self) -> float:
        return self.ranked[0][1] if self.ranked else 0.0


class ExpertSystem:
    def __init__(self, kb: Optional[KnowledgeBase] = None) -> None:
        self.kb = kb or KnowledgeBase()

    def diagnose(self, symptoms: Iterable[str], absent: Iterable[str] = (),
                 temperature_f: Optional[float] = None, pain_score: Optional[float] = None,
                 profile: Optional[PatientProfile] = None) -> Diagnosis:
        profile = profile or PatientProfile()
        problems = check_profile(profile)
        if problems:
            raise ProfileError(problems)
        unknown = [s for s in list(symptoms) + list(absent) if s not in self.kb.symptoms]
        if unknown:
            raise ValueError(f"unknown symptom(s): {', '.join(sorted(set(unknown)))}")

        present: Dict[str, float] = {s: 1.0 for s in symptoms}
        denied: Set[str] = set(absent) - set(present)

        temp = None
        if temperature_f is not None:
            temp = fever_profile(temperature_f)       # a measured value overrides the tick-boxes
            for sym in ("fever", "high_fever"):
                if temp[sym] > 0:
                    present[sym] = temp[sym]
                    denied.discard(sym)
                else:
                    present.pop(sym, None)
                    denied.add(sym)
        if pain_score is not None:
            for sym, cf in list(present.items()):
                if self.kb.symptoms[sym].get("scale") == "pain" and cf == 1.0:
                    present[sym] = pain_certainty(pain_score)

        if not present:
            raise ValueError("select at least one symptom or enter a temperature above normal")

        initial = dict(present)
        initial.update({f"not:{s}": 1.0 for s in denied})
        result = forward_chain(self.kb, initial)

        ranked = certainty.rank_diseases(result.facts, MIN_CF)
        alerts = safety_alerts(profile, present, temperature_f)
        top_urgency = 0
        advice: List[str] = []
        see_doctor_if = ""
        if ranked and ranked[0][1] >= MIN_TOP_CF:
            info = self.kb.diseases[ranked[0][0]]
            top_urgency, advice, see_doctor_if = info["urgency"], info["advice"], info["see_doctor_if"]
        elif not ranked:
            advice = ["The symptoms do not match any condition in the knowledge base."]
            see_doctor_if = "Symptoms persist, get worse, or worry you."
        urgency, urgency_label = final_urgency(top_urgency, alerts)

        return Diagnosis(
            ranked=ranked, urgency=urgency, urgency_label=urgency_label, alerts=alerts,
            explanation=build_explanation(self.kb, ranked, result.firings),
            present=present, absent=denied, facts=result.facts, firings=result.firings,
            advice=advice, see_doctor_if=see_doctor_if, temperature=temp,
        )

    def next_questions(self, d: Diagnosis, k: int = 3,
                       skip: Iterable[str] = ()) -> List[Tuple[str, str]]:
        """Follow-up questions as (symptom id, question text), most useful first."""
        picks = suggest_questions(self.kb, d.ranked, d.present, d.absent, facts=d.facts, k=k, exclude=set(skip))
        return [(sym, self.kb.symptoms[sym]["ask"]) for sym, _ in picks]

    def proof(self, d: Diagnosis, disease_id: str) -> ProofNode:
        return prove(self.kb, f"disease:{disease_id}", d.present, d.absent)
