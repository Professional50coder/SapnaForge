"""API wiring tests. External services (Gemini, Vision, Translate, NewsAPI) are never called."""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import main
import llm_workflows.multilin_structured_output as ml
from llm_workflows.google_translate_json import GoogleTranslateJSONConverter
from routers import pdf_process_api as pdf_api

client = TestClient(main.app)


def test_openapi_lists_all_routes():
    paths = client.get("/openapi.json").json()["paths"]
    for p in ["/process-pdf", "/llm-workflow/llm-analysis", "/llm-workflow/plan-feedback",
              "/translate-structured-output", "/translate-feedbacks", "/chat"]:
        assert p in paths


def test_process_pdf_rejects_malformed_payload():
    assert client.post("/process-pdf", json={"nope": 1}).status_code == 422


@pytest.mark.parametrize("url", ["file:///etc/passwd", "C:/secret.pdf", "ftp://h/x.pdf", "", "/local/path"])
def test_validate_url_rejects_non_http(url):
    with pytest.raises(HTTPException) as exc:
        pdf_api.validate_url(url)
    assert exc.value.status_code == 400


def test_validate_url_accepts_https():
    assert pdf_api.validate_url("https://example.com/plan.pdf")


def test_process_pdf_rejects_local_file_url():
    r = client.post("/process-pdf", json={"url": "file:///etc/passwd", "type": "pdf"})
    assert r.status_code == 400


def test_chat_without_key_reports_it(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    r = client.post("/chat", json={"query": "q", "transcription": "t"})
    assert r.status_code == 200
    assert "GOOGLE_API_KEY" in r.json()["response"]


def test_feedback_without_key_is_500_with_message(monkeypatch):
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    r = client.post("/llm-workflow/plan-feedback", json={"json_data": "plan"})
    assert r.status_code == 500 and "GOOGLE_API_KEY" in r.json()["detail"]


def test_translate_endpoint_with_stub(monkeypatch):
    class Stub:
        def detect_language(self, t):
            return {"language": "en"}

        def translate(self, text, target_language, source_language=None):
            return {"translatedText": text.upper()}

    monkeypatch.setattr(ml, "GoogleTranslateJSONConverter", lambda: GoogleTranslateJSONConverter(client=Stub()))
    r = client.post("/translate-structured-output", json={"structured_output": '{"title": "shop"}', "language": "hindi"})
    assert r.status_code == 200
    assert r.json() == {"translated_output": {"title": "SHOP"}, "language": "hindi"}
