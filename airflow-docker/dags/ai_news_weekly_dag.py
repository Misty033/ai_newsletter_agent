"""
Weekly AI Deep-Dive DAG — runs every Sunday at 9 AM.
Pulls the week's best articles from PostgreSQL (already scored and saved),
generates a 'theme of the week' paragraph via Ollama, and sends a longer digest.
"""

from datetime import datetime, date
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
from src.db        import get_sent_this_week, save_weekly_digest
from src.formatter import format_weekly_email
from src.emailer   import send_to_all
from src.config    import RECIPIENTS, WEEKLY_TOP_N, OLLAMA_URL, OLLAMA_MODEL


def generate_theme(articles: list) -> str:
    """
    Ask Ollama to synthesise a 2–3 sentence 'theme of the week' paragraph
    based on the titles of this week's top stories.
    """
    titles = "\n".join(f"- {a.get('title', '')}" for a in articles[:WEEKLY_TOP_N])
    prompt = (
        f"You are an AI analyst. Based on these top AI news headlines from this week, "
        f"write a 2–3 sentence paragraph describing the major theme or trend "
        f"in the AI field this week. Be insightful, not just descriptive.\n\n"
        f"Headlines:\n{titles}\n\nTheme paragraph:"
    )
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=60,
        )
        return response.json().get("response", "").strip()
    except Exception as e:
        print(f"[weekly] Theme generation failed: {e}")
        return "This week saw significant developments across AI research and industry."


def build_weekly_digest(**context):
    """Fetch week's articles, generate theme, push to XCom."""
    week_articles = get_sent_this_week()

    if not week_articles:
        print("[weekly] No articles found this week. Skipping.")
        context["ti"].xcom_push(key="skip", value=True)
        return

    # Convert DB rows to article dicts (DB stores them from daily runs)
    # We use the already-saved data — no re-scraping needed
    top = sorted(week_articles, key=lambda x: x.get("score", 0), reverse=True)[:WEEKLY_TOP_N]

    # Add placeholder fields needed by the formatter
    for a in top:
        a.setdefault("short_summary", a.get("title", ""))
        a.setdefault("source", a.get("source", ""))
        a.setdefault("category", a.get("category", "Industry news"))

    theme = generate_theme(top)
    print(f"[weekly] Theme: {theme[:80]}...")

    context["ti"].xcom_push(key="articles", value=top)
    context["ti"].xcom_push(key="theme",    value=theme)
    context["ti"].xcom_push(key="skip",     value=False)


def send_weekly(**context):
    skip = context["ti"].xcom_pull(key="skip", task_ids="build_weekly_digest")
    if skip:
        print("[weekly] Skipping — no articles this week.")
        return

    articles   = context["ti"].xcom_pull(key="articles", task_ids="build_weekly_digest")
    theme      = context["ti"].xcom_pull(key="theme",    task_ids="build_weekly_digest")
    recipients = RECIPIENTS

    send_to_all(articles, recipients, format_weekly_email, theme=theme)


def save_weekly(**context):
    skip = context["ti"].xcom_pull(key="skip", task_ids="build_weekly_digest")
    if skip:
        return
    articles = context["ti"].xcom_pull(key="articles", task_ids="build_weekly_digest")
    theme    = context["ti"].xcom_pull(key="theme",    task_ids="build_weekly_digest")
    top_links = [{"title": a.get("title"), "link": a.get("link")} for a in articles]
    save_weekly_digest(str(date.today()), theme, top_links)
    print(f"[weekly] Saved weekly digest to DB.")


# ─── DAG definition ────────────────────────────────────────────────────────────

default_args = {
    "owner":   "ai-news-agent",
    "retries": 1,
}

with DAG(
    dag_id            = "ai_news_weekly",
    description       = "Sunday AI deep-dive digest",
    start_date        = datetime(2024, 1, 1),
    schedule_interval = "0 9 * * 0",   # Every Sunday at 9:00 AM
    catchup           = False,
    default_args      = default_args,
    tags              = ["ai-news", "weekly"],
) as dag:

    t_build = PythonOperator(task_id="build_weekly_digest", python_callable=build_weekly_digest)
    t_send  = PythonOperator(task_id="send_weekly",         python_callable=send_weekly)
    t_save  = PythonOperator(task_id="save_weekly",         python_callable=save_weekly)

    t_build >> t_send >> t_save
