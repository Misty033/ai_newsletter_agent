from datetime import date
from src.config import CATEGORIES, FEEDBACK_BASE_URL
import urllib.parse


# ─── Category colours (inline CSS — safe for email clients) ───────────────────
CATEGORY_COLORS = {
    "Model release":      {"bg": "#EEEDFE", "text": "#3C3489", "border": "#AFA9EC"},
    "Research paper":     {"bg": "#E1F5EE", "text": "#085041", "border": "#5DCAA5"},
    "Industry news":      {"bg": "#FAEEDA", "text": "#633806", "border": "#EF9F27"},
    "Tools & repos":      {"bg": "#E6F1FB", "text": "#0C447C", "border": "#85B7EB"},
    "Policy & regulation":{"bg": "#FAECE7", "text": "#712B13", "border": "#F0997B"},
}


def _category_badge(category: str) -> str:
    c = CATEGORY_COLORS.get(category, {"bg": "#F1EFE8", "text": "#444441", "border": "#B4B2A9"})
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:20px;'
        f'font-size:11px;font-weight:500;background:{c["bg"]};color:{c["text"]};'
        f'border:1px solid {c["border"]};margin-bottom:8px;">{category}</span>'
    )


def _feedback_links(article_link: str, recipient_email: str) -> str:
    """Generate thumbs up / thumbs down links that call the feedback server."""
    enc_link  = urllib.parse.quote(article_link, safe="")
    enc_email = urllib.parse.quote(recipient_email, safe="")

    up_url   = f"{FEEDBACK_BASE_URL}/feedback?link={enc_link}&email={enc_email}&vote=1"
    down_url = f"{FEEDBACK_BASE_URL}/feedback?link={enc_link}&email={enc_email}&vote=-1"

    return (
        f'<span style="font-size:11px;color:#888;">'
        f'Was this useful? '
        f'<a href="{up_url}" style="text-decoration:none;color:#1D9E75;">👍 Yes</a> &nbsp;'
        f'<a href="{down_url}" style="text-decoration:none;color:#D85A30;">👎 No</a>'
        f'</span>'
    )


def _article_card(article: dict, index: int, recipient_email: str) -> str:
    """Render a single article as an HTML card."""
    title    = article.get("title", "No title")
    link     = article.get("link", "#")
    summary  = article.get("short_summary", article.get("summary", "")[:200])
    source   = article.get("source", "")
    category = article.get("category", "Industry news")
    score    = article.get("final_score", 0)

    badge    = _category_badge(category)
    feedback = _feedback_links(link, recipient_email)

    return f"""
    <div style="border:1px solid #e5e5e0;border-radius:10px;padding:18px 20px;
                margin-bottom:14px;background:#ffffff;">
        {badge}
        <div style="font-size:14px;font-weight:500;margin-bottom:6px;">
            <a href="{link}" style="color:#1a1a18;text-decoration:none;">{index}. {title}</a>
        </div>
        <div style="font-size:13px;color:#5f5e5a;line-height:1.6;margin-bottom:10px;">
            {summary}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;
                    font-size:11px;color:#888;">
            <span>
                <a href="{link}" style="color:#185FA5;text-decoration:none;">Read full article →</a>
                &nbsp;&nbsp;Source: {source}
            </span>
            {feedback}
        </div>
    </div>
    """


def _group_by_category(articles: list) -> dict:
    """Group articles by their category, preserving score order within each group."""
    grouped = {c: [] for c in CATEGORIES}
    for a in articles:
        cat = a.get("category", "Industry news")
        if cat in grouped:
            grouped[cat].append(a)
        else:
            grouped["Industry news"].append(a)
    return grouped


# ─── Daily email ───────────────────────────────────────────────────────────────

