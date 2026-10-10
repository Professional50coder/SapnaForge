import pytest
from pydantic import ValidationError

from llm_workflows.schemas import BusinessPlanDetails
from llm_workflows.text_utils import (
    PLAN_SECTIONS, format_articles, normalize_kpis, parse_keywords, section_coverage,
)


def test_parse_keywords_trims_and_limits():
    assert parse_keywords("a, b ,c,d,e,f,g") == ["a", "b", "c", "d", "e"]
    assert parse_keywords('"solar", ,  "welding"') == ["solar", "welding"]
    assert parse_keywords("") == []


def test_format_articles_empty_and_filled():
    assert format_articles([]) == "No articles found."
    text = format_articles([{
        "topic": "metal work", "title": "T", "description": "D",
        "source": "S", "published_at": "2025-01-01", "url": "http://x",
    }])
    assert "Article 1:" in text and "Topic: Metal Work" in text and "URL: http://x" in text


@pytest.mark.parametrize("raw,expected", [
    (["a", 1], ["a", "1"]),
    ({"k": "v", "n": 2}, ["v", "2"]),
    ("single", ["single"]),
    (None, []),
])
def test_normalize_kpis(raw, expected):
    assert normalize_kpis(raw) == expected


def test_scores_are_range_checked():
    BusinessPlanDetails(problem_and_customer_score=10)
    with pytest.raises(ValidationError):
        BusinessPlanDetails(problem_and_customer_score=11)


def test_section_coverage():
    plan = BusinessPlanDetails(
        problem_and_customer="p", problem_and_customer_score=8,
        solution_and_features="s", solution_and_features_score=6,
        risks_and_mitigation="   ",
    )
    cov = section_coverage(plan)
    assert cov["filled"] == ["problem_and_customer", "solution_and_features"]
    assert cov["total"] == len(PLAN_SECTIONS) == 8
    assert "risks_and_mitigation" in cov["missing"]  # whitespace-only counts as missing
    assert cov["mean_score"] == 7.0
    assert section_coverage(BusinessPlanDetails())["mean_score"] is None
