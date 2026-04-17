"""
Daily AI News Digest DAG
Runs every morning at 8 AM.

Pipeline:
  collect → filter → rank → deduplicate → summarise → categorise → send → save
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.db          import init_db, mark_sent, upsert_recipient
from src.collector   import fetch_all
from src.filter      import filter_ai
from src.ranker      import rank_articles
from src.deduplicator import remove_duplicates
from src.summarizer  import add_summaries
from src.categorizer import add_categories
from src.formatter   import format_daily_email
from src.emailer     import send_to_all
from src.config      import RECIPIENTS, DAILY_TOP_N


def setup(**context):
    """Initialise DB and sync recipients table from config."""
    init_db()
    for r in RECIPIENTS:
        upsert_recipient(r["email"], r["name"], r["interests"])
    print(f"[DAG] Setup complete. {len(RECIPIENTS)} recipients registered.")


def collect(**context):
    articles = fetch_all()
    context["ti"].xcom_push(key="articles", value=articles)


def filter_step(**context):
    articles = context["ti"].xcom_pull(key="articles", task_ids="collect")
    filtered = filter_ai(articles)
    context["ti"].xcom_push(key="articles", value=filtered)


def rank_step(**context):
    articles = context["ti"].xcom_pull(key="articles", task_ids="filter_step")
    ranked   = rank_articles(articles, use_llm=True)
    context["ti"].xcom_push(key="articles", value=ranked)


def deduplicate_step(**context):
    articles = context["ti"].xcom_pull(key="articles", task_ids="rank_step")
    fresh    = remove_duplicates(articles)
    context["ti"].xcom_push(key="articles", value=fresh)


def select_top(**context):
    articles = context["ti"].xcom_pull(key="articles", task_ids="deduplicate_step")
    top      = articles[:DAILY_TOP_N]
    if not top:
        raise ValueError("[DAG] No articles to send today — pipeline stopped.")
    print(f"[DAG] Selected top {len(top)} articles.")
    context["ti"].xcom_push(key="articles", value=top)


def summarise_step(**context):
    articles    = context["ti"].xcom_pull(key="articles", task_ids="select_top")
    summarised  = add_summaries(articles)
    context["ti"].xcom_push(key="articles", value=summarised)


def categorise_step(**context):
    articles    = context["ti"].xcom_pull(key="articles", task_ids="summarise_step")
    categorised = add_categories(articles)
    context["ti"].xcom_push(key="articles", value=categorised)


def send_step(**context):
    articles   = context["ti"].xcom_pull(key="articles", task_ids="categorise_step")
    recipients = RECIPIENTS  # in production, fetch from DB: get_active_recipients()
    send_to_all(articles, recipients, format_daily_email)


def save_step(**context):
    articles = context["ti"].xcom_pull(key="articles", task_ids="categorise_step")
    for a in articles:
        mark_sent(a)
    print(f"[DAG] Marked {len(articles)} articles as sent.")


# ─── DAG definition ────────────────────────────────────────────────────────────

default_args = {
    "owner":            "ai-news-agent",
    "retries":          1,
    "email_on_failure": True,
    "email":            ["202418033@dau.ac.in"],  # alert if pipeline fails
}

with DAG(
    dag_id          = "ai_news_daily",
    description     = "Daily AI news digest pipeline",
    start_date      = datetime(2024, 1, 1),
    schedule_interval = "0 8 * * *",   # Every day at 8:00 AM
    catchup         = False,
    default_args    = default_args,
    tags            = ["ai-news", "daily"],
) as dag:

    t_setup       = PythonOperator(task_id="setup",           python_callable=setup)
    t_collect     = PythonOperator(task_id="collect",         python_callable=collect)
    t_filter      = PythonOperator(task_id="filter_step",     python_callable=filter_step)
    t_rank        = PythonOperator(task_id="rank_step",       python_callable=rank_step)
    t_dedup       = PythonOperator(task_id="deduplicate_step",python_callable=deduplicate_step)
    t_top         = PythonOperator(task_id="select_top",      python_callable=select_top)
    t_summarise   = PythonOperator(task_id="summarise_step",  python_callable=summarise_step)
    t_categorise  = PythonOperator(task_id="categorise_step", python_callable=categorise_step)
    t_send        = PythonOperator(task_id="send_step",       python_callable=send_step)
    t_save        = PythonOperator(task_id="save_step",       python_callable=save_step)

    # Linear pipeline — each step depends on the previous one
    t_setup >> t_collect >> t_filter >> t_rank >> t_dedup >> t_top >> t_summarise >> t_categorise >> t_send >> t_save
