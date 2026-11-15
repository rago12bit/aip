"""Streamlit front end.  Run with:  streamlit run app.py"""
from __future__ import annotations

import pandas as pd
import streamlit as st

import certainty
from constraints import PatientProfile, ProfileError
from expert_system import ExpertSystem

st.set_page_config(page_title="MedRule", page_icon="🩺", layout="wide")


@st.cache_resource
def load_system() -> ExpertSystem:
    return ExpertSystem()


es = load_system()
kb = es.kb

# Demo links, e.g. http://localhost:8501/?demo=flu pre-fills a case and runs it (handy for screenshots).
DEMOS = {
    "flu": {"symptoms": ["fever", "chills", "body_aches", "cough", "sore_throat"], "temp": 102.4},
    "migraine": {"symptoms": ["headache", "light_sensitivity", "nausea"], "temp": None},
    "redflag": {"symptoms": ["chest_pain", "shortness_of_breath", "cough"], "temp": None},
}
demo = DEMOS.get(st.query_params.get("demo", ""))
if demo and not st.session_state.get("demo_loaded"):
    st.session_state["demo_loaded"] = True
    for sid in demo["symptoms"]:
        st.session_state.setdefault(f"sel_{kb.symptoms[sid]['group']}", []).append(sid)
    if demo["temp"]:
        st.session_state["temp_on"], st.session_state["temp_val"] = True, demo["temp"]
    st.session_state.analysed = True
    st.session_state.yes, st.session_state.no, st.session_state.skip = set(), set(), set()

st.title("🩺 MedRule: rule-based symptom checker")
st.caption("Educational AI project. It is not medical advice and cannot replace a doctor.")

# ------------------------------------------------------------------ sidebar inputs
with st.sidebar:
    st.header("About you")
    age = st.number_input("Age", 0, 120, 30)
    sex = st.selectbox("Sex", ["female", "male", "other"])
    pregnant = st.checkbox("Pregnant", disabled=(sex == "male"))
    days = st.number_input("Days with symptoms", 0, 60, 1)
    st.header("Measurements (optional)")
    temp_on = st.checkbox("I measured my temperature", key="temp_on")
    temp = st.number_input("Temperature (°F)", 90.0, 110.0, 98.6, 0.1, key="temp_val") if temp_on else None
    pain_on = st.checkbox("Rate my pain")
    pain = st.slider("Pain (0 none, 10 worst)", 0, 10, 4) if pain_on else None

tab_check, tab_how, tab_kb = st.tabs(["Check symptoms", "How it works", "Knowledge base"])

# --------------------------------------------------------------------- symptom check
with tab_check:
    st.subheader("1. What are you experiencing?")
    chosen = []
    cols = st.columns(3)
    for i, (group, ids) in enumerate(kb.symptom_groups().items()):
        with cols[i % 3]:
            picked = st.multiselect(
                group, ids, format_func=lambda s: kb.symptoms[s]["label"], key=f"sel_{group}"
            )
            chosen += picked

    if st.button("Analyse", type="primary"):
        st.session_state.analysed = True
        st.session_state.yes, st.session_state.no, st.session_state.skip = set(), set(), set()

    if st.session_state.get("analysed"):
        yes, no, skip = st.session_state.yes, st.session_state.no, st.session_state.skip
        symptoms = sorted(set(chosen) | yes)
        absent = sorted(no - set(symptoms))
        profile = PatientProfile(int(age), sex, bool(pregnant), int(days))
        try:
            d = es.diagnose(symptoms, absent, temp, pain, profile)
        except ProfileError as err:
            st.error("Please fix your details: " + "; ".join(err.problems))
            st.stop()
        except ValueError as err:
            st.warning(str(err).capitalize() + ".")
            st.stop()

        st.subheader("2. Result")
        banner = {0: st.success, 1: st.warning, 2: st.error}[d.urgency]
        banner(f"**{d.urgency_label}**")
        for alert in d.alerts:
            st.write(f"⚠️ {alert.message}")

        left, right = st.columns([1, 1])
        with left:
            if d.top:
                st.metric(d.explanation.headline.replace("Most likely: ", ""), f"{d.top_cf:.0%}",
                          certainty.label(d.top_cf) + " confidence")
            else:
                st.info(d.explanation.headline)
            for line in d.advice:
                st.write("• " + line)
            if d.see_doctor_if:
                st.write(f"**See a doctor if:** {d.see_doctor_if}")
        with right:
            st.write("**All possibilities**")
            for did, cf in d.ranked[:5]:
                st.write(kb.diseases[did]["label"])
                st.progress(min(max(cf, 0.0), 1.0), text=f"{cf:.0%}")

        with st.expander("Why this result? (explanation)"):
            e = d.explanation
            for rid, why, cf in e.supporting:
                st.write(f"✅ **{rid}**: {why} (+{cf:.2f})")
            for rid, why, cf in e.against:
                st.write(f"❌ **{rid}**: {why} ({cf:.2f})")
            if d.temperature:
                t = d.temperature
                st.write(f"Fuzzy temperature reading: fever {t['fever']:.2f}, high fever {t['high_fever']:.2f}, "
                         f"severity {t['severity']:.2f}")
        with st.expander("Every rule that fired (forward-chaining trace)"):
            st.dataframe(pd.DataFrame([
                {"pass": f.pass_no, "rule": f.rule.id, "concludes": kb.label(f.rule.then),
                 "because": f.rule.why, "CF": round(f.contribution, 3)}
                for f in d.firings
            ]), hide_index=True, use_container_width=True)

        questions = es.next_questions(d, k=3, skip=skip)
        if questions and d.top_cf < 0.8:
            st.subheader("3. Answer a few more questions (backward chaining)")
            with st.form("followup"):
                answers = {sym: st.radio(text, ["Not sure", "Yes", "No"], horizontal=True, key=f"q_{sym}")
                           for sym, text in questions}
                if st.form_submit_button("Update result"):
                    for sym, ans in answers.items():
                        (yes if ans == "Yes" else no if ans == "No" else skip).add(sym)
                    st.rerun()

# ------------------------------------------------------------------------- how it works
with tab_how:
    st.markdown("""
**Pipeline**

1. **Fuzzy logic** turns a measured temperature or pain score into degrees (for example 103 °F is
   partly "moderate" and partly "high" fever) instead of one hard cut-off.
2. **Forward chaining** starts from your symptoms and fires every matching rule:
   symptoms → syndromes (such as *respiratory*) → disease hypotheses.
3. **Certainty factors (MYCIN)** let several rules support or oppose the same disease,
   including *negative* evidence such as "fever argues against hay fever".
4. **Constraint checks** reject impossible profiles and raise the urgency for red flags,
   young or old age, pregnancy and long-lasting fever. Urgency can only go up.
5. **Backward chaining** picks the unanswered symptom that would best separate the leading diagnoses
   and asks you about it.
6. **Explanation** lists exactly which rules gave the result.
""")

# --------------------------------------------------------------------------- knowledge base
with tab_kb:
    st.write(f"{len(kb.diseases)} conditions, {len(kb.symptoms)} symptoms, {len(kb.rules)} rules.")
    st.caption(kb.meta.get("note", ""))
    st.dataframe(pd.DataFrame([
        {"rule": r.id, "IF": " AND ".join(kb.label(c) for c in r.if_all)
         + (" AND (" + " OR ".join(kb.label(c) for c in r.if_any) + ")" if r.if_any else ""),
         "THEN": kb.label(r.then), "CF": r.cf, "why": r.why}
        for r in kb.rules
    ]), hide_index=True, use_container_width=True)
