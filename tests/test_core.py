import json

import pytest

import certainty
from forward_chaining import forward_chain
from fuzzy import fever_profile, pain_certainty, pain_profile, trapezoid
from knowledge_base import KnowledgeBase


# ---------------------------------------------------------------- certainty factors
def test_combine_two_positive():
    assert certainty.combine(0.5, 0.5) == pytest.approx(0.75)


def test_combine_two_negative():
    assert certainty.combine(-0.5, -0.5) == pytest.approx(-0.75)


def test_combine_mixed_and_commutative():
    assert certainty.combine(0.6, -0.3) == pytest.approx(0.3 / 0.7)
    assert certainty.combine(0.6, -0.3) == pytest.approx(certainty.combine(-0.3, 0.6))


def test_combine_never_leaves_range():
    for a in (-1, -0.4, 0, 0.4, 1):
        for b in (-1, -0.4, 0, 0.4, 0.99):
            if a == 1 and b == -1:
                continue
            assert -1.0 <= certainty.combine(a, b) <= 1.0


def test_labels():
    assert certainty.label(0.85) == "very high"
    assert certainty.label(0.45) == "moderate"
    assert certainty.label(0.05) == "very low"


# --------------------------------------------------------------------------- fuzzy
def test_trapezoid_shape():
    assert trapezoid(5, 0, 2, 4, 6) == pytest.approx(0.5)      # falling edge
    assert trapezoid(1, 0, 2, 4, 6) == pytest.approx(0.5)      # rising edge
    assert trapezoid(3, 0, 2, 4, 6) == 1.0
    assert trapezoid(7, 0, 2, 4, 6) == 0.0


def test_fever_line_is_around_100_4():
    assert fever_profile(99.4)["fever"] == 0
    assert 0 < fever_profile(99.9)["fever"] < 0.5
    assert fever_profile(100.4)["fever"] == 1


def test_normal_temperature_is_not_fever():
    p = fever_profile(98.6)
    assert p["fever"] == 0 and p["high_fever"] == 0 and p["severity"] == 0


def test_fever_degrees_grow_with_temperature():
    sev = [fever_profile(t)["severity"] for t in (98.6, 100.6, 102.2, 104.5)]
    assert sev == sorted(sev) and sev[0] < sev[-1] == 1.0


def test_borderline_temperature_is_partly_high():
    assert 0 < fever_profile(102.0)["high_fever"] < 1
    assert fever_profile(102.5)["high_fever"] == 1


def test_pain_certainty_range_and_order():
    assert pain_certainty(1) < pain_certainty(5) < pain_certainty(9) <= 1.0
    assert pain_profile(9)["severe"] == 1.0


# ---------------------------------------------------------------- knowledge base
def test_kb_loads_and_is_consistent():
    kb = KnowledgeBase()
    assert len(kb.diseases) == 10 and len(kb.symptoms) >= 30 and len(kb.rules) == 53


def test_kb_rejects_unknown_condition(tmp_path):
    data = json.loads(open(KnowledgeBase.__init__.__globals__["DEFAULT_PATH"]).read())
    data["rules"].append({"id": "BAD", "if": ["no_such_symptom"], "then": "disease:influenza", "cf": 0.5})
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="unknown condition"):
        KnowledgeBase(path)


def test_kb_rejects_cf_out_of_range(tmp_path):
    data = json.loads(open(KnowledgeBase.__init__.__globals__["DEFAULT_PATH"]).read())
    data["rules"][0]["cf"] = 1.5
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="outside"):
        KnowledgeBase(path)


# ------------------------------------------------------------------ forward chaining
def test_forward_chaining_derives_syndromes_then_diseases():
    kb = KnowledgeBase()
    r = forward_chain(kb, {"fever": 1.0, "cough": 1.0, "chills": 1.0})
    assert r.facts["syndrome:respiratory"] == 1.0
    assert r.facts["syndrome:systemic"] == 1.0
    assert r.facts["disease:influenza"] > 0


def test_each_rule_fires_at_most_once():
    kb = KnowledgeBase()
    r = forward_chain(kb, {"fever": 1.0, "cough": 1.0, "chills": 1.0, "body_aches": 1.0})
    ids = [f.rule.id for f in r.firings]
    assert len(ids) == len(set(ids))


def test_negative_rule_lowers_confidence():
    kb = KnowledgeBase()
    with_fever = forward_chain(kb, {"sneezing": 1.0, "runny_nose": 1.0, "fever": 1.0})
    without = forward_chain(kb, {"sneezing": 1.0, "runny_nose": 1.0, "not:fever": 1.0})
    assert without.facts.get("disease:allergic_rhinitis", 0) > with_fever.facts["disease:allergic_rhinitis"]
    assert with_fever.facts["disease:allergic_rhinitis"] < 0


def test_fuzzy_certainty_scales_conclusion():
    kb = KnowledgeBase()
    strong = forward_chain(kb, {"burning_urination": 1.0})
    weak = forward_chain(kb, {"burning_urination": 0.5})
    assert weak.facts["disease:uti"] == pytest.approx(strong.facts["disease:uti"] / 2)