def format_daily_email(articles: list, recipient: dict) -> tuple[str, str]:
    """
    Build a styled HTML daily digest email personalised for one recipient.

    Personalisation: if the recipient has interests, articles matching those
    categories appear at the top of the email.

    Returns (subject_line, html_body).
    """
    name      = recipient.get("name", "there")
    email     = recipient.get("email", "")
    interests = recipient.get("interests", [])
    today     = date.today().strftime("%B %d, %Y")

    # Sort articles so the recipient's preferred categories come first
    def interest_priority(a):
        cat = a.get("category", "").lower()
        for i, interest in enumerate(interests):
            if interest.lower() in cat.lower():
                return i
        return len(interests)

    sorted_articles = sorted(articles, key=interest_priority)

    # Build article cards
    cards_html = ""
    for i, article in enumerate(sorted_articles, 1):
        cards_html += _article_card(article, i, email)

    subject = f"AI Daily Digest — {today}"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:30px auto;background:#f4f4f0;padding:0 16px 40px;">

    <!-- Header -->
    <div style="background:#1a1a18;border-radius:12px;padding:24px 28px;margin-bottom:20px;">
      <div style="font-size:11px;letter-spacing:0.08em;color:#888;text-transform:uppercase;margin-bottom:6px;">
        AI Daily Digest
      </div>
      <div style="font-size:22px;font-weight:500;color:#ffffff;margin-bottom:4px;">
        {today}
      </div>
      <div style="font-size:13px;color:#aaa;">
        Hi {name} — here are today's top {len(sorted_articles)} AI stories.
      </div>
    </div>

    <!-- Articles -->
    {cards_html}

    <!-- Footer -->
    <div style="text-align:center;font-size:11px;color:#999;margin-top:20px;line-height:1.7;">
      You're receiving this because you subscribed to AI Daily Digest.<br>
      Your feedback (👍 👎) helps improve future digests.<br>
      <a href="{FEEDBACK_BASE_URL}/unsubscribe?email={urllib.parse.quote(email)}"
         style="color:#888;">Unsubscribe</a>
    </div>

  </div>
</body>
</html>
    """
    return subject, html


# ─── Weekly deep-dive email ────────────────────────────────────────────────────

def format_weekly_email(articles: list, theme: str, recipient: dict) -> tuple[str, str]:
    """
    Build the Sunday weekly deep-dive email.
    Includes all top articles from the week, grouped by category,
    plus a 'theme of the week' paragraph at the top.

    Returns (subject_line, html_body).
    """
    name   = recipient.get("name", "there")
    email  = recipient.get("email", "")
    today  = date.today().strftime("%B %d, %Y")

    grouped = _group_by_category(articles)

    sections_html = ""
    for category, cat_articles in grouped.items():
        if not cat_articles:
            continue
        c = CATEGORY_COLORS.get(category, {"bg": "#F1EFE8", "text": "#444441", "border": "#B4B2A9"})
        sections_html += f"""
        <div style="margin-bottom:24px;">
          <div style="font-size:11px;font-weight:500;letter-spacing:0.06em;
                      color:{c["text"]};text-transform:uppercase;margin-bottom:10px;
                      padding-bottom:6px;border-bottom:1px solid {c["border"]};">
            {category}
          </div>
        """
        for i, article in enumerate(cat_articles, 1):
            sections_html += _article_card(article, i, email)
        sections_html += "</div>"

    subject = f"AI Weekly Digest — Week of {today}"

    html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:600px;margin:30px auto;background:#f4f4f0;padding:0 16px 40px;">

    <!-- Header -->
    <div style="background:#1a1a18;border-radius:12px;padding:24px 28px;margin-bottom:20px;">
      <div style="font-size:11px;letter-spacing:0.08em;color:#888;text-transform:uppercase;margin-bottom:6px;">
        AI Weekly Deep-Dive
      </div>
      <div style="font-size:22px;font-weight:500;color:#ffffff;margin-bottom:4px;">
        Week of {today}
      </div>
      <div style="font-size:13px;color:#aaa;">Hi {name} — your Sunday AI roundup.</div>
    </div>

    <!-- Theme of the week -->
    <div style="background:#EEEDFE;border:1px solid #AFA9EC;border-radius:10px;
                padding:16px 20px;margin-bottom:20px;">
      <div style="font-size:11px;font-weight:500;color:#534AB7;
                  text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">
        Theme of the week
      </div>
      <div style="font-size:14px;color:#3C3489;line-height:1.6;">{theme}</div>
    </div>

    <!-- Categorised articles -->
    {sections_html}

    <!-- Footer -->
    <div style="text-align:center;font-size:11px;color:#999;margin-top:20px;line-height:1.7;">
      AI Weekly Digest — every Sunday.<br>
      <a href="{FEEDBACK_BASE_URL}/unsubscribe?email={urllib.parse.quote(email)}"
         style="color:#888;">Unsubscribe</a>
    </div>

  </div>
</body>
</html>
    """
    return subject, html
