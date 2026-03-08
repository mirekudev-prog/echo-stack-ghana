# email_utils.py
import os
import secrets
from datetime import datetime, timedelta

try:
    import resend
except ImportError:
    resend = None

def generate_token():
    """Generate secure random token."""
    return secrets.token_urlsafe(32)

def send_verification_email(email, username, token):
    """Send account verification email using Resend."""
    if not resend:
        print(f"[ERROR] resend package not installed.")
        return False
    
    try:
        app_url = os.getenv("SITE_URL", "https://echostackgh.onrender.com")
        
        # Link to verify
        verify_link = f"{app_url}/verify-email?token={token}"
        
        resend.Email.send({
            "from": os.getenv("RESEND_FROM_EMAIL", "EchoStack <onboarding@resend.dev>"),
            "to": [email],
            "subject": "Welcome to EchoStack Ghana - Verify Your Email",
            "html": f"""
            <h1 style="color:#0D1B2A;">Hello {username}!</h1>
            <p>Welcome to EchoStack Ghana Heritage Archive 🇬🇭</p>
            <p>Please verify your email address to start posting and exploring.</p>
            <br/>
            <a href="{verify_link}" style="background-color:#C8962E;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Verify Email</a>
            <p>Or copy this link into your browser:</p>
            <p>{verify_link}</p>
            <p>If you didn't request this, ignore this email.</p>
            <hr/>
            <small style="color:#999">EchoStack Team</small>
            """
        })
        print(f"✅ Verification sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send verification email: {e}")
        return False

def send_password_reset_email(email, username, token):
    """Send password reset email using Resend."""
    if not resend:
        print(f"[ERROR] resend package not installed.")
        return False

    try:
        app_url = os.getenv("SITE_URL", "https://echostackgh.onrender.com")
        reset_link = f"{app_url}/reset-password?token={token}"
        
        resend.Email.send({
            "from": os.getenv("RESEND_FROM_EMAIL", "EchoStack <onboarding@resend.dev>"),
            "to": [email],
            "subject": "Password Reset Request - EchoStack",
            "html": f"""
            <h1>Reset Password</h1>
            <p>We received a request to reset your password for EchoStack.</p>
            <br/>
            <a href="{reset_link}" style="background-color:#0077b6;color:white;padding:12px 24px;text-decoration:none;border-radius:8px;font-weight:bold;display:inline-block;">Reset Password</a>
            <p>This link expires in 1 hour.</p>
            <hr/>
            <small style="color:#999">EchoStack Team</small>
            """
        })
        print(f"✅ Reset link sent to {email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send reset email: {e}")
        return False
