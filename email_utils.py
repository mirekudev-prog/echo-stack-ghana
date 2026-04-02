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

def send_newsletter_email(to_email: str, username: str, post_title: str, post_excerpt: str, post_url: str) -> None:
    subject = f"New post on EchoStack: {post_title}"
    html = f"""
    <html>
      <head>
        <style>
          body {{ font-family: 'DM Sans', Arial, sans-serif; background: #FAF6EF; margin: 0; padding: 0; }}
          .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; }}
          .header {{ background: #0D1B2A; padding: 24px; text-align: center; }}
          .header h1 {{ color: #E8B84B; font-family: 'Playfair Display', serif; margin: 0; font-size: 1.5rem; }}
          .content {{ padding: 32px 24px; }}
          .content h2 {{ font-family: 'Playfair Display', serif; color: #0D1B2A; margin-top: 0; }}
          .content p {{ color: #64748b; line-height: 1.6; }}
          .btn {{ display: inline-block; background: linear-gradient(135deg, #C8962E, #E8B84B); color: #0D1B2A; padding: 14px 32px; border-radius: 50px; text-decoration: none; font-weight: 700; margin-top: 16px; }}
          .footer {{ background: #0f1e2d; padding: 24px; text-align: center; color: rgba(255,255,255,0.5); font-size: 0.8rem; }}
        </style>
      </head>
      <body>
        <div class="container">
          <div class="header">
            <h1>EchoStack</h1>
          </div>
          <div class="content">
            <p style="font-size:0.85rem;color:#94A3B8;margin-top:0">Hi {username},</p>
            <h2>{post_title}</h2>
            <p>{post_excerpt}</p>
            <a href="{post_url}" class="btn">Read Full Story</a>
          </div>
          <div class="footer">
            <p>You're receiving this because you follow creators on EchoStack.</p>
            <p>Built by Mireku Development</p>
          </div>
        </div>
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
