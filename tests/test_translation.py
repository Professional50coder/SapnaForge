from llm_workflows.google_translate_json import GoogleTranslateJSONConverter as Conv


class StubClient:
    """Stands in for google.cloud.translate_v2.Client; no network."""

    def __init__(self, detected="en"):
        self.detected = detected
        self.calls = []

    def detect_language(self, text):
        return {"language": self.detected}

    def translate(self, text, target_language, source_language=None):
        self.calls.append((text, target_language))
        return {"translatedText": f"[{target_language}] {text}"}


def test_language_names_and_codes_resolve():
    assert Conv.resolve_language_code("Hindi") == "hi"
    assert Conv.resolve_language_code(" ODIA ") == "or"
    assert Conv.resolve_language_code("hi") == "hi"
    assert Conv.resolve_language_code("pt") == "pt"  # unknown codes pass through


def test_translates_every_string_and_keeps_structure():
    conv = Conv(client=StubClient())
    data = {"title": "Shop", "scores": [1, 2], "tags": ["a", "b"], "nested": {"x": "y", "none": None, "empty": ""}}
    out = conv.translate_json_content(data, "hindi")
    assert out["title"] == "[hi] Shop"
    assert out["tags"] == ["[hi] a", "[hi] b"]
    assert out["nested"]["x"] == "[hi] y"
    assert out["scores"] == [1, 2]
    assert out["nested"]["none"] is None and out["nested"]["empty"] == ""


def test_same_language_by_name_skips_translation():
    # Regression: the detected code "hi" was compared with the raw name "hindi",
    # so already-Hindi content was always re-translated.
    stub = StubClient(detected="hi")
    out = Conv(client=stub).translate_json_content({"title": "namaste"}, "Hindi")
    assert out == {"title": "namaste"}
    assert stub.calls == []


def test_translation_failure_returns_original_text():
    class Broken(StubClient):
        def translate(self, *a, **k):
            raise RuntimeError("quota")

    out = Conv(client=Broken()).translate_json_content({"a": "hello"}, "hi")
    assert out == {"a": "hello"}
