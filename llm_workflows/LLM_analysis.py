from typing import Any

import os
import json
import requests
from datetime import datetime, timedelta
from .llm import get_chat_model
from .schemas import BusinessPlanAnalysis
from .text_utils import DEFAULT_KEYWORDS, parse_keywords, format_articles, normalize_kpis

def analyze_business_plan(json_data: Any) -> BusinessPlanAnalysis:
    """
    Analyze business plan JSON data using LLM and return structured BusinessPlanAnalysis output.
    Integrates news summary generated from transcription inside json_data.
    Args:
        json_data: Dictionary containing business plan information to analyze. Must include 'transcribed_text' key.
    Returns:
        BusinessPlanAnalysis: Structured analysis with scores, feedback, and recommendations
    """

    NEWS_API_KEY = os.getenv("NEWS_API_KEY")
    # GEMINI_API_KEY falls back to GOOGLE_API_KEY so one key is enough.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

    def extract_keywords_from_transcription(transcribed_text):
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            prompt = f"""
            Analyze the following transcribed text and extract exactly 5 relevant keywords or topics that would be good for news searching.
            Requirements:
            1. Return only 5 keywords/phrases
            2. Each keyword should be 1-3 words maximum
            3. Focus on technology, business, science, or current affairs topics
            4. Make keywords suitable for news searches
            5. Return as a simple comma-separated list with no other text
            Transcribed Text:
            {transcribed_text}
            Return format: keyword1, keyword2, keyword3, keyword4, keyword5
            """
            response = model.generate_content(prompt)
            keywords_text = response.text.strip()
            return parse_keywords(keywords_text) or DEFAULT_KEYWORDS
        except Exception as e:
            print(f"Error extracting keywords: {e}")
            return list(DEFAULT_KEYWORDS)

    def fetch_news_articles(query, num=5):
        if not NEWS_API_KEY:
            return None
        try:
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': query,
                'apiKey': NEWS_API_KEY,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': num,
                'from': from_date
            }
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching news for {query}: {e}")
            return None

    def prepare_news_data(topics):
        all_articles = []
        for topic in topics:
            news_data = fetch_news_articles(topic)
            if news_data and news_data.get('status') == 'ok':
                articles = news_data.get('articles', [])
                for article in articles:
                    title = article.get('title', 'No title')
                    description = article.get('description', 'No description')
                    url = article.get('url', 'No URL')
                    published_at = article.get('publishedAt', 'Unknown date')
                    source = article.get('source', {}).get('name', 'Unknown source')
                    if title != 'No title' and description != 'No description':
                        article_info = {
                            'topic': topic,
                            'title': title,
                            'description': description,
                            'url': url,
                            'published_at': published_at,
                            'source': source
                        }
                        all_articles.append(article_info)
        return all_articles

    def analyze_with_gemini(articles_text, topics):
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            topics_list = ", ".join(topics)
            prompt = f"""
            Please analyze the following recent news articles and create a comprehensive summary report.
            Instructions:
            1. Group the articles by these topics: {topics_list}
            2. For each topic, provide a summary paragraph highlighting the key developments and trends
            3. Include important details, statistics, and implications mentioned in the articles
            4. Write in a clear, professional news summary format using plain text only
            5. Do not use any markdown formatting, asterisks, or special characters for emphasis
            6. Include relevant source citations where appropriate
            7. End with a brief overall outlook section
            8. Use proper paragraph breaks and clear section headings
            Here are the articles:
            {articles_text}
            Please provide a well-structured summary in clean paragraph format without any formatting symbols.
            """
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print("Error analyzing with Gemini:", e)
            return None

    # Accept either a dict with 'json_data' or a direct string as input
    if isinstance(json_data, dict) and "json_data" in json_data:
        transcribed_text = str(json_data["json_data"])
    elif isinstance(json_data, str):
        transcribed_text = json_data
    else:
        # Any other JSON (e.g. the structured plan object itself) is analysed as serialised text.
        transcribed_text = json.dumps(json_data, ensure_ascii=False)

    llm = get_chat_model(temperature=0)  # fail fast if GOOGLE_API_KEY is missing

    # News grounding is best-effort: without NEWS_API_KEY (or on any failure) the
    # analysis still runs, just without a news summary.
    news_summary = None
    if NEWS_API_KEY:
        keywords = extract_keywords_from_transcription(transcribed_text)
        articles = prepare_news_data(keywords)
        if articles:
            news_summary = analyze_with_gemini(format_articles(articles), keywords)

    structured_llm = llm.with_structured_output(BusinessPlanAnalysis)

    # For this payload, just pass the full_text and news_summary
    prompt = f"""
    You are an expert business plan analyst. Analyze the following business plan text and the news summary, and provide a comprehensive analysis according to the BusinessPlanAnalysis schema.

    Evaluate the business plan across these dimensions:
    - Problem identification and market opportunity (0-5 scale)
    - Market understanding and sizing (0-5 scale)
    - Value proposition clarity (0-5 scale)
    - Business model viability (0-5 scale)
    - Team strength and capabilities (0-5 scale)
    - Traction and validation evidence (0-5 scale)
    - Funding readiness (0-5 scale)

    Provide:
    - Specific strengths and weaknesses
    - Prioritized action items for improvement
    - Red flags or major concerns
    - Overall risk assessment
    - Overall confidence in the plan (0.0-1.0)

    Business Plan Text:
    {transcribed_text}

    News Summary (from latest news articles based on transcription):
    {news_summary or "No news context available."}

    Please provide a thorough analysis structured according to the BusinessPlanAnalysis schema.
    """

    response = structured_llm.invoke(prompt)
    data = response if isinstance(response, dict) else response.dict() if hasattr(response, 'dict') else response
    kpis = normalize_kpis(data.get('extracted_kpis', []))
    data['extracted_kpis'] = kpis
    return BusinessPlanAnalysis(**data)
