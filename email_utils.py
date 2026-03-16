import os
import secrets
from mailersend import emails

MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY")
if not MAILERSEND_API_KEY:
    raise ValueError("MAILERSEND_API_KEY environment variable not set")

FROM_DOMAIN = "test-r83ql3pyydmgzw1j.mlsender.net"  # your exact test domain
FROM_EMAIL = f"noreply@{FROM_DOMAIN}"
FROM_NAME = "EchoStack"

mailer = emails.NewEmail(MAILERSEND_API_KEY)

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def send_verification_email(to_email: str, username: str, token: str):
    link = f"https://echostack.onrender.com/verify-email?token={token}"
    subject = "Verify your EchoStack account"
    html = f"""
    <html>
      <body>
        <h2>Akwaaba, {username}!</h2>
        <p>Click <a href="{link}">here</a> to verify your email.</p>
      </body>
    </html>
    """
    _send_email(to_email, subject, html)

def send_password_reset_email(to_email: str, username: str, token: str):
    link = f"https://echostack.onrender.com/reset-password?token={token}"
    subject = "Reset your EchoStack password"
    html = f"""
    <html>
      <body>
        <p>Hi {username},</p>
        <p>Click <a href="{link}">here</a> to reset your password.</p>
      </body>
    </html>
    """
    _send_email(to_email, subject, html)

def _send_email(to_email: str, subject: str, html_content: str):
    mail_from = {"name": FROM_NAME, "email": FROM_EMAIL}
    recipients = [{"email": to_email}]
    try:
        # MailerSend expects content as a dictionary, not as keyword 'html'
        response = mailer.send(
            mail_from,
            recipients,
            subject,
            content={
                "html": html_content
            }
        )
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        # Optionally re-raise if you want the caller to know
        # raise
