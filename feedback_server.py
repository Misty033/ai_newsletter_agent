"""
Feedback server — runs as a separate long-running process.
Friends click thumbs up / down links in their email → this server records the vote.

Run it with:
    python feedback_server.py

Keep it running in the background (use screen, tmux, or a systemd service).
It needs to be reachable at FEEDBACK_BASE_URL from your friends' email clients.
For local testing, use ngrok to expose it: ngrok http 5050
"""

from flask import Flask, request, jsonify
from src.db import save_feedback, init_db

app = Flask(__name__)


@app.route("/feedback")
def feedback():
    """
    Called when a recipient clicks 👍 or 👎 in their email.

    Query params:
        link  — the article URL
        email — the recipient's email
        vote  — +1 (thumbs up) or -1 (thumbs down)
    """
    link  = request.args.get("link", "")
    email = request.args.get("email", "")
    vote  = request.args.get("vote", "0")

    if not link or not email:
        return "Missing parameters", 400

    try:
        vote_int = int(vote)
        if vote_int not in (1, -1):
            return "Vote must be 1 or -1", 400
    except ValueError:
        return "Invalid vote value", 400

    save_feedback(link, email, vote_int)
    print(f"[feedback] {email} voted {'👍' if vote_int == 1 else '👎'} on {link[:60]}")

    # Return a friendly HTML page so the browser shows something nice
    emoji   = "👍" if vote_int == 1 else "👎"
    message = "Thanks! Your feedback helps improve future digests." if vote_int == 1 \
              else "Got it — we'll show fewer stories like this."

    return f"""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px 20px;">
      <div style="font-size:48px;margin-bottom:16px;">{emoji}</div>
      <div style="font-size:18px;color:#333;">{message}</div>
    </body></html>
    """, 200


@app.route("/unsubscribe")
def unsubscribe():
    """Mark a recipient as inactive so they stop receiving emails."""
    from src.db import get_conn
    email = request.args.get("email", "")
    if not email:
        return "Missing email", 400

    conn = get_conn()
    cur  = conn.cursor()
    cur.execute("UPDATE recipients SET active = FALSE WHERE email = %s", (email,))
    conn.commit()
    cur.close()
    conn.close()

    return f"""
    <html><body style="font-family:sans-serif;text-align:center;padding:60px 20px;">
      <div style="font-size:18px;color:#333;">
        {email} has been unsubscribed. You won't receive any more digests.
      </div>
    </body></html>
    """, 200


@app.route("/health")
def health():
    """Simple health check endpoint."""
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    init_db()
    print("[feedback_server] Starting on http://0.0.0.0:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)
