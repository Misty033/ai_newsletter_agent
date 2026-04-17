import requests
from collections import defaultdict
from src.config import (
    IMPORTANT_WORDS, BIG_PLAYERS, OLLAMA_URL, OLLAMA_MODEL,
    VELOCITY_SOURCES_THRESHOLD, VELOCITY_MULTIPLIER, MIN_SCORE_TO_SEND
)
from src.db import get_feedback_penalty


# ─── Layer 1: Keyword heuristic score ──────────────────────────────────────────

def keyword_score(article: dict) -> float:
    """
    Fast, cheap heuristic score based on presence of important words.
    Returns a score between 0 and ~15.
    """
    text  = (article.get("title", "") + " " + article.get("summary", "")).lower()
    score = 0.0

    for word in IMPORTANT_WORDS:
        if word in text:
            score += 2

    for player in BIG_PLAYERS:
        if player in text:
            score += 3

    return score


# ─── Layer 2: LLM importance score ─────────────────────────────────────────────

def llm_score(article: dict) -> float:
    """
    Ask Ollama to rate the article's importance from 1–10.
    This catches nuance that keyword matching misses — e.g. understanding
    that 'GPT-5 cancelled' is far more significant than 'GPT mentioned in blog'.

    Falls back to 5.0 if Ollama is unavailable.
    """
    prompt = (
        f"You are an AI news editor. Rate this article's importance to the "
        f"AI/ML field on a scale from 1 to 10. Return ONLY a single integer.\n\n"
        f"Title: {article.get('title', '')}\n"
        f"Summary: {article.get('summary', '')[:300]}"
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30,
        )
        text = response.json().get("response", "5").strip()
        # Extract the first integer found in the response
        for token in text.split():
            if token.isdigit():
                return float(min(10, max(1, int(token))))
        return 5.0
    except Exception as e:
        print(f"[ranker] LLM score failed: {e} — using 5.0")
        return 5.0


# ─── Layer 3: Velocity detection ───────────────────────────────────────────────

def detect_velocity(articles: list) -> dict:
    """
    Find articles that cover the same story across multiple sources.
    Returns a dict mapping article link → velocity multiplier.

    Method: compare title keywords. If 4+ key words overlap between two
    articles from different sources, they're likely the same story.
    """
    def key_words(title: str) -> set:
        stop = {"the", "a", "an", "in", "of", "to", "is", "for", "and", "on",
                "with", "new", "ai", "how"}
        return {w.lower() for w in title.split() if len(w) > 3 and w.lower() not in stop}

    # Build story clusters — group articles that share 4+ title keywords
    clusters  = defaultdict(list)  # article_link → list of article_links in same story
    links     = [a["link"] for a in articles]
    kw_map    = {a["link"]: key_words(a.get("title", "")) for a in articles}

    for i, a in enumerate(articles):
        for j, b in enumerate(articles):
            if i >= j:
                continue
            if a.get("source") == b.get("source"):
                continue  # same source doesn't count
            overlap = len(kw_map[a["link"]] & kw_map[b["link"]])
            if overlap >= 4:
                clusters[a["link"]].append(b["link"])
                clusters[b["link"]].append(a["link"])

    # Build multiplier map
    multipliers = {}
    for a in articles:
        link         = a["link"]
        source_count = len(set(clusters.get(link, []))) + 1  # +1 for itself
        if source_count >= VELOCITY_SOURCES_THRESHOLD:
            multipliers[link] = VELOCITY_MULTIPLIER
            print(f"[ranker] Velocity hit: '{a['title'][:50]}' — {source_count} sources")
        else:
            multipliers[link] = 1.0

    return multipliers


# ─── Combined scorer ───────────────────────────────────────────────────────────

def rank_articles(articles: list, use_llm: bool = True) -> list:
    """
    Score every article using all three layers, then sort highest first.

    Final score = (keyword_score + llm_score) × source_weight × velocity_multiplier + feedback_penalty
    """
    print(f"[ranker] Scoring {len(articles)} articles...")

    velocity_map = detect_velocity(articles)

    scored = []
    for a in articles:
        k_score   = keyword_score(a)
        l_score   = llm_score(a) if use_llm else 5.0
        weight    = a.get("weight", 1.0)
        velocity  = velocity_map.get(a["link"], 1.0)
        feedback  = get_feedback_penalty(a["link"])  # +1 loved, -3 hated

        final = (k_score + l_score) * weight * velocity + feedback

        a["keyword_score"] = round(k_score, 2)
        a["llm_score"]     = round(l_score, 2)
        a["velocity"]      = velocity
        a["feedback"]      = feedback
        a["final_score"]   = round(final, 2)

        if final >= MIN_SCORE_TO_SEND:
            scored.append(a)

    ranked = sorted(scored, key=lambda x: x["final_score"], reverse=True)
    print(f"[ranker] {len(ranked)} articles above score threshold {MIN_SCORE_TO_SEND}")
    return ranked
