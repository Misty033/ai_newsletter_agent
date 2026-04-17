import requests
from src.config import OLLAMA_URL, OLLAMA_MODEL, CATEGORIES


def categorize(title: str, summary: str) -> str:
    """
    Ask Ollama to classify the article into one of the predefined categories.
    Returns one of: "Model release", "Research paper", "Industry news",
                    "Tools & repos", "Policy & regulation"
    Falls back to "Industry news" if classification fails.
    """
    category_list = "\n".join(f"- {c}" for c in CATEGORIES)
    prompt = (
        f"Classify this AI news article into exactly one of these categories:\n"
        f"{category_list}\n\n"
        f"Title: {title}\n"
        f"Summary: {summary[:300]}\n\n"
        f"Reply with ONLY the category name, nothing else."
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        result = response.json().get("response", "").strip()

        # Match the response to one of the valid categories
        for category in CATEGORIES:
            if category.lower() in result.lower():
                return category

        return "Industry news"  # safe default
    except Exception as e:
        print(f"[categorizer] Error: {e} — defaulting to 'Industry news'")
        return "Industry news"


def add_categories(articles: list) -> list:
    """Add a 'category' field to each article."""
    print(f"[categorizer] Categorising {len(articles)} articles...")
    for a in articles:
        a["category"] = categorize(a.get("title", ""), a.get("summary", ""))
    return articles
