"""Compare MedRule with simpler alternatives on the 40 vignettes in cases.py.

    python experiments/compare_methods.py            # prints a table and writes docs/EXPERIMENT.md

Methods
  full         the complete system (fuzzy fever + certainty factors + negative evidence)
  no_negative  same, but every rule with a negative CF removed         (tests negative evidence)
  crisp_fever  same KB, but temperature turned into fever/high_fever with hard thresholds
               (100.4 F and 102 F) instead of fuzzy degrees            (tests fuzzy logic)
  overlap      baseline: fraction of a disease's symptoms that the user reported
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import CASES, TARGETED             # noqa: E402
from expert_system import ExpertSystem        # noqa: E402
from knowledge_base import KnowledgeBase      # noqa: E402

KB_FULL = KnowledgeBase()
FULL = ExpertSystem(KB_FULL)


def _kb_without_negative_rules() -> KnowledgeBase:
    data = json.loads((ROOT / "data" / "kb.json").read_text(encoding="utf-8"))
    data["rules"] = [r for r in data["rules"] if r["cf"] >= 0]
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(data, fh)
    return KnowledgeBase(fh.name)


NO_NEG = ExpertSystem(_kb_without_negative_rules())


def crisp_inputs(symptoms, absent, temp):
    """Hard-threshold version of the temperature handling."""
    sym, ab = set(symptoms), set(absent)
    if temp is not None:
        for name, limit in (("fever", 100.4), ("high_fever", 102.0)):
            (sym if temp >= limit else ab).add(name)
            (ab if temp >= limit else sym).discard(name)
    return sorted(sym), sorted(ab)


def rank_full(symptoms, absent, temp):
    return [d for d, _ in FULL.diagnose(symptoms, absent, temp).ranked]


def rank_no_negative(symptoms, absent, temp):
    return [d for d, _ in NO_NEG.diagnose(symptoms, absent, temp).ranked]


def rank_crisp(symptoms, absent, temp):
    s, a = crisp_inputs(symptoms, absent, temp)
    return [d for d, _ in FULL.diagnose(s, a).ranked]


_DISEASE_SYMPTOMS = {}
for did in KB_FULL.diseases:
    syms = set()
    for rule in KB_FULL.rules_for(f"disease:{did}"):
        if rule.cf > 0:
            syms |= {c for c in rule.conditions if c in KB_FULL.symptoms}
    _DISEASE_SYMPTOMS[did] = syms


def rank_overlap(symptoms, absent, temp):
    s, _ = crisp_inputs(symptoms, absent, temp)
    scores = {d: len(set(s) & syms) / len(syms) for d, syms in _DISEASE_SYMPTOMS.items()}
    return [d for d, v in sorted(scores.items(), key=lambda kv: (-kv[1], kv[0])) if v > 0]


METHODS = {"full": rank_full, "no_negative": rank_no_negative,
           "crisp_fever": rank_crisp, "overlap": rank_overlap}


def evaluate(cases):
    rows, failures = {}, []
    for name, fn in METHODS.items():
        top1 = top3 = 0
        for symptoms, absent, temp, ok in cases:
            ranked = fn(symptoms, absent, temp)
            top1 += bool(ranked) and ranked[0] in ok
            top3 += bool(set(ranked[:3]) & ok)
            if name == "full" and not (ranked and ranked[0] in ok):
                failures.append((symptoms, temp, sorted(ok), ranked[:3]))
        rows[name] = (top1, top3)
    return rows, failures


def table(rows, n):
    lines = ["| Method | Top-1 correct | Top-3 contains answer |", "|---|---|---|"]
    for name, (t1, t3) in rows.items():
        lines.append(f"| {name} | {t1}/{n} ({t1 / n:.0%}) | {t3}/{n} ({t3 / n:.0%}) |")
    return "\n".join(lines)


def main() -> None:
    out = ["# Experiment: MedRule against simpler methods", "",
           "Vignettes are hand-written by the project author after the knowledge base was built, so this",
           "shows internal consistency on noisy and overlapping presentations, **not clinical accuracy**.",
           "Methods: `full` = the whole system; `no_negative` = negative rules removed; `crisp_fever` =",
           "hard 100.4 F / 102 F thresholds instead of fuzzy degrees; `overlap` = share of a disease's",
           "symptoms reported (baseline).", ""]
    for title, cases, note in (
        (f"General set ({len(CASES)} cases)", CASES, "A fair sample of typical and noisy presentations."),
        (f"Targeted set ({len(TARGETED)} cases)", TARGETED,
         "Written to probe negative evidence and graded fever. Not a fair sample: it shows what each feature is for."),
    ):
        rows, failures = evaluate(cases)
        out += [f"## {title}", "", note, "", table(rows, len(cases)), ""]
        if failures:
            out += ["Cases where the full system's top answer was not acceptable:", ""]
            for sym, temp, ok, got in failures:
                out.append(f"- {', '.join(sym)}" + (f" at {temp} F" if temp else "") + f": expected {ok}, got {got}")
            out.append("")
    text = "\n".join(out)
    print(text)
    (ROOT / "docs" / "EXPERIMENT.md").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
