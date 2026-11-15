# MedRule: a rule-based symptom checker

A small, explainable expert system written in Python. It takes symptoms (and optionally a temperature
and a pain score), reasons with **classical AI rules and algorithms**, and explains every result.
No machine learning and no database: the whole knowledge base is one readable JSON file.

> **Educational project. Not medical advice.** The rules were written for a course and checked against
> NHS condition pages (see `docs/REPORT.md`), but they have *not* been reviewed by a clinician. Never use this to decide on real treatment.

## What it demonstrates

| Technique | File | Role in the system |
|---|---|---|
| Forward chaining | `forward_chaining.py` | symptoms → syndromes → disease hypotheses |
| Backward chaining | `backward_chaining.py` | proof trees, and choosing the next question to ask |
| Certainty factors (MYCIN) | `certainty.py` | combining supporting and opposing evidence |
| Fuzzy logic | `fuzzy.py` | graded fever and pain instead of hard cut-offs |
| Constraint checking | `constraints.py` | rejects impossible profiles; red flags raise urgency |
| Explanation | `explain.py` | lists the rules behind each result |

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py                                   # web app
python cli.py --symptoms fever cough body_aches --temp 102.4 --trace   # command line
python cli.py --symptoms headache --interactive        # asks follow-up questions
python -m pytest                                       # 53 tests
python experiments/compare_methods.py                  # accuracy vs simpler methods
```

`python cli.py --list-symptoms` prints every symptom id. Python 3.10+.
Demo links for screenshots: `http://localhost:8501/?demo=flu`, `?demo=migraine`, `?demo=redflag`.

## Structure

```
app.py               Streamlit UI (check symptoms / how it works / knowledge base)
cli.py               command-line UI, including an interactive question loop
expert_system.py     facade: runs the whole pipeline
knowledge_base.py    loads and validates data/kb.json
forward_chaining.py  backward_chaining.py  certainty.py  fuzzy.py  constraints.py  explain.py
data/kb.json         10 conditions, 31 symptoms, 53 rules
tests/               unit, scenario, experiment and UI tests
experiments/         40 + 10 vignettes and the method comparison (results in docs/EXPERIMENT.md)
docs/REPORT.md       project report (idea, background, algorithm choice, implementation, references)
docs/screenshots/    screenshots of the running app
```

```
UI (app.py / cli.py) → expert_system.py → fuzzy → forward_chaining ⇄ certainty → constraints → explain
                                      ↘ backward_chaining (follow-up questions, proofs)
                                                 ↑ all read knowledge_base.py ← data/kb.json
```

## Origin and changes

The layered architecture (UI → facade → separate reasoning engines → knowledge base) follows
[anandd46/AI_Medical_Diagnosis_Expert_System](https://github.com/anandd46/AI_Medical_Diagnosis_Expert_System)
(MIT licence). The code here was written from scratch, not copied, and deliberately made much smaller:

| | Reference project | MedRule |
|---|---|---|
| Storage | SQLite + SQLAlchemy, patient records, visits | one JSON file, no accounts |
| Logic | hand-built predicate-logic/unification engine | plain rule objects with certainty factors |
| Fuzzy logic | scikit-fuzzy, Mamdani system | under 80 lines of standard-library trapezoid sets |
| Search extras | best-first, hill climbing, generate-and-test, problem reduction, networkx tree, PDF export | removed |
| Treatments | medicine database | removed (general advice only, for safety) |
| **Added** | | negative evidence rules, measured-temperature override, red-flag/age/pregnancy urgency escalation, question-ranking heuristic, CLI, rule-trace table, demo links, comparison experiment, 53 automated tests |

## Licence

MIT, see `LICENSE`.
