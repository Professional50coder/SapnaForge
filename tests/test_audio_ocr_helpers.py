from llm_workflows.audio_text import (
    convert_time_to_srt_format, create_multiline_srt, split_line_by_char_limit,
)
from utils.full_multi_updated2 import detect_languages_in_text, save_results


def test_srt_timestamp_format():
    assert convert_time_to_srt_format(0) == "00:00:00,000"
    assert convert_time_to_srt_format(3661.5) == "01:01:01,500"
    assert convert_time_to_srt_format(59.9996) == "00:01:00,000"  # rounding carries into the next second


def test_split_line_respects_limit():
    lines = split_line_by_char_limit("one two three four five six seven", 12)
    assert all(len(line) <= 12 for line in lines)
    assert " ".join(lines) == "one two three four five six seven"


def test_multiline_srt_file(tmp_path):
    out = tmp_path / "a.srt"
    create_multiline_srt([{"text": "hello world again", "start": 0, "end": 1.25}], str(out), 11)
    assert out.read_text(encoding="utf-8") == "1\n00:00:00,000 --> 00:00:01,250\nhello world\nagain\n\n"


def test_detect_languages():
    assert detect_languages_in_text("hello") == ["Latin_Script"]
    assert detect_languages_in_text("ଓଡ଼ିଆ") == ["Odia"]
    assert detect_languages_in_text("ଓ abc") == ["Odia", "Latin_Script"]
    assert detect_languages_in_text("12345") == ["Unknown"]


def test_save_results_skips_error_pages(tmp_path):
    pages = [
        {"page_number": 1, "full_text": "first"},
        {"page_number": 2, "error": "boom", "has_content": False},
    ]
    save_results(pages, str(tmp_path), "plan")
    txt = (tmp_path / "plan_extracted_text.txt").read_text(encoding="utf-8")
    assert "=== Page 1 ===" in txt and "first" in txt and "Page 2" not in txt
    assert (tmp_path / "plan_complete.json").exists()
