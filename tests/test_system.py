import pytest

from backward_chaining import FAILED, PROVED, UNKNOWN, open_questions, prove, suggest_questions
from constraints import (PatientProfile, ProfileError, check_profile, final_urgency,
                         safety_alerts)
from expert_system import ExpertSystem

es = ExpertSystem()


def top(symptoms, **kw):
    return es.diagnose(symptoms, **kw)


# ---------------------------------------------------------- end-to-end scenarios
@pytest.mark.parametrize("symptoms, kwargs, expected", [
    (["runny_nose", "sneezing", "sore_throat", "nasal_congestion"], {}, "common_cold"),
    (["sneezing", "itchy_eyes", "runny_nose"], {"temperature_f": 98.4}, "allergic_rhinitis"),
    (["fever", "high_fever", "body_aches", "chills", "fatigue", "cough"], {}, "influenza"),
    (["sore_throat", "fever", "swollen_glands", "difficulty_swallowing"], {"absent": ["cough"]}, "strep_throat"),
    (["vomiting", "diarrhea", "nausea", "abdominal_pain"], {}, "gastroenteritis"),
    (["headache", "light_sensitivity", "nausea", "visual_aura"], {}, "migraine"),
    (["pain_behind_eyes", "joint_pain", "rash", "headache"], {"temperature_f": 104.2}, "dengue"),
    (["burning_urination", "frequent_urination", "cloudy_urine"], {}, "uti"),
    (["fever", "cough", "shortness_of_breath", "chest_pain", "fatigue"], {}, "pneumonia"),
    (["loss_of_smell_taste", "fever", "cough", "fatigue"], {}, "covid19"),
])
def test_expected_top_diagnosis(symptoms, kwargs, expected):
    d = top(symptoms, **kwargs)
    assert d.top == expected, d.ranked


def test_explanation_lists_supporting_rules():
    d = top(["burning_urination", "frequent_urination"])
    assert d.explanation.headline.endswith("Urinary tract infection")
    assert any(rid == "U1" for rid, _, _ in d.explanation.supporting)


def test_measured_temperature_overrides_tickbox():
    d = top(["fever", "cough"], temperature_f=98.4)
    assert "fever" not in d.present and "fever" in d.absent


def test_pain_score_scales_symptom_certainty():
    mild = top(["headache", "nausea"], pain_score=1)
    severe = top(["headache", "nausea"], pain_score=9)
    assert mild.present["headache"] < severe.present["headache"]
    assert mild.facts["disease:migraine"] < severe.facts["disease:migraine"]


def test_no_symptoms_is_rejected():
    with pytest.raises(ValueError):
        es.diagnose([])


def test_unknown_symptom_is_rejected():
    with pytest.raises(ValueError, match="unknown symptom"):
        es.diagnose(["not_a_symptom"])


# --------------------------------------------------------------------- constraints
def test_profile_constraints():
    assert check_profile(PatientProfile(30, "female", False, 1)) == []
    assert check_profile(PatientProfile(30, "male", True, 1))
    assert check_profile(PatientProfile(5, "female", True, 1))
    assert check_profile(PatientProfile(200, "male", False, 1))
    with pytest.raises(ProfileError):
        es.diagnose(["cough"], profile=PatientProfile(30, "male", True))


def test_red_flags_force_urgent_care():
    d = top(["chest_pain", "shortness_of_breath"])
    assert d.urgency == 2
    d = top(["fever", "stiff_neck", "headache"])
    assert d.urgency == 2
    assert top(["confusion", "fever"]).urgency == 2


def test_breathlessness_and_chest_pain_do_not_look_like_a_cold():
    d = top(["cough", "chest_pain", "shortness_of_breath"])
    assert d.top == "pneumonia" and d.urgency == 2


def test_chest_pain_alone_means_see_a_doctor():
    assert top(["chest_pain"]).urgency == 1


def test_urgency_only_rises():
    base = top(["runny_nose", "sneezing"]).urgency
    assert base == 0
    assert top(["runny_nose", "sneezing"], profile=PatientProfile(30, "female", False, 8)).urgency == 1
    level, _ = final_urgency(1, [])
    assert level == 1


def test_age_and_pregnancy_risk():
    assert top(["fever", "cough"], profile=PatientProfile(70, "male", False, 1)).urgency >= 1
    assert top(["fever", "cough"], profile=PatientProfile(0, "male", False, 1)).urgency == 2
    assert top(["vomiting", "diarrhea"], profile=PatientProfile(28, "female", True, 1)).urgency >= 1


def test_dangerous_temperature():
    assert top(["fever"], temperature_f=104.5).urgency == 2
    assert top(["fever"], temperature_f=102.8).urgency >= 1


# --------------------------------------------------------------- backward chaining
def test_prove_status_proved_failed_unknown():
    kb = es.kb
    present = {"burning_urination": 1.0}
    assert prove(kb, "disease:uti", present, set()).status == PROVED
    assert prove(kb, "disease:migraine", {"headache": 1.0}, set()).status == UNKNOWN
    node = prove(kb, "disease:allergic_rhinitis", {"fever": 1.0}, {"sneezing"})
    # A1 needs sneezing which was denied, so that rule is FAILED
    a1 = [c for c in node.children if c.goal == "A1"][0]
    assert a1.status == FAILED


def test_proof_cf_matches_forward_chaining():
    d = top(["burning_urination", "frequent_urination", "cloudy_urine"])
    node = es.proof(d, "uti")
    assert node.cf == pytest.approx(d.facts["disease:uti"])


def test_open_questions_ignore_settled_rules():
    kb = es.kb
    node = prove(kb, "disease:uti", {"burning_urination": 1.0}, {"frequent_urination"})
    assert "frequent_urination" not in open_questions(node)


def test_next_questions_are_unanswered_and_relevant():
    d = top(["headache"])
    qs = es.next_questions(d, k=3)
    asked = {s for s, _ in qs}
    assert qs and asked.isdisjoint(set(d.present) | d.absent)
    assert asked & {"light_sensitivity", "nausea", "visual_aura", "fever"}


def test_skip_excludes_question():
    d = top(["headache"])
    first = es.next_questions(d, k=1)[0][0]
    assert first not in {s for s, _ in es.next_questions(d, k=3, skip=[first])}


def test_answering_questions_improves_confidence():
    d1 = top(["headache"])
    sym = es.next_questions(d1, k=1)[0][0]
    d2 = es.diagnose(["headache", sym])
    assert d2.top_cf >= d1.top_cf
