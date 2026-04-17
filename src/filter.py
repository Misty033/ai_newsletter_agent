from src.config import AI_KEYWORDS


def is_ai_related(article: dict) -> bool:
    """
    Return True if the article is genuinely AI-related.
    Checks title + summary against the AI keyword list.
    """
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return any(keyword in text for keyword in AI_KEYWORDS)


def filter_ai(articles: list) -> list:
    """
    Filter a list of articles to only those that are AI-related.
    Also drops articles with empty titles or very short summaries.
    """
    filtered = []
    for a in articles:
        if not a.get("title"):
            continue
        if not a.get("link"):
            continue
        if is_ai_related(a):
            filtered.append(a)

    print(f"[filter] {len(filtered)} AI-related articles (from {len(articles)} total)")
    return filtered
