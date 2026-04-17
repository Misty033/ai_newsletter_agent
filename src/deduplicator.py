from src.db import is_sent


def remove_duplicates(articles: list) -> list:
    """
    Remove articles that were already sent in a previous run.
    Checks the sent_articles table in PostgreSQL.
    """
    fresh = [a for a in articles if not is_sent(a["link"])]
    removed = len(articles) - len(fresh)
    print(f"[deduplicator] Removed {removed} already-sent articles. {len(fresh)} fresh.")
    return fresh
