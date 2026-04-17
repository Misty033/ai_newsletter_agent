import feedparser
import requests
from bs4 import BeautifulSoup
from src.config import RSS_FEEDS, ARXIV_CATEGORIES, ARXIV_MAX_RESULTS, REDDIT_SUBS, REDDIT_MIN_UPVOTES


# ─── RSS ───────────────────────────────────────────────────────────────────────

def fetch_rss() -> list:
    """Fetch articles from all configured RSS feeds."""
    articles = []

    for feed_cfg in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:15]:  # max 15 per feed
                articles.append({
                    "title":   entry.get("title", "").strip(),
                    "link":    entry.get("link", "").strip(),
                    "summary": BeautifulSoup(entry.get("summary", ""), "lxml").get_text()[:500],
                    "source":  feed_cfg["name"],
                    "weight":  feed_cfg["weight"],
                    "type":    "rss",
                })
        except Exception as e:
            print(f"[collector] RSS error ({feed_cfg['name']}): {e}")

    print(f"[collector] RSS: fetched {len(articles)} articles")
    return articles


# ─── arXiv ─────────────────────────────────────────────────────────────────────

def fetch_arxiv() -> list:
    """
    Pull recent AI papers from arXiv using their public API.
    No authentication required.
    """
    articles = []
    base_url = "http://export.arxiv.org/api/query"

    for category in ARXIV_CATEGORIES:
        try:
            params = {
                "search_query": f"cat:{category}",
                "sortBy":       "submittedDate",
                "sortOrder":    "descending",
                "max_results":  ARXIV_MAX_RESULTS,
            }
            response = requests.get(base_url, params=params, timeout=15)
            soup     = BeautifulSoup(response.text, "lxml-xml")

            for entry in soup.find_all("entry"):
                title   = entry.find("title").get_text(strip=True)
                link    = entry.find("id").get_text(strip=True)
                summary = entry.find("summary").get_text(strip=True)[:500]

                articles.append({
                    "title":   title,
                    "link":    link,
                    "summary": summary,
                    "source":  f"arXiv ({category})",
                    "weight":  1.5,  # arXiv = credible, primary source
                    "type":    "arxiv",
                })
        except Exception as e:
            print(f"[collector] arXiv error ({category}): {e}")

    print(f"[collector] arXiv: fetched {len(articles)} papers")
    return articles


# ─── Reddit ────────────────────────────────────────────────────────────────────

def fetch_reddit() -> list:
    """
    Pull top posts from AI subreddits using Reddit's public JSON API.
    No API key required — Reddit exposes .json endpoints publicly.
    """
    articles = []
    headers  = {"User-Agent": "ai-news-digest/1.0"}

    for sub in REDDIT_SUBS:
        try:
            url      = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
            response = requests.get(url, headers=headers, timeout=15)
            data     = response.json()

            for post in data["data"]["children"]:
                p = post["data"]
                if p.get("ups", 0) < REDDIT_MIN_UPVOTES:
                    continue
                if p.get("is_self") and not p.get("selftext"):
                    continue  # skip empty text posts

                articles.append({
                    "title":   p.get("title", "").strip(),
                    "link":    f"https://reddit.com{p.get('permalink', '')}",
                    "summary": p.get("selftext", p.get("url", ""))[:500],
                    "source":  f"Reddit r/{sub}",
                    "weight":  1.0,
                    "type":    "reddit",
                    "upvotes": p.get("ups", 0),
                })
        except Exception as e:
            print(f"[collector] Reddit error (r/{sub}): {e}")

    print(f"[collector] Reddit: fetched {len(articles)} posts")
    return articles


# ─── GitHub trending ───────────────────────────────────────────────────────────

def fetch_github_trending() -> list:
    """
    Scrape GitHub's trending page for AI/ML repositories.
    Filters by relevant topics. No API key needed.
    """
    articles = []
    ai_terms = ["llm", "ai", "ml", "gpt", "neural", "diffusion", "nlp",
                 "machine-learning", "deep-learning", "transformer", "llama",
                 "stable-diffusion", "chatbot", "embedding", "rag"]

    try:
        headers  = {"User-Agent": "ai-news-digest/1.0"}
        response = requests.get("https://github.com/trending?since=daily", headers=headers, timeout=15)
        soup     = BeautifulSoup(response.text, "lxml")

        for repo in soup.select("article.Box-row"):
            name_tag = repo.select_one("h2 a")
            desc_tag = repo.select_one("p")
            stars_tag= repo.select_one("span.d-inline-block.float-sm-right")

            if not name_tag:
                continue

            repo_name = name_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
            desc      = desc_tag.get_text(strip=True) if desc_tag else ""
            stars     = stars_tag.get_text(strip=True) if stars_tag else "0"

            # Only include repos that look AI-related
            combined = (repo_name + " " + desc).lower()
            if not any(term in combined for term in ai_terms):
                continue

            articles.append({
                "title":   f"[GitHub] {repo_name} — {desc[:80]}",
                "link":    f"https://github.com/{repo_name.lstrip('/')}",
                "summary": f"Trending GitHub repository. {desc} Stars today: {stars}",
                "source":  "GitHub Trending",
                "weight":  1.1,
                "type":    "github",
            })

    except Exception as e:
        print(f"[collector] GitHub error: {e}")

    print(f"[collector] GitHub: fetched {len(articles)} repos")
    return articles


# ─── Main collector ────────────────────────────────────────────────────────────

def fetch_all() -> list:
    """Run all collectors and return a combined, deduplicated list of articles."""
    all_articles = []
    all_articles += fetch_rss()
    all_articles += fetch_arxiv()
    all_articles += fetch_reddit()
    all_articles += fetch_github_trending()

    # Deduplicate by link (same URL from different sources)
    seen  = set()
    deduped = []
    for a in all_articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            deduped.append(a)

    print(f"[collector] Total unique articles collected: {len(deduped)}")
    return deduped
