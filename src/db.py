import psycopg2
import psycopg2.extras
import json
from datetime import datetime, timedelta
from src.config import POSTGRES_CONFIG


def get_conn():
    """Return a new database connection."""
    return psycopg2.connect(**POSTGRES_CONFIG)


def init_db():
    """
    Create all tables if they don't already exist.
    Run this once on startup — safe to call every time (uses IF NOT EXISTS).
    """
    conn = get_conn()
    cur  = conn.cursor()

    # Stores every article that was ever sent — prevents duplicate sends forever.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_articles (
            link        TEXT PRIMARY KEY,
            title       TEXT,
            source      TEXT,
            category    TEXT,
            score       FLOAT,
            sent_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stores recipient preferences so we can personalise digests.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recipients (
            email       TEXT PRIMARY KEY,
            name        TEXT,
            interests   TEXT[],   -- e.g. ARRAY['research','models']
            active      BOOLEAN DEFAULT TRUE,
            joined_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stores thumbs up / down feedback from recipients.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id          SERIAL PRIMARY KEY,
            article_link TEXT NOT NULL,
            recipient_email TEXT NOT NULL,
            vote        SMALLINT NOT NULL,  -- +1 or -1
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stores weekly digest metadata for the archive dashboard.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_digest (
            week_of     DATE PRIMARY KEY,
            theme       TEXT,
            top_links   JSONB,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("[db] Tables initialised.")


# ─── sent_articles ─────────────────────────────────────────────────────────────

def is_sent(link: str) -> bool:
    """Return True if this article link was already sent."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("SELECT 1 FROM sent_articles WHERE link = %s", (link,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists


def mark_sent(article: dict):
    """Save an article as sent so it won't be sent again."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO sent_articles (link, title, source, category, score)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (link) DO NOTHING
    """, (
        article.get("link"),
        article.get("title"),
        article.get("source"),
        article.get("category"),
        article.get("final_score", 0),
    ))
    conn.commit()
    cur.close()
    conn.close()


def get_sent_this_week() -> list:
    """Return all articles sent in the last 7 days (for the weekly digest)."""
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT * FROM sent_articles
        WHERE sent_at >= NOW() - INTERVAL '7 days'
        ORDER BY score DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# ─── recipients ────────────────────────────────────────────────────────────────

def upsert_recipient(email: str, name: str, interests: list):
    """Insert or update a recipient's profile."""
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO recipients (email, name, interests)
        VALUES (%s, %s, %s)
        ON CONFLICT (email) DO UPDATE
            SET name = EXCLUDED.name,
                interests = EXCLUDED.interests
    """, (email, name, interests))
    conn.commit()
    cur.close()
    conn.close()


def get_active_recipients() -> list:
    """Return all active recipients with their interest profiles."""
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM recipients WHERE active = TRUE")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


# ─── feedback ──────────────────────────────────────────────────────────────────

def save_feedback(article_link: str, recipient_email: str, vote: int):
    """
    Save a thumbs up (+1) or thumbs down (-1) for an article.
    Ignores duplicate votes from the same person for the same article.
    """
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO feedback (article_link, recipient_email, vote)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """, (article_link, recipient_email, vote))
    conn.commit()
    cur.close()
    conn.close()


def get_feedback_penalty(article_link: str) -> float:
    """
    Return a penalty score for an article based on past negative feedback.
    Used by the ranker to downweight articles similar to ones people disliked.
    Returns a value between -3 (heavily disliked) and +1 (loved).
    """
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(vote), 0) FROM feedback
        WHERE article_link = %s
    """, (article_link,))
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    # Clamp to range [-3, +1] so a single bad signal doesn't destroy an article
    return max(-3.0, min(1.0, float(total)))


# ─── weekly_digest ─────────────────────────────────────────────────────────────

def save_weekly_digest(week_of: str, theme: str, top_links: list):
    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO weekly_digest (week_of, theme, top_links)
        VALUES (%s, %s, %s)
        ON CONFLICT (week_of) DO UPDATE
            SET theme = EXCLUDED.theme,
                top_links = EXCLUDED.top_links
    """, (week_of, theme, json.dumps(top_links)))
    conn.commit()
    cur.close()
    conn.close()
