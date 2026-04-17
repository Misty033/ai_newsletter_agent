"""
Archive Dashboard — browse and search all past AI articles.
Built from the data already in PostgreSQL — zero extra scraping.

Run with:
    streamlit run dashboard.py
"""

import streamlit as st
import psycopg2
import psycopg2.extras
import pandas as pd
from src.config import POSTGRES_CONFIG, CATEGORIES

st.set_page_config(page_title="AI News Archive", page_icon="🤖", layout="wide")


@st.cache_resource
def get_conn():
    return psycopg2.connect(**POSTGRES_CONFIG)


def load_articles(category_filter=None, search_query=None, limit=100):
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query  = "SELECT * FROM sent_articles WHERE 1=1"
    params = []

    if category_filter and category_filter != "All":
        query += " AND category = %s"
        params.append(category_filter)

    if search_query:
        query += " AND (title ILIKE %s OR source ILIKE %s)"
        params += [f"%{search_query}%", f"%{search_query}%"]

    query += " ORDER BY sent_at DESC LIMIT %s"
    params.append(limit)

    cur.execute(query, params)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


def load_feedback_summary():
    conn = get_conn()
    cur  = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT article_link, SUM(vote) as net_votes, COUNT(*) as total_votes
        FROM feedback
        GROUP BY article_link
        ORDER BY net_votes DESC
        LIMIT 10
    """)
    rows = cur.fetchall()
    cur.close()
    return [dict(r) for r in rows]


# ─── UI ────────────────────────────────────────────────────────────────────────

st.title("AI News Archive")
st.caption("Browse every article ever sent through your digest.")

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    category = st.selectbox("Category", ["All"] + CATEGORIES)
    search   = st.text_input("Search title / source", "")
    limit    = st.slider("Max articles", 20, 500, 100)

# Main content
articles = load_articles(category, search, limit)

st.markdown(f"**{len(articles)} articles** found")

if articles:
    df = pd.DataFrame(articles)
    df["sent_at"]      = pd.to_datetime(df["sent_at"]).dt.strftime("%b %d %Y")
    df["score"]        = df["score"].round(2)
    df["title_link"]   = df.apply(lambda r: f'<a href="{r["link"]}" target="_blank">{r["title"]}</a>', axis=1)

    st.write(
        df[["sent_at", "title_link", "category", "source", "score"]]
          .rename(columns={
              "sent_at":    "Date",
              "title_link": "Title",
              "category":   "Category",
              "source":     "Source",
              "score":      "Score",
          })
          .to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

# Feedback leaderboard
st.divider()
st.subheader("Most loved articles (feedback)")
feedback = load_feedback_summary()
if feedback:
    for row in feedback[:5]:
        votes = row["net_votes"]
        icon  = "👍" if votes > 0 else "👎"
        st.markdown(f"{icon} **{votes:+d} votes** — [{row['article_link'][:60]}...]({row['article_link']})")
else:
    st.caption("No feedback recorded yet.")
