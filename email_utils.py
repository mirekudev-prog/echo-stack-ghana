import resend
import os
import secrets
from datetime import datetime, timedelta

# Configure Resend
resend.api_key = os.getenv("RESEND_API_KEY")
FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")

def generate_token() -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(32)

def send_verification_email(to_email: str, username: str, token: str) -> bool:
    """Send email verification link"""
    verification_link = f"https://echostack.onrender.com/verify-email?token={token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: sans-serif; background: #0D1B2A; padding: 40px;">
        <div style="max-width: 480px; margin: 0 auto; background: #0a1520; border: 1px solid #C8962E; border-radius: 24px; padding: 40px;">
            <h1 style="color: #C8962E;">Welcome, {username}!</h1>
            <p style="color: #fff;">Thank you for joining EchoStack. Please verify your email address:</p>
            <a href="{verification_link}" style="display: inline-block; background: #C8962E; color: #0D1B2A; padding: 12px 30px; border-radius: 50px; text-decoration: none; font-weight: bold;">Verify Email</a>
            <p style="color: #94A3B8; margin-top: 20px;">This link expires in 24 hours.</p>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Verify your EchoStack account",
            "html": html_content,
        }
        resend.Emails.send(params)
        print(f"✅ Verification email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def send_password_reset_email(to_email: str, username: str, token: str) -> bool:
    """Send password reset link"""
    reset_link = f"https://echostack.onrender.com/reset-password?token={token}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: sans-serif; background: #0D1B2A; padding: 40px;">
        <div style="max-width: 480px; margin: 0 auto; background: #0a1520; border: 1px solid #C8962E; border-radius: 24px; padding: 40px;">
            <h1 style="color: #C8962E;">Reset your password</h1>
            <p style="color: #fff;">Hi {username}, click below to set a new password:</p>
            <a href="{reset_link}" style="display: inline-block; background: #C8962E; color: #0D1B2A; padding: 12px 30px; border-radius: 50px; text-decoration: none; font-weight: bold;">Reset Password</a>
            <p style="color: #94A3B8; margin-top: 20px;">This link expires in 1 hour. If you didn't request this, ignore this email.</p>
        </div>
    </body>
    </html>
    """
    
    try:
        params = {
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your EchoStack password",
            "html": html_content,
        }
        resend.Emails.send(params)
        print(f"✅ Password reset email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False
