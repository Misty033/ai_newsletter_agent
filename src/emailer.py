import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.config import EMAIL_SENDER, EMAIL_APP_PASSWORD


def send_email(to_email: str, subject: str, html_body: str):
    """
    Send a single HTML email from your sender account to one recipient.

    The recipient only needs to provide their email address.
    You authenticate with YOUR sender account's app password only.

    Gmail App Password setup:
      1. Go to myaccount.google.com → Security
      2. Enable 2-step verification
      3. Search "App passwords" → generate one → paste in .env
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"AI News Digest <{EMAIL_SENDER}>"
    msg["To"]      = to_email

    # Attach HTML version
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, to_email, msg.as_string())
        print(f"[emailer] Sent to {to_email}")
    except Exception as e:
        print(f"[emailer] Failed to send to {to_email}: {e}")
        raise


def send_to_all(articles: list, recipients: list, formatter_fn, **kwargs):
    """
    Send a personalised email to every active recipient.

    formatter_fn: either format_daily_email or format_weekly_email from formatter.py
    kwargs:       any extra arguments the formatter needs (e.g. theme= for weekly)
    """
    print(f"[emailer] Sending to {len(recipients)} recipients...")
    for recipient in recipients:
        try:
            subject, html = formatter_fn(articles, recipient, **kwargs)
            send_email(recipient["email"], subject, html)
        except Exception as e:
            print(f"[emailer] Error for {recipient['email']}: {e}")
