import requests
from src.config import OLLAMA_URL, OLLAMA_MODEL


def summarize(title: str, text: str) -> str:
    """
    Ask Ollama (running locally) to summarize an article in exactly 2 sentences.
    Free. Runs on your machine. No internet or API key needed.

    Falls back to a truncated version of the original summary if Ollama is down.
    """
    prompt = (
        f"Summarize the following AI news article in exactly 2 clear, informative "
        f"sentences. Do not include any preamble — just the 2 sentences.\n\n"
        f"Title: {title}\n"
        f"Content: {text[:600]}"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        summary = response.json().get("response", "").strip()
        return summary if summary else text[:200]
    except Exception as e:
        print(f"[summarizer] Ollama unavailable: {e} — using truncated text")
        return text[:200] + "..."


def add_summaries(articles: list) -> list:
    """Add a 'short_summary' field to each article."""
    print(f"[summarizer] Summarising {len(articles)} articles...")
    for a in articles:
        a["short_summary"] = summarize(a.get("title", ""), a.get("summary", ""))
    return articles
