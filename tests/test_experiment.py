import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments"))

from cases import CASES, TARGETED          # noqa: E402
from compare_methods import evaluate       # noqa: E402


def test_general_accuracy_does_not_regress():
    rows, _ = evaluate(CASES)
    top1, top3 = rows["full"]
    assert top1 / len(CASES) >= 0.90
    assert top3 == len(CASES)


def test_targeted_cases_all_pass():
    rows, failures = evaluate(TARGETED)
    assert rows["full"][0] == len(TARGETED), failures
