"""40 hand-written patient vignettes used by compare_methods.py.

They were written *after* the knowledge base, by the project author, from general knowledge of
how these conditions present.  They test whether the engine behaves sensibly on noisy and
overlapping presentations; they are NOT clinical ground truth.

Each case: (symptoms, absent symptoms, temperature in F or None, acceptable top conditions)
"""

CASES = [
    # common cold
    (["runny_nose", "sneezing", "sore_throat", "cough"], [], 98.8, {"common_cold"}),
    (["nasal_congestion", "runny_nose", "cough"], ["fever"], None, {"common_cold"}),
    (["sore_throat", "runny_nose", "sneezing", "fatigue"], [], None, {"common_cold"}),
    (["nasal_congestion", "sneezing", "cough", "headache"], [], 99.1, {"common_cold"}),
    (["runny_nose", "nasal_congestion", "sore_throat", "cough"], [], 100.6, {"common_cold"}),
    (["runny_nose", "sneezing", "rash"], [], None, {"common_cold"}),            # unrelated extra symptom
    # influenza
    (["fever", "high_fever", "body_aches", "chills", "fatigue", "cough", "headache"], [], 103.1, {"influenza"}),
    (["fever", "body_aches", "fatigue", "cough", "sore_throat"], [], 102.0, {"influenza"}),
    (["chills", "fatigue", "body_aches", "cough", "headache"], [], 101.5, {"influenza"}),
    (["fever", "cough", "body_aches", "headache", "runny_nose"], [], 102.8, {"influenza"}),
    (["fever", "high_fever", "body_aches", "chills", "sore_throat", "headache"], [], 103.2, {"influenza"}),
    # COVID-19
    (["loss_of_smell_taste", "fever", "cough", "fatigue"], [], 100.8, {"covid19"}),
    (["loss_of_smell_taste", "sore_throat", "headache", "runny_nose"], ["fever"], None, {"covid19"}),
    (["fever", "cough", "shortness_of_breath", "fatigue", "body_aches"], [], 101.2, {"covid19", "pneumonia"}),
    # allergic rhinitis
    (["sneezing", "itchy_eyes", "runny_nose", "nasal_congestion"], [], 98.2, {"allergic_rhinitis"}),
    (["sneezing", "itchy_eyes", "nasal_congestion", "headache"], ["fever"], None, {"allergic_rhinitis"}),
    (["sneezing", "runny_nose", "itchy_eyes", "cough"], [], 98.6, {"allergic_rhinitis"}),
    # strep throat
    (["sore_throat", "fever", "swollen_glands", "difficulty_swallowing", "headache"], ["cough"], 101.9, {"strep_throat"}),
    (["sore_throat", "difficulty_swallowing", "swollen_glands"], ["cough", "runny_nose"], 100.9, {"strep_throat"}),
    (["sore_throat", "fever", "swollen_glands"], ["cough"], None, {"strep_throat"}),
    # gastroenteritis
    (["vomiting", "diarrhea", "nausea", "abdominal_pain"], [], None, {"gastroenteritis"}),
    (["diarrhea", "nausea", "abdominal_pain"], [], 99.8, {"gastroenteritis"}),
    (["vomiting", "nausea", "diarrhea", "fatigue"], [], 100.6, {"gastroenteritis"}),
    (["nausea", "vomiting", "abdominal_pain"], [], None, {"gastroenteritis"}),
    # migraine
    (["headache", "light_sensitivity", "nausea"], ["fever"], None, {"migraine"}),
    (["visual_aura", "headache", "nausea"], [], None, {"migraine"}),
    (["headache", "light_sensitivity", "vomiting"], [], 98.4, {"migraine"}),
    (["headache", "nausea", "light_sensitivity", "fatigue"], [], None, {"migraine"}),
    # dengue
    (["fever", "high_fever", "pain_behind_eyes", "joint_pain", "headache", "rash"], [], 103.8, {"dengue"}),
    (["high_fever", "headache", "joint_pain", "body_aches", "nausea"], [], 103.5, {"dengue"}),
    (["fever", "rash", "joint_pain", "body_aches", "pain_behind_eyes"], [], 102.9, {"dengue"}),
    (["high_fever", "pain_behind_eyes", "headache", "vomiting"], [], 104.0, {"dengue"}),
    # urinary tract infection
    (["burning_urination", "frequent_urination"], [], None, {"uti"}),
    (["frequent_urination", "cloudy_urine", "abdominal_pain"], [], None, {"uti"}),
    (["burning_urination", "cloudy_urine", "abdominal_pain"], [], 99.0, {"uti"}),
    (["burning_urination", "frequent_urination", "headache", "fatigue"], [], None, {"uti"}),
    # pneumonia
    (["fever", "high_fever", "cough", "shortness_of_breath", "chest_pain", "fatigue"], [], 103.0, {"pneumonia"}),
    (["cough", "chest_pain", "shortness_of_breath", "fatigue"], [], 100.8, {"pneumonia"}),
    (["fever", "cough", "shortness_of_breath"], [], 102.2, {"pneumonia", "covid19"}),
    (["high_fever", "cough", "chest_pain", "body_aches", "fatigue"], [], 103.4, {"pneumonia"}),
]


# ---------------------------------------------------------------------------------------------
# TARGETED cases: written on purpose to probe one feature each, so they are NOT a fair sample.
# Expected answers come from clinical reasoning (e.g. allergy does not cause fever), not from
# running the model.  They show what a feature is *for*; the general set above is the fair test.
# ---------------------------------------------------------------------------------------------
TARGETED = [
    # negative evidence: fever argues against allergy / migraine, cough+runny nose against strep
    (["sneezing", "runny_nose", "nasal_congestion", "sore_throat"], [], 101.0, {"common_cold", "influenza"}),
    (["sneezing", "itchy_eyes", "runny_nose", "body_aches"], [], 101.6, {"common_cold", "influenza"}),
    (["headache", "nausea", "light_sensitivity", "body_aches", "chills"], [], 102.0, {"influenza", "dengue"}),
    (["sore_throat", "fever", "cough", "runny_nose", "nasal_congestion"], [], 100.9, {"common_cold", "influenza"}),
    (["high_fever", "headache", "runny_nose", "cough", "sneezing"], [], 102.4, {"influenza", "common_cold"}),
    # graded fever: values at or near the 102 F "high fever" line
    (["pain_behind_eyes", "joint_pain", "headache"], [], 102.0, {"dengue"}),
    (["pain_behind_eyes", "joint_pain", "headache", "nausea"], [], 102.2, {"dengue"}),
    (["cough", "body_aches", "chills", "fatigue", "headache"], [], 102.0, {"influenza"}),
    (["runny_nose", "sneezing", "sore_throat", "cough"], [], 100.5, {"common_cold"}),
    (["sneezing", "itchy_eyes", "runny_nose"], [], 99.4, {"allergic_rhinitis"}),
]
