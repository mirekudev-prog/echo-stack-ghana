import os
import secrets
from mailersend import emails

# MailerSend API key from environment
MAILERSEND_API_KEY = os.getenv("MAILERSEND_API_KEY")
if not MAILERSEND_API_KEY:
    raise ValueError("MAILERSEND_API_KEY environment variable not set")

# Your test domain (from MailerSend)
FROM_DOMAIN = "test-r83ql3pyydmgzw1j.mlsender.net"  # replace with your actual test domain
FROM_EMAIL = f"noreply@{FROM_DOMAIN}"
FROM_NAME = "EchoStack"

# Initialize MailerSend client
mailer = emails.NewEmail(MAILERSEND_API_KEY)

def generate_token() -> str:
    """Generate a secure random token for email verification/password reset."""
    return secrets.token_urlsafe(32)

def send_verification_email(to_email: str, username: str, token: str) -> None:
    """Send email verification link to user."""
    verification_link = f"https://echostack.onrender.com/verify-email?token={token}"
    subject = "Verify your EchoStack account"
    html_content = f"""
    <html>
      <body>
        <h2>Akwaaba, {username}!</h2>
        <p>Thank you for joining EchoStack. Please verify your email address by clicking the link below:</p>
        <p><a href="{verification_link}">Verify Email</a></p>
        <p>If you didn't sign up, you can ignore this email.</p>
        <p>– EchoStack Team</p>
      </body>
    </html>
    """
    _send_email(to_email, subject, html_content)

def send_password_reset_email(to_email: str, username: str, token: str) -> None:
    """Send password reset link to user."""
    reset_link = f"https://echostack.onrender.com/reset-password?token={token}"
    subject = "Reset your EchoStack password"
    html_content = f"""
    <html>
      <body>
        <p>Hi {username},</p>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_link}">Reset Password</a></p>
        <p>If you didn't request this, you can ignore this email.</p>
        <p>– EchoStack Team</p>
      </body>
    </html>
    """
    _send_email(to_email, subject, html_content)

def _send_email(to_email: str, subject: str, html_content: str) -> None:
    """Internal helper to send email via MailerSend API."""
    mail_from = {
        "name": FROM_NAME,
        "email": FROM_EMAIL,
    }
    recipients = [
        {
            "email": to_email,
        }
    ]

    try:
        # Using mailersend library
        response = mailer.send(
            mail_from,
            recipients,
            subject,
            html=html_content
        )
        print(f"✅ Email sent to {to_email}, response: {response}")
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {e}")
        # In production you might want to log to a file or retry
        raise  # re-raise to let the caller know it failed
