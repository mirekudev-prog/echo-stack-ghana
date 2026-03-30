import os
import secrets
import httpx

# Brevo API settings
BREVO_API_KEY = os.getenv("BREVO_API_KEY")
if not BREVO_API_KEY:
    raise ValueError("BREVO_API_KEY environment variable not set")

FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")  # Use your verified sender
FROM_NAME = "EchoStack"

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def send_verification_email(to_email: str, username: str, token: str) -> None:
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

def send_password_reset_email(to_email: str, username: str, token: str) -> None:
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

def _send_email(to_email: str, subject: str, html_content: str) -> None:
    """Send email using Brevo's API (HTTPS)."""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json"
    }
    payload = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_content
    }

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            print(f"✅ Email sent to {to_email} via Brevo API")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        # Don't raise – let signup continue even if email fails
