import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "app.py")


def run_app():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_app_starts_without_error():
    at = run_app()
    assert not at.exception
    assert at.title[0].value.startswith("🩺")


def test_flu_like_symptoms_give_a_result():
    at = run_app()
    at.multiselect(key="sel_General").set_value(["fever", "chills", "body_aches"])
    at.multiselect(key="sel_Respiratory").set_value(["cough"])
    at.button[0].click().run()
    assert not at.exception
    assert any("Influenza" in m.label for m in at.metric)


def test_red_flag_shows_urgent_banner():
    at = run_app()
    at.multiselect(key="sel_Respiratory").set_value(["chest_pain", "shortness_of_breath"])
    at.button[0].click().run()
    assert not at.exception
    assert any("urgent" in e.value.lower() for e in at.error)


def test_invalid_profile_is_reported():
    at = run_app()
    at.sidebar.selectbox[0].set_value("female")
    at.sidebar.checkbox[0].set_value(True)     # pregnant
    at.sidebar.number_input[0].set_value(5)    # age 5
    at.multiselect(key="sel_Respiratory").set_value(["cough"])
    at.button[0].click().run()
    assert any("not plausible" in e.value for e in at.error)


def test_demo_link_prefills_and_runs():
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["demo"] = "flu"
    at.run()
    assert not at.exception
    assert any("Influenza" in m.label for m in at.metric)
