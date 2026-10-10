"""Pure helpers (no network, no LLM) used by the analysis pipeline."""
from typing import Any, Dict, List

from .schemas import BusinessPlanDetails

DEFAULT_KEYWORDS = ["artificial intelligence", "technology", "business", "innovation", "market trends"]


def parse_keywords(text: str, limit: int = 5) -> List[str]:
    """Split a comma-separated LLM reply into at most `limit` clean keywords."""
    keywords = [k.strip().strip('"\'') for k in (text or "").split(",")]
    return [k for k in keywords if k][:limit]


def format_articles(articles: List[Dict[str, str]]) -> str:
    """Render NewsAPI article dicts as the plain-text block fed to the summariser."""
    if not articles:
        return "No articles found."
    out = "Recent news articles for analysis:\n\n"
    for i, a in enumerate(articles, 1):
        out += f"Article {i}:\n"
        out += f"Topic: {a['topic'].title()}\n"
        out += f"Title: {a['title']}\n"
        out += f"Description: {a['description']}\n"
        out += f"Source: {a['source']}\n"
        out += f"Published: {a['published_at']}\n"
        out += f"URL: {a['url']}\n"
        out += "-" * 80 + "\n\n"
    return out


def normalize_kpis(kpis: Any) -> List[str]:
    """Coerce the model's `extracted_kpis` (list, dict, str or None) into a list of strings."""
    if isinstance(kpis, dict):
        return [str(v) for v in kpis.values()]
    if isinstance(kpis, str):
        return [kpis]
    if isinstance(kpis, list):
        return [str(x) for x in kpis]
    return []


# The eight narrative sections of BusinessPlanDetails, each paired with its 0-10 score field.
PLAN_SECTIONS = [
    "problem_and_customer",
    "solution_and_features",
    "market_and_competitors",
    "channels_and_revenue",
    "operations_and_team",
    "traction_and_funding",
    "risks_and_mitigation",
    "social_and_environmental_impact",
]


def section_coverage(plan: BusinessPlanDetails) -> Dict[str, Any]:
    """Report which of the eight plan sections are filled in and the mean of any scores present.

    This is a plain completeness check on the structured output, not a quality judgement.
    """
    filled = [s for s in PLAN_SECTIONS if (getattr(plan, s) or "").strip()]
    missing = [s for s in PLAN_SECTIONS if s not in filled]
    scores = [getattr(plan, f"{s}_score") for s in PLAN_SECTIONS if getattr(plan, f"{s}_score") is not None]
    return {
        "filled": filled,
        "missing": missing,
        "filled_count": len(filled),
        "total": len(PLAN_SECTIONS),
        "mean_score": round(sum(scores) / len(scores), 2) if scores else None,
    }
