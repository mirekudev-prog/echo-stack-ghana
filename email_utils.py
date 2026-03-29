import os
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Read SMTP settings from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL")          # Your personal email (Brevo‑verified)
FROM_NAME = "EchoStack"

def generate_token() -> str:
    """Generate a secure random token for email verification/password reset."""
    return secrets.token_urlsafe(32)

def send_verification_email(to_email: str, username: str, token: str) -> None:
    """Send email verification link to user."""
    link = f"https://echostack.onrender.com/verify-email?token={token}"
    subject = "Verify your EchoStack account"
    html = f"""
    <html>
      <body>
        <h2>Akwaaba, {username}!</h2>
        <p>Thank you for joining EchoStack. Please verify your email address by clicking the link below:</p>
        <p><a href="{link}">Verify Email</a></p>
        <p>If you didn't sign up, you can ignore this email.</p>
        <p>– EchoStack Team</p>
      </body>
    </html>
    """
    _send_email(to_email, subject, html)

def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    """Send password reset link to user."""
    link = f"https://echostack.onrender.com/reset-password?token={token}"
    subject = "Reset your EchoStack password"
    html = f"""
    <html>
      <body>
        <p>Hi {username},</p>
        <p>Click the link below to reset your password:</p>
        <p><a href="{link}">Reset Password</a></p>
        <p>If you didn't request this, you can ignore this email.</p>
        <p>– EchoStack Team</p>
      </body>
    </html>
    """
    _send_email(to_email, subject, html)

def _send_email(to_email: str, subject: str, html_content: str) -> None:
    """Internal helper to send email via Brevo SMTP."""
    if not SMTP_USER or not SMTP_PASS or not FROM_EMAIL:
        print("❌ SMTP credentials not fully configured in environment")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email

    part = MIMEText(html_content, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()                # Upgrade connection to secure
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"✅ Verification email sent to {to_email}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        # Don't raise – let the signup succeed even if email fails
