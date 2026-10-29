"""Route regressions without loading trained models or optional parsers."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest


@pytest.fixture
def web_app(monkeypatch):
    # Isolate external analysis dependencies; exercise the real Flask route
    # and result template, without requiring model artifacts or network access.
    dependencies = {
        "model.predict": ["predict"],
        "explainability.shap_explainer": ["get_top_shap_words"],
        "utils.scraper": ["scrape_job_url"],
        "utils.pdf_parser": ["extract_text_from_pdf", "save_uploaded_pdf"],
        "utils.contact_checker": ["check_contact_info"],
        "utils.keyword_analyzer": ["analyze_keywords"],
        "utils.job_validator": ["is_job_posting"],
    }
    for name, functions in dependencies.items():
        module = ModuleType(name)
        for function in functions:
            setattr(module, function, Mock())
        monkeypatch.setitem(sys.modules, name, module)

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("verifid_app_test", root / "app.py")
    module = importlib.util.module_from_spec(spec)
    # app.py adjusts sys.path when imported; restore it after this test.
    monkeypatch.setattr(sys, "path", sys.path.copy())
    spec.loader.exec_module(module)
    module.app.config.update(TESTING=True, SECRET_KEY="test-only-secret")
    module.predict.return_value = {
        "risk_label": "Safe", "final_score": 0.1, "ml_score": 0.1,
        "phrase_score": 0.0, "salary": {"risk_score": 0.0, "reason": ""},
        "lr_prob": 0.1, "nb_prob": 0.1, "suspicious_phrases": [],
    }
    module.check_contact_info.return_value = {"risk_score": 0.0, "flags": []}
    module.analyze_keywords.return_value = {
        "risk_score": 0.0, "total_words": 3, "top_word": "engineer",
        "top_density": 10, "is_stuffed": False,
        "urgency_keywords": [], "money_keywords": [], "vague_keywords": [],
    }
    return module


@pytest.mark.parametrize("text, expected", [
    ('Engineer <script>alert("xss")</script>',
     'Engineer &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'),
    ('Engineer <img src=x onerror=alert(1)>',
     'Engineer &lt;img src=x onerror=alert(1)&gt;'),
    ('Research & development: "Python"',
     'Research &amp; development: &quot;Python&quot;'),
])
def test_explanation_failure_renders_job_text_as_text(web_app, text, expected):
    web_app.get_top_shap_words.side_effect = RuntimeError("Explanation unavailable")
    with web_app.app.test_client() as client:
        with client.session_transaction() as session:
            session["pending_text"] = text
            session["pending_source"] = "Text input"
        response = client.get("/process")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert f'<div class="shap-box">{expected}</div>' in body
    assert text not in body
    web_app.predict.assert_called_once_with(text)


def test_successful_explanation_preserves_highlight_markup(web_app):
    highlighted = '<span class="shap-real">Engineer</span>'
    web_app.get_top_shap_words.return_value = {
        "html": highlighted, "fake_words": [], "real_words": [],
    }
    with web_app.app.test_client() as client:
        with client.session_transaction() as session:
            session["pending_text"] = "Engineer"
        response = client.get("/process")

    assert response.status_code == 200
    assert f'<div class="shap-box">{highlighted}</div>' in response.get_data(as_text=True)
