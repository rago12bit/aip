"""Command-line front end.

Examples
    python cli.py --list-symptoms
    python cli.py --symptoms fever cough body_aches --temp 102.4 --age 28 --sex male
    python cli.py --symptoms sneezing runny_nose --interactive
"""
from __future__ import annotations

import argparse
import sys

from constraints import PatientProfile, ProfileError
from expert_system import Diagnosis, ExpertSystem


def show(es: ExpertSystem, d: Diagnosis, trace: bool) -> None:
    print("\n" + d.explanation.to_text())
    print(f"\nUrgency: {d.urgency_label}")
    for a in d.alerts:
        print(f"  ! {a.message}")
    for line in d.advice:
        print(f"  - {line}")
    if d.see_doctor_if:
        print(f"See a doctor if: {d.see_doctor_if}")
    if trace:
        print("\nRule trace (in firing order):")
        for f in d.firings:
            print(f"  pass {f.pass_no}: {f.rule.id:3} -> {f.rule.then:28} {f.contribution:+.2f}")
    print("\nThis is an educational tool, not medical advice.")


def interactive(es: ExpertSystem, symptoms: set, absent: set, args, profile) -> Diagnosis:
    """Ask up to 5 follow-up questions chosen by backward chaining."""
    d = es.diagnose(symptoms, absent, args.temp, args.pain, profile)
    skipped: set = set()
    for _ in range(5):
        if d.top_cf >= 0.80:
            break
        questions = es.next_questions(d, k=1, skip=skipped)
        if not questions:
            break
        sym, text = questions[0]
        answer = input(f"{text} [y/n/skip] ").strip().lower()
        if answer in {"y", "yes"}:
            symptoms.add(sym)
        elif answer in {"n", "no"}:
            absent.add(sym)
        else:
            skipped.add(sym)
            continue
        d = es.diagnose(symptoms, absent, args.temp, args.pain, profile)
        label = es.kb.diseases[d.top]["label"] if d.top else "no match"
        print(f"  -> now: {label} ({d.top_cf:.0%})")
    return d


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MedRule rule-based symptom checker (educational)")
    p.add_argument("--symptoms", nargs="*", default=[], help="symptom ids, see --list-symptoms")
    p.add_argument("--absent", nargs="*", default=[], help="symptoms you do NOT have")
    p.add_argument("--temp", type=float, help="body temperature in F")
    p.add_argument("--pain", type=float, help="pain rating 0-10")
    p.add_argument("--age", type=int, default=30)
    p.add_argument("--sex", default="female", choices=["female", "male", "other"])
    p.add_argument("--pregnant", action="store_true")
    p.add_argument("--days", type=int, default=1, help="how many days the symptoms have lasted")
    p.add_argument("--interactive", action="store_true", help="ask follow-up questions")
    p.add_argument("--trace", action="store_true", help="print every rule that fired")
    p.add_argument("--list-symptoms", action="store_true")
    args = p.parse_args(argv)

    es = ExpertSystem()
    if args.list_symptoms:
        for group, ids in es.kb.symptom_groups().items():
            print(f"\n{group}")
            for sid in ids:
                print(f"  {sid:24} {es.kb.symptoms[sid]['label']}")
        return 0

    profile = PatientProfile(args.age, args.sex, args.pregnant, args.days)
    try:
        if args.interactive:
            d = interactive(es, set(args.symptoms), set(args.absent), args, profile)
        else:
            d = es.diagnose(args.symptoms, args.absent, args.temp, args.pain, profile)
    except (ProfileError, ValueError) as err:
        print(f"Input problem: {err}", file=sys.stderr)
        return 2
    show(es, d, args.trace)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
