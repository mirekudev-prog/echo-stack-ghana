from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, and_, func, inspect
import os, uuid, re, json, httpx, random
from datetime import datetime, timedelta
import secrets
import traceback

# Load environment variables from .env file (if python-dotenv is installed)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv not installed; rely on system environment variables

# Password hashing
from passlib.context import CryptContext

from database import engine, get_db, Base
import models

# CMS Models and Router (Project 9: Audio Archive & Podcast Network)
from cms_models import Base as CmsBase, Project, ProjectBlock, AudioClip, RevenuePlan
from cms_admin import router as cms_admin_router

# ─── PASSWORD HASHING ────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain, hashed):
    try:
        if not plain or not hashed:
            return False
        # Try truncated password first (72 byte limit for bcrypt)
        truncated = plain[:72]
        if pwd_context.verify(truncated, hashed):
            return True
        # Fallback: try original password (for legacy passwords stored before fix)
        if plain != truncated and pwd_context.verify(plain, hashed):
            return True
        return False
    except Exception as e:
        print(f"Password verify error: {e}")
        return False


def get_password_hash(password):
    if not password:
        return ""
    # Truncate to 72 bytes (bcrypt limit)
    truncated = password[:72]
    return pwd_context.hash(truncated)


# ─── EMAIL UTILITIES (safe import — won't crash if file is missing) ──────────
try:
    from email_utils import (
        generate_token,
        send_verification_email,
        send_password_reset_email,
        send_newsletter_email,
    )

    EMAIL_ENABLED = True
except Exception as _e:
    EMAIL_ENABLED = False
    print(f"WARNING  email_utils not loaded: {_e} - email features disabled")

    def generate_token():
        return secrets.token_urlsafe(32)

    def send_verification_email(email, username, token):
        print(f"[EMAIL STUB] verify {email} token={token}")

    def send_password_reset_email(email, username, token):
        print(f"[EMAIL STUB] reset {email} token={token}")

    def send_newsletter_email(to_email, username, post_title, post_excerpt, post_url):
        print(f"[EMAIL STUB] newsletter {to_email}: {post_title}")


# ─── TABLE CREATION ──────────────────────────────────────────────────────────
_CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    capital VARCHAR(100),
    population VARCHAR(50),
    terrain VARCHAR(100),
    description TEXT,
    overview TEXT,
    category VARCHAR(50),
    tags TEXT,
    hero_image VARCHAR(500),
    gallery_images TEXT,
    audio_files TEXT,
    video_files TEXT,
    documents TEXT,
    source VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) DEFAULT '',
    bio TEXT DEFAULT '',
    avatar_url VARCHAR(500) DEFAULT '',
    channel_name VARCHAR(200) DEFAULT '',
    channel_desc TEXT DEFAULT '',
    role VARCHAR(50) DEFAULT 'user',
    is_premium INTEGER DEFAULT 0,
    is_suspended INTEGER DEFAULT 0,
    follower_count INTEGER DEFAULT 0,
    email_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR(255),
    verification_token_expires TIMESTAMP,
    reset_token VARCHAR(255),
    reset_token_expires TIMESTAMP,
    reset_code VARCHAR(6),
    reset_code_expires TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) DEFAULT '',
    slug VARCHAR(500) DEFAULT '',
    excerpt TEXT DEFAULT '',
    content TEXT DEFAULT '',
    cover_image VARCHAR(500) DEFAULT '',
    content_type VARCHAR(50) DEFAULT 'article',
    status VARCHAR(50) DEFAULT 'draft',
    is_locked INTEGER DEFAULT 0,
    author_id UUID REFERENCES users(id),
    author_username VARCHAR(200) DEFAULT '',
    region_id INTEGER DEFAULT NULL,
    tags TEXT DEFAULT '',
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    audio_url VARCHAR(500) DEFAULT '',
    video_url VARCHAR(500) DEFAULT '',
    gallery TEXT DEFAULT '',
    media_url VARCHAR(500) DEFAULT '',
    media_path VARCHAR(500) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id),
    user_id UUID REFERENCES users(id),
    username VARCHAR(200) DEFAULT '',
    content TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS faqs (
    id SERIAL PRIMARY KEY,
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100) DEFAULT 'General',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS follows (
    id SERIAL PRIMARY KEY,
    follower_id UUID REFERENCES users(id),
    following_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    original_name VARCHAR(255),
    file_path VARCHAR(500) DEFAULT '',
    file_size INTEGER,
    mime_type VARCHAR(100),
    category VARCHAR(50),
    region_id INTEGER DEFAULT NULL,
    description TEXT,
    uploaded_by VARCHAR(100) DEFAULT 'user',
    is_public INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    slug VARCHAR(100) UNIQUE,
    description TEXT,
    parent_section_id INTEGER DEFAULT NULL,
    display_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id SERIAL PRIMARY KEY,
    email VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    description TEXT,
    event_date TIMESTAMP,
    location VARCHAR(300),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    username VARCHAR(200) DEFAULT 'Guest',
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS story_submissions (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT,
    region VARCHAR(100),
    author_name VARCHAR(200),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_logs (
    id SERIAL PRIMARY KEY,
    admin_username VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,   -- e.g., 'upload', 'delete', 'edit'
    target_type VARCHAR(50),       -- e.g., 'file', 'post', 'region'
    target_id VARCHAR(100),        -- file id, post id, region id
    details TEXT,                  -- extra info like filename, post title
    ip_address VARCHAR(45),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    email VARCHAR(200),
    amount INTEGER DEFAULT 0,
    reference VARCHAR(200),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_topics (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, topic_id)
);

-- ADDED: creator_chat_messages table (now inside the SQL string)
CREATE TABLE IF NOT EXISTS creator_chat_messages (
    id SERIAL PRIMARY KEY,
    creator_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    username VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    category VARCHAR(50) DEFAULT 'general',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS page_contents (
    id SERIAL PRIMARY KEY,
    page_name VARCHAR(100) NOT NULL,
    section VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    display_order INTEGER DEFAULT 0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS navigation_items (
    id SERIAL PRIMARY KEY,
    label VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    target VARCHAR(20) DEFAULT '_self',
    parent_id INTEGER DEFAULT NULL,
    display_order INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    post_id INTEGER REFERENCES posts(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    type VARCHAR(50) DEFAULT 'info',
    title VARCHAR(200) DEFAULT '',
    message TEXT DEFAULT '',
    link VARCHAR(500) DEFAULT '',
    is_read INTEGER DEFAULT 0,
    actor_id UUID REFERENCES users(id),
    actor_username VARCHAR(200) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS direct_messages (
    id SERIAL PRIMARY KEY,
    sender_id UUID REFERENCES users(id),
    receiver_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collections (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(200) NOT NULL,
    description TEXT DEFAULT '',
    cover_image VARCHAR(500) DEFAULT '',
    is_public INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_items (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES collections(id) ON DELETE CASCADE,
    post_id INTEGER REFERENCES posts(id),
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id UUID UNIQUE REFERENCES users(id),
    dark_mode INTEGER DEFAULT 0,
    language VARCHAR(20) DEFAULT 'en',
    email_notifications INTEGER DEFAULT 1,
    push_notifications INTEGER DEFAULT 1,
    show_follower_count INTEGER DEFAULT 1,
    show_post_stats INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tips (
    id SERIAL PRIMARY KEY,
    sender_id UUID REFERENCES users(id),
    receiver_id UUID REFERENCES users(id),
    amount INTEGER DEFAULT 0,
    message TEXT DEFAULT '',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id SERIAL PRIMARY KEY,
    subscriber_id UUID REFERENCES users(id),
    creator_id UUID REFERENCES users(id),
    tier VARCHAR(50) DEFAULT 'free',
    amount INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'active',
    starts_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_badges (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    badge_type VARCHAR(50) NOT NULL,
    badge_name VARCHAR(100) DEFAULT '',
    badge_icon VARCHAR(100) DEFAULT '',
    awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS shares (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    post_id INTEGER REFERENCES posts(id),
    platform VARCHAR(50) DEFAULT 'internal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"SQLAlchemy create_all note: {e}")


def _run_startup_sql():
    try:
        with engine.connect() as conn:
            for stmt in _CREATE_TABLES_SQL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        conn.execute(text(stmt))
                        conn.commit()
                    except Exception:
                        pass
        print("SUCCESS EchoStack tables verified/created")
    except Exception as e:
        print(f"Startup SQL note: {e}")


def _run_migrations():
    cols = [
        ("users", "hashed_password", "VARCHAR(255) DEFAULT ''"),
        ("users", "bio", "TEXT DEFAULT ''"),
        ("users", "avatar_url", "VARCHAR(500) DEFAULT ''"),
        ("users", "channel_name", "VARCHAR(200) DEFAULT ''"),
        ("users", "channel_desc", "TEXT DEFAULT ''"),
        ("users", "role", "VARCHAR(50) DEFAULT 'user'"),
        ("users", "is_premium", "INTEGER DEFAULT 0"),
        ("users", "is_suspended", "INTEGER DEFAULT 0"),
        ("users", "follower_count", "INTEGER DEFAULT 0"),
        ("users", "email_verified", "BOOLEAN DEFAULT FALSE"),
        ("users", "verification_token", "VARCHAR(255)"),
        ("users", "verification_token_expires", "TIMESTAMP"),
        ("users", "reset_token", "VARCHAR(255)"),
        ("users", "reset_token_expires", "TIMESTAMP"),
        # NEW columns for 6-digit reset code
        ("users", "reset_code", "VARCHAR(6)"),
        ("users", "reset_code_expires", "TIMESTAMP"),
        ("posts", "audio_url", "VARCHAR(500) DEFAULT ''"),
        ("posts", "video_url", "VARCHAR(500) DEFAULT ''"),
        ("posts", "gallery", "TEXT DEFAULT ''"),
        ("posts", "cover_image", "VARCHAR(500) DEFAULT ''"),
        ("posts", "is_locked", "INTEGER DEFAULT 0"),
        ("posts", "tags", "TEXT DEFAULT ''"),
        ("posts", "views", "INTEGER DEFAULT 0"),
        ("posts", "likes", "INTEGER DEFAULT 0"),
        ("posts", "media_url", "VARCHAR(500) DEFAULT ''"),
        ("posts", "media_path", "VARCHAR(500) DEFAULT ''"),
        ("users", "full_name", "VARCHAR(255) DEFAULT ''"),
        ("users", "is_verified", "BOOLEAN DEFAULT FALSE"),
        ("posts", "media_type", "VARCHAR(50) DEFAULT 'image'"),
        ("posts", "likes_count", "INTEGER DEFAULT 0"),
        ("posts", "author_avatar", "VARCHAR(500) DEFAULT ''"),
        ("regions", "overview", "TEXT DEFAULT ''"),
        ("regions", "video_files", "TEXT DEFAULT ''"),
        ("regions", "documents", "TEXT DEFAULT ''"),
        ("uploaded_files", "file_path", "VARCHAR(500) DEFAULT ''"),
        ("uploaded_files", "uploaded_by", "VARCHAR(200) DEFAULT 'user'"),
        ("uploaded_files", "is_public", "INTEGER DEFAULT 1"),
        ("uploaded_files", "description", "TEXT DEFAULT ''"),
        ("story_submissions", "region", "VARCHAR(100) DEFAULT ''"),
    ]
    try:
        inspector = inspect(engine)
        with engine.connect() as conn:
            for table, col, col_def in cols:
                try:
                    # Cross-platform way to check column existence (SQLite & Postgres)
                    columns = inspector.get_columns(table)
                    exists = any(c["name"].lower() == col.lower() for c in columns)

                    if not exists:
                        print(f"Adding missing column: {table}.{col}")
                        conn.execute(
                            text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                        )
                        conn.commit()
                except Exception as e:
                    print(f"Migration note ({table}.{col}): {e}")
        print("SUCCESS Migrations verified")
    except Exception as e:
        print(f"Migration error: {e}")


def _seed_topics():
    default_topics = [
        "Ashanti Culture",
        "Ga Traditions",
        "Ewe Music",
        "Northern Heritage",
        "Gold Coast History",
        "Slave Castles",
        "Highlife Music",
        "Traditional Drums",
        "Kente Cloth",
        "Fante Language",
        "Mole National Park",
        "Kakum Forest",
        "Lake Volta",
        "Twi Language",
        "Dagomba Stories",
        "Chieftaincy",
        "Oral Histories",
        "Modern Ghana Art",
        "Afrobeats History",
        "Festivals & Ceremonies",
    ]
    try:
        with engine.connect() as conn:
            for topic in default_topics:
                conn.execute(
                    text(
                        "INSERT INTO topics (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"
                    ),
                    {"name": topic},
                )
            conn.commit()
        print("SUCCESS Topics seeded")
    except Exception as e:
        print(f"Topics seeding note: {e}")


_run_startup_sql()
_run_migrations()
_seed_topics()


# ─── CREATE CMS TABLES ──────────────────────────────────────────────────────
def _create_cms_tables():
    try:
        CmsBase.metadata.create_all(bind=engine)
        print("SUCCESS CMS tables created/verified")
    except Exception as e:
        print(f"CMS tables note: {e}")


_create_cms_tables()

# ─── APP ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="EchoStack API")

# Include CMS Admin Router
app.include_router(cms_admin_router)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception:
    pass
try:
    app.mount("/css", StaticFiles(directory="css"), name="css")
except Exception:
    pass
try:
    app.mount("/icons", StaticFiles(directory="icons"), name="icons")
except Exception:
    pass
try:
    app.mount("/js", StaticFiles(directory="js"), name="js")
except Exception:
    pass

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "the admin")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "echostack-uploads")
HF_TOKEN = os.getenv("HF_TOKEN", "")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY", "")
SUPERUSER_EMAIL = "memmanuel06@outlook.com"


# ─── ERROR PAGES ─────────────────────────────────────────────────────────────────
def _serve_error_page(status_code: int) -> FileResponse:
    """Serve an error page (404.html, 500.html) with fallback to plain text."""
    error_page = f"{status_code}.html"
    if os.path.exists(error_page):
        return FileResponse(error_page, status_code=status_code)
    # Fallback: return plain text response
    return JSONResponse(
        {
            "error": f"{status_code} - Service Unavailable"
            if status_code == 500
            else "Not Found"
        },
        status_code=status_code,
    )


# ─── EXCEPTION HANDLERS ──────────────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 - Page or resource not found."""
    # For API requests, return JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"error": "Not found", "detail": exc.detail, "path": request.url.path},
            status_code=404,
        )
    # For HTML requests, serve custom 404 page
    return _serve_error_page(404)


@app.exception_handler(500)
async def server_error_handler(request: Request, exc: Exception):
    """Handle 500 - Internal server error."""
    # Log the error for debugging
    import traceback

    print(f"500 Error: {exc}")
    print(traceback.format_exc())

    # For API requests, return JSON with error details
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {
                "error": "Internal server error",
                "detail": str(exc) if os.getenv("DEBUG") else None,
            },
            status_code=500,
        )
    # For HTML requests, serve custom 500 page
    return _serve_error_page(500)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle other HTTP exceptions (400, 401, 403, etc.)."""
    # For API requests, return JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {"error": exc.detail, "status_code": exc.status_code},
            status_code=exc.status_code,
        )
    # For HTML pages, redirect to appropriate error page based on status
    if exc.status_code in [404, 500]:
        return _serve_error_page(exc.status_code)
    # For other errors, return simple HTML response
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{{exc.status_code}} — EchoStack</title>
            <link rel="stylesheet" href="/css/base.css">
        </head>
        <body style="display:flex;align-items:center;justify-content:center;min-height:100vh;font-family:'DM Sans',sans-serif;background:var(--cream);text-align:center;padding:24px;">
            <div style="max-width:500px;animation:fadeInUp 0.6s ease-out;">
                <div style="font-family:'Playfair Display',serif;font-size:clamp(3rem,10vw,6rem);font-weight:900;color:var(--ink);margin-bottom:16px;">{exc.status_code}</div>
                <h1 style="font-family:'Playfair Display',serif;font-size:1.5rem;font-weight:700;margin-bottom:12px;color:var(--ink);">Oops!</h1>
                <p style="font-size:1rem;color:#64748b;line-height:1.7;margin-bottom:24px;">{{exc.detail}}</p>
                <a href="/" style="display:inline-flex;align-items:center;gap:8px;padding:12px 24px;border-radius:50px;font-weight:600;background:linear-gradient(135deg,var(--gold),var(--gold2));color:var(--ink);text-decoration:none;box-shadow:0 4px 12px rgba(200,150,46,0.3);">
                    <i class="fas fa-home"></i>Go Home
                </a>
            </div>
        </body>
        </html>
        """,
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for any unhandled exceptions."""
    import traceback

    print(f"Unhandled exception: {{exc}}")
    print(traceback.format_exc())

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            {{"error": "Internal server error", "code": "UNHANDLED_ERROR"}},
            status_code=500,
        )
    return _serve_error_page(500)


# ─── HEALTH CHECK ───────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Simple health check endpoint for monitoring and offline detection."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "EchoStack API",
    }


# ─── HELPERS ────────────────────────────────────────────────────────────────────
def slugify(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:80]


def _is_admin(request: Request) -> bool:
    # First, check the admin cookie (for normal admins)
    if request.cookies.get("admin_session") == "ADMIN_AUTHORIZED":
        return True

    # Then, check if the logged‑in user is the hardcoded superuser
    sid = request.cookies.get("user_session")
    if sid:
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("SELECT email FROM users WHERE id = :uid"), {"uid": sid}
                ).fetchone()
                if result and result[0] == SUPERUSER_EMAIL:
                    return True
        except Exception:
            pass

    # Also check admin_preview query param for bypass mode
    if request.query_params.get("admin_preview") == "true":
        # If admin_preview is set, check if user has admin_session or is superuser
        if request.cookies.get("admin_session") == "ADMIN_AUTHORIZED":
            return True
        if sid:
            try:
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT email FROM users WHERE id = :uid"), {"uid": sid}
                    ).fetchone()
                    if result and result[0] == SUPERUSER_EMAIL:
                        return True
            except Exception:
                pass

    return False


def _get_user(request: Request, db: Session):
    """Return User row from user_session cookie, or None."""
    sid = request.cookies.get("user_session")
    if not sid:
        return None
    try:
        return db.query(models.User).filter(models.User.id == sid).first()
    except Exception:
        return None


async def upload_to_supabase(content: bytes, filename: str, ctype: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
        headers = {
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": ctype,
            "x-upsert": "true",
        }
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, content=content, headers=headers)
        if r.status_code in (200, 201):
            return (
                f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
            )
    except Exception as e:
        print(f"Supabase error: {e}")
    return None


async def _do_upload(file: UploadFile, category: str, db: Session) -> dict:
    content = await file.read()
    ext = os.path.splitext(file.filename or "file")[1].lower() or ".bin"
    safe = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    ctype = file.content_type or "application/octet-stream"

    pub_url = await upload_to_supabase(content, safe, ctype)
    if pub_url:
        fpath = pub_url
    else:
        fpath = os.path.join(UPLOAD_DIR, safe)
        with open(fpath, "wb") as f:
            f.write(content)
        pub_url = f"/uploads/{safe}"

    try:
        rec = models.UploadedFile(
            filename=safe,
            original_name=file.filename or safe,
            file_path=fpath,
            file_size=len(content),
            mime_type=ctype,
            category=category,
            uploaded_by="user",
            is_public=True,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        fid = rec.id
    except Exception:
        fid = None

    size_bytes = len(content)
    return {
        "success": True,
        "url": pub_url,
        "file_url": pub_url,
        "filename": safe,
        "original_name": file.filename or safe,
        "file_id": fid,
        "size": size_bytes,
        "file_size_mb": round(size_bytes / (1024 * 1024), 2),
        "file_size_kb": round(size_bytes / 1024, 1),
        "category": category,
        "mime_type": ctype,
    }


def log_admin_action(
    request: Request,
    action: str,
    target_type: str,
    target_id: str,
    details: str,
    db: Session,
):
    """Log an admin action to the admin_logs table."""
    admin_username = request.cookies.get("admin_user", "Unknown")
    ip = request.client.host if request.client else ""
    db.execute(
        text(
            "INSERT INTO admin_logs (admin_username, action, target_type, target_id, details, ip_address) VALUES (:admin, :action, :type, :tid, :details, :ip)"
        ),
        {
            "admin": admin_username,
            "action": action,
            "type": target_type,
            "tid": target_id,
            "details": details,
            "ip": ip,
        },
    )
    db.commit()


# ─── STATIC PAGE HELPER ───────────────────────────────────────────────────────
def _serve(filename: str, request: Request = None):
    """Serve an HTML file. Admins can always access any page."""
    if os.path.exists(filename):
        return FileResponse(filename)
    raise HTTPException(404, f"{filename} not found")


# ─── PUBLIC PAGES ─────────────────────────────────────────────────────────────
@app.get("/")
async def homepage(request: Request):
    # Admins can bypass email verification when previewing the live site
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("index.html")
    return _serve("index.html")


@app.get("/login")
def login_page():
    return _serve("login.html")


@app.get("/signup")
def signup_page():
    return _serve("signup.html")


@app.get("/user-login")
def user_login_page():
    return _serve("user-login.html")


@app.get("/premium")
def premium_page():
    return _serve("premium.html")


@app.get("/verify-email")
def verify_email_page():
    return _serve("verify-email.html")


@app.get("/reset-password")
def reset_password_page():
    return _serve("reset-password.html")


@app.get("/explore")
def explore_page():
    return _serve("explore.html")


@app.get("/archive")
def archive_page():
    return _serve("archive.html")


@app.get("/community")
def community_page():
    return _serve("community_chat.html")


@app.get("/chat")
def chat_page():
    return _serve("community_chat.html")


# ─── PROTECTED PAGES (user OR admin can access) ───────────────────────────────
@app.get("/app")
async def app_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("app.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("app.html")
    return RedirectResponse("/user-login")


@app.get("/dashboard")
async def dashboard_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("dashboard.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("dashboard.html")
    return RedirectResponse("/user-login")


@app.get("/reels")
async def reels_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("reels.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("reels.html")
    return RedirectResponse("/user-login")


@app.get("/creator")
async def creator_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("creator.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("creator.html")
    return RedirectResponse("/user-login")


@app.get("/activity")
async def activity_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("activity.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("activity.html")
    return RedirectResponse("/user-login")


@app.get("/following")
async def following_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("following.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("following.html")
    return RedirectResponse("/user-login")


@app.get("/subscriptions")
async def subscriptions_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("subscriptions.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("subscriptions.html")
    return RedirectResponse("/user-login")


@app.get("/notifications")
async def notifications_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("notifications.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("notifications.html")
    return RedirectResponse("/user-login")


@app.get("/bookmarks")
async def bookmarks_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("bookmarks.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("bookmarks.html")
    return RedirectResponse("/user-login")


@app.get("/trending")
async def trending_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("trending.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("trending.html")
    return RedirectResponse("/user-login")


@app.get("/messages")
async def messages_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("messages.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("messages.html")
    return RedirectResponse("/user-login")


@app.get("/settings")
async def settings_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("settings.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("settings.html")
    return RedirectResponse("/user-login")


@app.get("/donate")
async def donate_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("donate.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("donate.html")
    return RedirectResponse("/user-login")


@app.get("/chatbot")
async def chatbot_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("chatbot.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("chatbot.html")
    return RedirectResponse("/user-login")


@app.get("/read/{post_id}")
async def read_page(post_id: int, request: Request):
    return _serve("read.html")


@app.get("/read")
async def read_redirect(request: Request):
    return RedirectResponse("/dashboard")


@app.get("/subscribers")
async def subscribers_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("subscribers.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("subscribers.html")
    return RedirectResponse("/user-login")


@app.get("/user")
async def user_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("user_profile.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("user_profile.html")
    return RedirectResponse("/user-login")


@app.get("/user/{uname}")
async def user_publication_page(uname: str, request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("publication.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("publication.html")
    return RedirectResponse("/user-login")


@app.get("/user-profile")
async def user_profile_redirect(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        return _serve("user-profile.html")
    if _is_admin(request) or request.cookies.get("user_session"):
        return _serve("user-profile.html")
    return RedirectResponse("/user-login")


@app.get("/user-settings")
async def user_settings_page(request: Request):
    # Admin preview bypasses email verification
    if request.query_params.get("admin_preview") == "true" and _is_admin(request):
        if os.path.exists("user_settings.html"):
            return FileResponse("user_settings.html")
        raise HTTPException(404, "user_settings.html not found")
    if _is_admin(request) or request.cookies.get("user_session"):
        if os.path.exists("user_settings.html"):
            return FileResponse("user_settings.html")
        raise HTTPException(404, "user_settings.html not found")
    return RedirectResponse("/user-login")


@app.get("/post/{pid}")
async def post_page(pid: int, request: Request):
    # Posts are publicly viewable (locked content is handled client-side)
    return _serve("post.html")


@app.get("/logout")
async def logout_redirect():
    """Clear user session and redirect to home."""
    r = RedirectResponse(url="/")
    r.delete_cookie("user_session", path="/")
    return r


# ─── MANIFEST / SERVICE WORKER / ASSETS ──────────────────────────────────────
@app.get("/manifest.json")
def manifest():
    if os.path.exists("manifest.json"):
        return JSONResponse(json.load(open("manifest.json")))
    raise HTTPException(404)


@app.get("/sw.js")
def sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript")
    raise HTTPException(404)


@app.get("/echostack-logo.png")
def logo():
    if os.path.exists("echostack-logo.png"):
        return FileResponse("echostack-logo.png")
    raise HTTPException(404)


@app.get("/test")
def test():
    return {
        "status": "ok",
        "version": "EchoStack v2",
        "email_enabled": EMAIL_ENABLED,
        "supabase_configured": bool(SUPABASE_URL),
        "paystack_configured": bool(PAYSTACK_SECRET),
        "hf_configured": bool(HF_TOKEN),
    }


@app.get("/api/debug/db")
async def debug_db(db: Session = Depends(get_db)):
    """Debug database connection and data"""
    import os

    db_url = os.environ.get("DATABASE_URL", "not set")
    masked_url = (
        db_url[:30] + "..." if db_url != "not set" and len(db_url) > 30 else db_url
    )

    try:
        posts_count = db.query(models.Post).count()
        users_count = db.query(models.User).count()
        regions_count = db.query(models.Region).count()

        recent_posts = (
            db.query(models.Post).order_by(models.Post.created_at.desc()).limit(3).all()
        )
        recent = [
            {"id": p.id, "title": p.title, "status": p.status} for p in recent_posts
        ]

        return {
            "status": "connected",
            "database_url_configured": bool(db_url and db_url != "not set"),
            "database_type": "postgresql" if "postgresql" in db_url else "sqlite",
            "posts_count": posts_count,
            "users_count": users_count,
            "regions_count": regions_count,
            "recent_posts": recent,
        }
    except Exception as e:
        return {
            "status": "error",
            "database_url_configured": bool(db_url and db_url != "not set"),
            "error": str(e),
        }


# ─── ADMIN PAGES & AUTH ───────────────────────────────────────────────────────
@app.get("/admin")
async def admin_page(request: Request):
    if _is_admin(request):
        return _serve("admin_dashboard.html")
    return _serve("login.html")


@app.get("/admin-dashboard")
async def admin_dashboard_page(request: Request):
    """Dynamic CMS Admin Dashboard for Project 9 and beyond"""
    if _is_admin(request):
        return _serve("admin_dashboard.html")
    return _serve("login.html")


@app.get("/project/{project_id}")
async def project_page(project_id: int, request: Request):
    """Public project viewer - Audio Archive & Podcast Network"""
    return _serve("project.html")


@app.get("/admin-preview")
async def admin_preview(request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    # Redirect to the live app page with admin bypass - opens in same window
    return RedirectResponse(url="/app?admin_preview=true")


@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    if answer.strip().lower().replace(" ", "") == ADMIN_SECRET.lower().replace(" ", ""):
        admin_username = os.getenv("ADMIN_USERNAME", "Admin")
        r = JSONResponse({"success": True, "role": "admin"})
        r.set_cookie(
            "admin_session",
            "ADMIN_AUTHORIZED",
            max_age=86400 * 7,
            path="/",
            httponly=False,
            samesite="Lax",
        )
        r.set_cookie(
            "admin_user",
            admin_username,
            max_age=86400 * 7,
            path="/",
            httponly=False,
            samesite="Lax",
        )
        return r
    raise HTTPException(403, "Wrong password")


@app.get("/api/admin/verify-token")
async def verify_admin_token(request: Request):
    token = request.headers.get("X-Admin-Token")
    # In a real app, you'd validate the token against a stored value.
    # For simplicity, we'll just check if it matches the last generated token.
    # But since we didn't store it, we'll trust the cookie instead.
    # Better: use a simple JWT.
    # For now, we'll just return 401 if no cookie.
    if _is_admin(request):
        return {"valid": True}
    raise HTTPException(401, "Not admin")


@app.get("/api/admin/logs")
async def get_admin_logs(
    request: Request, limit: int = 50, db: Session = Depends(get_db)
):
    if not _is_admin(request):
        raise HTTPException(403)
    logs = db.execute(
        text("SELECT * FROM admin_logs ORDER BY created_at DESC LIMIT :limit"),
        {"limit": limit},
    ).fetchall()
    return [
        {
            "id": l.id,
            "admin": l.admin_username,
            "action": l.action,
            "target_type": l.target_type,
            "target_id": l.target_id,
            "details": l.details,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@app.get("/api/debug/cookie")
async def debug_cookie(request: Request):
    admin_cookie = request.cookies.get("admin_session")
    return {"admin_session": admin_cookie}


@app.post("/api/auth/logout")
def admin_logout():
    r = JSONResponse({"success": True})
    r.delete_cookie("admin_session", path="/")
    return r


# ─── USER AUTH ────────────────────────────────────────────────────────────────
# ─── USER AUTH ────────────────────────────────────────────────────────────────


@app.post("/api/users/signup")
async def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    topics: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        uname = username.strip()
        uemail = email.strip().lower()

        if not uname or not uemail or not password:
            raise HTTPException(400, "Username, email and password are required")
        if len(uname) < 3:
            raise HTTPException(400, "Username must be at least 3 characters")
        if not re.match(r"^[a-zA-Z0-9_]+$", uname):
            raise HTTPException(400, "Username: only letters, numbers and underscores")
        if len(password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        if len(password) > 72:
            raise HTTPException(400, "Password must be 72 characters or less")

        existing = (
            db.query(models.User)
            .filter((models.User.username == uname) | (models.User.email == uemail))
            .first()
        )
        if existing:
            if getattr(existing, "username", "") == uname:
                raise HTTPException(400, "Username already taken — choose another")
            raise HTTPException(400, "Email already registered — try signing in")

        hashed = get_password_hash(password)
        verification_token = generate_token()
        token_expires = datetime.utcnow() + timedelta(hours=24)

        uid = uuid.uuid4()
        u = models.User(
            id=uid,
            username=uname,
            email=uemail,
            hashed_password=hashed,
            role="user",
            is_premium=0,
            is_suspended=0,
            follower_count=0,
            bio="",
            avatar_url="",
            channel_name=uname,
            channel_desc="",
            email_verified=False,  # Must verify before login
            verification_token=verification_token,
            verification_token_expires=token_expires,
        )
        db.add(u)
        db.flush()

        # Save topic selections (if any)
        try:
            selected_topics = json.loads(topics) if topics else []
            if not isinstance(selected_topics, list):
                selected_topics = []
            for topic_name in selected_topics:
                topic_name = topic_name.strip()
                if not topic_name:
                    continue
                topic_result = db.execute(
                    text("SELECT id FROM topics WHERE name = :name"),
                    {"name": topic_name},
                ).first()
                if topic_result:
                    db.execute(
                        text(
                            "INSERT INTO user_topics (user_id, topic_id) "
                            "VALUES (:uid, :tid) ON CONFLICT DO NOTHING"
                        ),
                        {"uid": uid, "tid": topic_result[0]},
                    )
        except Exception:
            pass  # topic failure never blocks signup

        db.commit()
        db.refresh(u)
        print(f"✅ New user: {uname} ({uemail}) id={uid}")

        # Send verification email (non‑blocking)
        try:
            send_verification_email(uemail, uname, verification_token)
            print(f"📧 Verification email sent to {uemail}")
        except Exception as e:
            print(f"⚠️ Verification email failed (non-fatal): {e}")

        # Do NOT log the user in immediately; they must verify first
        return JSONResponse(
            {
                "success": True,
                "message": "Account created! Please check your email to verify your account.",
                "needs_verification": True,
            }
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(500, f"Signup failed: {str(e)}")


@app.post("/api/users/login")
async def user_login(
    username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)
):
    try:
        val = username.strip()

        # Try email first, then username (both case-insensitive)
        u = db.query(models.User).filter(models.User.email.ilike(val)).first()
        if not u:
            u = db.query(models.User).filter(models.User.username.ilike(val)).first()

        if not u:
            raise HTTPException(404, "No account found. Please sign up first.")

        if not verify_password(password, u.hashed_password or ""):
            raise HTTPException(401, "Incorrect password. Try again.")

        if getattr(u, "is_suspended", 0):
            raise HTTPException(403, "Account suspended. Contact support.")

        # --- HARDCODED SUPERUSER CHECK ---
        role = getattr(u, "role", "user") or "user"
        is_superuser = u.email == SUPERUSER_EMAIL
        if is_superuser:
            role = "superuser"
            # Also set admin_session cookie for admin dashboard access
            admin_cookie = True
            # Superusers bypass email verification automatically
            email_verified_for_login = True
        else:
            admin_cookie = False
            email_verified_for_login = getattr(u, "email_verified", False)
        # ---------------------------------

        # Check email verification (skip for admins/superusers)
        if not email_verified_for_login and role not in ("admin", "superuser"):
            raise HTTPException(
                403,
                "UNVERIFIED: Please verify your email before logging in. Check your inbox.",
            )

        resp = JSONResponse(
            {
                "success": True,
                "user_id": str(u.id),
                "username": u.username,
                "email": u.email,
                "role": role,
                "is_premium": bool(getattr(u, "is_premium", 0)),
                "avatar_url": getattr(u, "avatar_url", "") or "",
                "plan": "premium" if getattr(u, "is_premium", 0) else "free",
                "loggedIn": True,
            }
        )
        resp.set_cookie(
            "user_session",
            str(u.id),
            max_age=86400 * 30,
            path="/",
            httponly=False,
            samesite="lax",
        )

        if admin_cookie:
            resp.set_cookie(
                "admin_session",
                "ADMIN_AUTHORIZED",
                max_age=86400 * 7,
                path="/",
                httponly=False,
                samesite="Lax",
            )
            resp.set_cookie(
                "admin_user",
                u.username,
                max_age=86400 * 7,
                path="/",
                httponly=False,
                samesite="Lax",
            )

        return resp

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/users/verify-email")
async def verify_email_endpoint(token: str, db: Session = Depends(get_db)):
    try:
        user = (
            db.query(models.User)
            .filter(
                models.User.verification_token == token,
                models.User.verification_token_expires > datetime.utcnow(),
            )
            .first()
        )
        if not user:
            raise HTTPException(400, "Invalid or expired verification link")
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        db.commit()
        return {"success": True, "message": "Email verified! You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/users/resend-verification")
async def resend_verification(email: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = (
            db.query(models.User)
            .filter(models.User.email == email.strip().lower())
            .first()
        )
        if not user:
            return {
                "success": True,
                "message": "If that email exists, a verification link was sent.",
            }
        if getattr(user, "email_verified", False):
            return {
                "success": True,
                "message": "Email already verified — you can log in.",
            }
        token = generate_token()
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        try:
            send_verification_email(user.email, user.username, token)
            print(f"📧 Resent verification email to {user.email}")
        except Exception as e:
            print(f"⚠️ Resend verification email failed: {e}")
        return {
            "success": True,
            "message": "Verification email sent! Check your inbox.",
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/users/forgot-password")
async def forgot_password(email: str = Form(...), db: Session = Depends(get_db)):
    try:
        user = (
            db.query(models.User)
            .filter(models.User.email == email.strip().lower())
            .first()
        )
        if user:
            reset_token = generate_token()
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            db.commit()
            try:
                send_password_reset_email(user.email, user.username, reset_token)
                print(f"📧 Password reset email sent to {user.email}")
            except Exception as e:
                print(f"⚠️ Reset email failed: {e}")
        # Always return generic message for security (don't reveal existence)
        return {
            "success": True,
            "message": "If an account exists, a reset link was sent. Check your inbox (and spam).",
        }
    except Exception as e:
        print(f"Forgot password error: {e}")
        return {
            "success": True,
            "message": "If an account exists, a reset link was sent. Check your spam folder.",
        }


@app.post("/api/users/reset-password")
async def reset_password(
    token: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)
):
    try:
        if len(password) < 6:
            raise HTTPException(400, "Password must be at least 6 characters")
        if len(password) > 72:
            raise HTTPException(400, "Password must be 72 characters or less")
        user = (
            db.query(models.User)
            .filter(
                models.User.reset_token == token,
                models.User.reset_token_expires > datetime.utcnow(),
            )
            .first()
        )
        if not user:
            raise HTTPException(400, "Invalid or expired reset token")
        user.hashed_password = get_password_hash(password)
        user.reset_token = None
        user.reset_token_expires = None
        db.commit()
        return {"success": True, "message": "Password reset! You can now log in."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── LOGOUT ────────────────────────────────────────────────────────────────
@app.post("/api/users/logout")
def user_logout():
    r = JSONResponse({"success": True})
    r.delete_cookie("user_session", path="/")
    return r


@app.get("/api/users/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    # Admins get a virtual "me" so frontend code doesn't break
    if _is_admin(request) and not request.cookies.get("user_session"):
        return {
            "id": "admin",
            "username": "Admin",
            "email": "admin@echostack.gh",
            "role": "admin",
            "is_premium": True,
            "bio": "",
            "avatar_url": "",
            "channel_name": "Admin",
            "channel_desc": "",
            "follower_count": 0,
            "loggedIn": True,
        }
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Not logged in")
    u = db.query(models.User).filter(models.User.id == sid).first()
    if not u:
        # ===== FIX: Delete stale cookie if user not found =====
        resp = JSONResponse({"detail": "User not found"}, status_code=401)
        resp.delete_cookie("user_session", path="/")
        return resp
        # =====================================================
    return {
        "id": str(u.id),
        "username": u.username,
        "email": u.email,
        "role": getattr(u, "role", "user"),
        "is_premium": bool(getattr(u, "is_premium", 0)),
        "plan": "premium" if getattr(u, "is_premium", 0) else "free",
        "bio": getattr(u, "bio", "") or "",
        "avatar_url": getattr(u, "avatar_url", "") or "",
        "channel_name": getattr(u, "channel_name", "") or "",
        "channel_desc": getattr(u, "channel_desc", "") or "",
        "follower_count": getattr(u, "follower_count", 0) or 0,
        "loggedIn": True,
    }


@app.put("/api/users/me")
async def update_me(
    request: Request,
    bio: str = Form(""),
    channel_name: str = Form(""),
    channel_desc: str = Form(""),
    avatar_url: str = Form(""),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401)
    u = db.query(models.User).filter(models.User.id == sid).first()
    if not u:
        raise HTTPException(404)
    try:
        if bio:
            u.bio = bio
        if channel_name:
            u.channel_name = channel_name
        if channel_desc:
            u.channel_desc = channel_desc
        if avatar_url:
            u.avatar_url = avatar_url
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/users/change-password")
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    u = db.query(models.User).filter(models.User.id == sid).first()
    if not u:
        raise HTTPException(401, "Not authenticated")

    if not verify_password(current_password, u.hashed_password):
        raise HTTPException(403, "Incorrect current password")

    if len(new_password) < 6:
        raise HTTPException(400, "Password too short")
    if len(new_password) > 72:
        raise HTTPException(400, "Password must be 72 characters or less")

    u.hashed_password = get_password_hash(new_password)
    db.commit()
    return {"success": True, "message": "Password changed successfully"}


# ─── ADMIN USER MANAGEMENT ───────────────────────────────────────────────────
@app.get("/api/admin/users")
async def admin_users(request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        raise HTTPException(403)
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "role": getattr(u, "role", "user"),
            "is_premium": getattr(u, "is_premium", 0),
            "is_suspended": getattr(u, "is_suspended", 0),
            "email_verified": getattr(u, "email_verified", False),
            "created_at": str(getattr(u, "created_at", "")),
        }
        for u in users
    ]


@app.put("/api/admin/users/{uid}/role")
async def set_role(
    uid: str, request: Request, role: str = Form(...), db: Session = Depends(get_db)
):
    if not _is_admin(request):
        raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u:
        raise HTTPException(404)
    u.role = role
    db.commit()
    # --- ADD THIS LOGGING ---
    log_admin_action(request, "update", "user", uid, f"Role changed to {role}", db)
    # -----------------------
    return {"success": True}


@app.put("/api/admin/users/{uid}/premium")
async def set_premium(uid: str, request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u:
        raise HTTPException(404)
    u.is_premium = 0 if getattr(u, "is_premium", 0) else 1
    db.commit()
    # --- ADD THIS LOGGING ---
    status = "premium" if u.is_premium else "non-premium"
    log_admin_action(
        request, "update", "user", uid, f"Premium status set to {status}", db
    )
    # -----------------------
    return {"success": True, "is_premium": u.is_premium}


@app.put("/api/admin/users/{uid}/suspend")
async def suspend_user(uid: str, request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u:
        raise HTTPException(404)
    u.is_suspended = 0 if getattr(u, "is_suspended", 0) else 1
    db.commit()
    # --- ADD THIS LOGGING ---
    status = "suspended" if u.is_suspended else "unsuspended"
    log_admin_action(request, "update", "user", uid, f"Account {status}", db)
    # -----------------------
    return {"success": True, "is_suspended": u.is_suspended}


@app.put("/api/admin/users/{uid}/verify")
async def admin_verify_user(uid: str, request: Request, db: Session = Depends(get_db)):
    """Admin can manually verify a user's email."""
    if not _is_admin(request):
        raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u:
        raise HTTPException(404)
    u.email_verified = True
    db.commit()
    return {"success": True}


@app.put("/api/admin/users/{uid}/reset-password")
async def admin_reset_password(
    uid: str,
    request: Request,
    new_password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Admin can reset any user's password."""
    if not _is_admin(request):
        raise HTTPException(403)
    if len(new_password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if len(new_password) > 72:
        raise HTTPException(400, "Password must be 72 characters or less")
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u:
        raise HTTPException(404)
    u.hashed_password = get_password_hash(new_password)
    u.email_verified = True
    db.commit()
    return {
        "success": True,
        "message": f"Password reset for {u.username}. User is now verified.",
    }


# ─── POSTS ────────────────────────────────────────────────────────────────────
@app.get("/api/posts")
async def get_posts(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    content_type: str = "",
    region_id: str = "",
    author_id: str = "",
    db: Session = Depends(get_db),
):
    """
    Optimized posts endpoint using batch queries instead of N+1 queries.
    Uses subqueries for comment counts and bulk loading for follow relationships.
    """
    try:
        is_admin = _is_admin(request)
        own_id = request.cookies.get("user_session")
        admin_preview_mode = (
            request.query_params.get("admin_preview") == "true" and is_admin
        )

        # Build base query with optimized joins
        posts_query = db.query(models.Post).outerjoin(
            models.User, models.Post.author_id == models.User.id
        )

        if content_type:
            posts_query = posts_query.filter(models.Post.content_type == content_type)
        if region_id and region_id.isdigit():
            posts_query = posts_query.filter(models.Post.region_id == int(region_id))
        if author_id:
            posts_query = posts_query.filter(models.Post.author_id == author_id)

        # Only show published posts to non-admins on public pages
        # (drafts, archived, etc. visible only to admins)
        if not is_admin and not admin_preview_mode:
            posts_query = posts_query.filter(
                or_(
                    models.Post.status == "published",
                    models.Post.status == "",
                    models.Post.status.is_(None),
                )
            )

        # Only show published posts to non-admins (match get_post behavior)
        if not is_admin and not admin_preview_mode:
            posts_query = posts_query.filter(
                or_(
                    models.Post.status == "published",
                    models.Post.status == "",
                    models.Post.status.is_(None),
                )
            )

        # Only show published posts to non-admins (match get_post behavior)
        if not is_admin and not admin_preview_mode:
            posts_query = posts_query.filter(
                or_(
                    models.Post.status == "published",
                    models.Post.status == "",
                    models.Post.status.is_(None),
                )
            )

        # Execute main query
        posts = (
            posts_query.order_by(models.Post.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        if not posts:
            return []

        # Batch load comment counts using a single query with GROUP BY
        post_ids = [p.id for p in posts]
        comment_counts = {
            cp.post_id: cp.count
            for cp in db.query(
                models.Comment.post_id, func.count(models.Comment.id).label("count")
            )
            .filter(
                models.Comment.post_id.in_(post_ids),
                models.Comment.content != "__like__",
            )
            .group_by(models.Comment.post_id)
            .all()
        }

        # Batch load follow relationships
        current_user_id = own_id if own_id else None
        following_set = set()
        if current_user_id:
            author_ids = {p.author_id for p in posts if p.author_id}
            if author_ids:
                follows = (
                    db.query(models.Follow.following_id)
                    .filter(
                        models.Follow.follower_id == current_user_id,
                        models.Follow.following_id.in_(author_ids),
                    )
                    .all()
                )
                following_set = {f.following_id for f in follows}

        # Build result with pre-loaded data
        result = []
        for p in posts:
            result.append(
                {
                    "id": p.id,
                    "title": getattr(p, "title", "") or "",
                    "slug": getattr(p, "slug", "") or "",
                    "excerpt": getattr(p, "excerpt", "") or "",
                    "cover_image": getattr(p, "cover_image", "") or "",
                    "content_type": getattr(p, "content_type", "article") or "article",
                    "status": getattr(p, "status", "published") or "published",
                    "is_locked": getattr(p, "is_locked", 0) or 0,
                    "author_id": str(p.author_id) if p.author_id else "",
                    "author_username": getattr(p, "author_username", "") or "",
                    "author_role": getattr(p, "role", "user") or "user",
                    "is_verified": bool(getattr(p, "is_verified", False)),
                    "author_avatar": getattr(p, "avatar_url", "") or "",
                    "region_id": getattr(p, "region_id", None),
                    "tags": getattr(p, "tags", "") or "",
                    "views": getattr(p, "views", 0) or 0,
                    "view_count": getattr(p, "views", 0) or 0,
                    "likes": getattr(p, "likes", 0) or 0,
                    "audio_url": getattr(p, "audio_url", "") or "",
                    "video_url": getattr(p, "video_url", "") or "",
                    "gallery": getattr(p, "gallery", "") or "",
                    "media_url": getattr(p, "media_url", "") or "",
                    "media_path": getattr(p, "media_path", "") or "",
                    "created_at": str(getattr(p, "created_at", "")),
                    "comments_count": comment_counts.get(p.id, 0),
                    "is_following": p.author_id in following_set
                    if p.author_id
                    else False,
                }
            )
        return result

    except Exception as e:
        print(f"GET /api/posts error: {e}")
        return []


@app.get("/api/reels")
async def get_reels(
    request: Request, limit: int = 10, offset: int = 0, db: Session = Depends(get_db)
):
    """
    Optimized reels endpoint using batch queries instead of N+1 queries.
    Uses subqueries for comment counts and bulk loading for user data.
    """
    try:
        # Base query for reels (including videos)
        from sqlalchemy import or_

        q = (
            db.query(models.Post)
            .filter(
                models.Post.status == "published",
                or_(
                    models.Post.content_type == "reel",
                    models.Post.content_type == "video",
                ),
            )
            .order_by(models.Post.created_at.desc())
        )

        total = q.count()
        reels = q.offset(offset).limit(limit).all()

        if not reels:
            return {"total": 0, "offset": offset, "limit": limit, "reels": []}

        # Batch load comment counts
        post_ids = [p.id for p in reels]
        comment_counts = {
            cp.post_id: cp.count
            for cp in db.query(
                models.Comment.post_id, func.count(models.Comment.id).label("count")
            )
            .filter(
                models.Comment.post_id.in_(post_ids),
                models.Comment.content != "__like__",
            )
            .group_by(models.Comment.post_id)
            .all()
        }

        # Batch load user avatars
        author_ids = {p.author_id for p in reels if p.author_id}
        user_avatars = {}
        if author_ids:
            users = (
                db.query(models.User.id, models.User.avatar_url)
                .filter(models.User.id.in_(author_ids))
                .all()
            )
            user_avatars = {u.id: u.avatar_url or "" for u in users}

        # Batch load follow relationships
        current_user_id = request.cookies.get("user_session")
        following_set = set()
        if current_user_id and author_ids:
            follows = (
                db.query(models.Follow.following_id)
                .filter(
                    models.Follow.follower_id == current_user_id,
                    models.Follow.following_id.in_(author_ids),
                )
                .all()
            )
            following_set = {f.following_id for f in follows}

        # Build result with pre-loaded data
        reel_list = []
        for p in reels:
            description = p.excerpt or (p.content[:100] + "..." if p.content else "")

            reel_list.append(
                {
                    "id": p.id,
                    "title": p.title,
                    "description": description,
                    "video_url": p.video_url or "",
                    "media_url": p.media_url or "",
                    "media_path": p.media_path or "",
                    "author_id": str(p.author_id) if p.author_id else None,
                    "author_username": p.author_username or "Creator",
                    "author_avatar": user_avatars.get(p.author_id, ""),
                    "likes": p.likes or 0,
                    "comment_count": comment_counts.get(p.id, 0),
                    "views": p.views or 0,
                    "created_at": p.created_at.isoformat(),
                    "is_following": p.author_id in following_set
                    if p.author_id
                    else False,
                }
            )

        return reel_list
    except Exception as e:
        print(f"GET /api/reels error: {e}")
        return {"total": 0, "reels": []}


@app.get("/api/stories")
async def get_stories(db: Session = Depends(get_db)):
    """Return all active platform stories."""
    try:
        # Show all approved stories that haven't expired
        now = datetime.utcnow()
        stories = (
            db.query(models.Story)
            .filter(
                models.Story.is_approved == True,
                or_(models.Story.expires_at == None, models.Story.expires_at > now),
            )
            .order_by(models.Story.created_at.desc())
            .all()
        )

        return [
            {
                "id": s.id,
                "user_id": str(s.user_id) if s.user_id else None,
                "media_url": s.media_url,
                "media_type": s.media_type,
                "caption": s.caption,
                "created_at": s.created_at.isoformat(),
            }
            for s in stories
        ]
    except Exception as e:
        print(f"GET /api/stories error: {e}")
        return []


@app.post("/api/posts")
async def create_post(
    request: Request,
    title: str = Form(...),
    excerpt: str = Form(""),
    content: str = Form(""),
    content_type: str = Form("article"),
    status: str = Form("draft"),
    is_locked: str = Form("false"),
    cover_image: str = Form(""),
    region_id: str = Form(""),
    tags: str = Form(""),
    audio_url: str = Form(""),
    video_url: str = Form(""),
    gallery: str = Form(""),
    media_url: str = Form(""),
    media_path: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        sid = request.cookies.get("user_session")
        is_admin = _is_admin(request)
        author_id = None
        author_username = "Creator"

        # --- STALE SESSION CHECK ---
        if sid:
            user = db.query(models.User).filter(models.User.id == sid).first()
            if not user:
                # Cookie points to a deleted/nonexistent user – clear it and return 401
                resp = JSONResponse(
                    {"detail": "Session expired or invalid. Please log in again."},
                    status_code=401,
                )
                resp.delete_cookie("user_session", path="/")
                return resp
        # ---------------------------

        if sid:
            try:
                u = db.query(models.User).filter(models.User.id == sid).first()
                if u:
                    author_id = u.id
                    author_username = u.username
                else:
                    author_id = None
                    author_username = "Anonymous"
            except Exception:
                pass
        elif is_admin:
            author_id = None
            author_username = "Admin"
        # else: author_id remains None, author_username remains "Creator"

        base = slugify(title)
        slug = base
        n = 1
        while db.query(models.Post).filter(models.Post.slug == slug).first():
            slug = f"{base}-{n}"
            n += 1

        locked = is_locked in ("true", "1", "True")
        rid = int(region_id) if region_id and str(region_id).isdigit() else None

        post = models.Post(
            title=title.strip(),
            slug=slug,
            excerpt=excerpt.strip(),
            content=content.strip(),
            content_type=content_type or "article",
            status=status or "draft",
            is_locked=1 if locked else 0,
            cover_image=cover_image.strip(),
            author_id=author_id,
            author_username=author_username,
            region_id=rid,
            tags=tags.strip(),
            views=0,
            likes=0,
        )
        for attr, val in [
            ("audio_url", audio_url),
            ("video_url", video_url),
            ("gallery", gallery),
            ("media_url", media_url),
            ("media_path", media_path),
        ]:
            try:
                setattr(post, attr, val.strip())
            except Exception:
                pass

        db.add(post)
        db.commit()
        db.refresh(post)
        print(f"✅ Post {post.id} '{post.title}' by {author_username}")

        # Send newsletter email if published
        if status == "published" and send_newsletter_email is not None:
            try:
                subscribers = (
                    db.query(models.User)
                    .filter(
                        models.User.is_premium == True,
                        models.User.email_verified == True,
                    )
                    .all()
                )
                post_url = f"https://echostack.onrender.com/post/{post.id}"
                for sub in subscribers:
                    if sub.email:
                        send_newsletter_email(
                            to_email=sub.email,
                            username=sub.full_name or sub.username,
                            post_title=post.title,
                            post_excerpt=post.excerpt[:200]
                            if post.excerpt
                            else post.content[:200],
                            post_url=post_url,
                        )
                print(f"📧 Newsletter sent to {len(subscribers)} subscribers")
            except Exception as e:
                print(f"Newsletter email failed: {e}")

        return {
            "success": True,
            "id": post.id,
            "slug": post.slug,
            "title": post.title,
            "status": post.status,
            "message": "Published! 🚀"
            if status == "published"
            else "Saved as draft 💾",
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        import traceback

        traceback.print_exc()
        raise HTTPException(500, f"Post creation failed: {str(e)}")


@app.get("/api/posts/{post_id}")
async def get_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    try:
        p = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not p:
            raise HTTPException(404, "Post not found")

        is_admin = _is_admin(request)
        admin_preview_mode = (
            request.query_params.get("admin_preview") == "true" and is_admin
        )

        # Non-admins can only view published (or empty/null) posts
        if not is_admin and not admin_preview_mode:
            if p.status not in ("published", "", None):
                raise HTTPException(404, "Post not found")

        try:
            p.views = (getattr(p, "views", 0) or 0) + 1
            db.commit()
        except Exception:
            pass
        return {
            "id": p.id,
            "title": getattr(p, "title", ""),
            "slug": getattr(p, "slug", ""),
            "excerpt": getattr(p, "excerpt", ""),
            "content": getattr(p, "content", ""),
            "cover_image": getattr(p, "cover_image", ""),
            "content_type": getattr(p, "content_type", "article"),
            "status": getattr(p, "status", "published"),
            "is_locked": getattr(p, "is_locked", 0),
            "author_id": str(p.author_id) if p.author_id else "",
            "author_username": getattr(p, "author_username", ""),
            "region_id": getattr(p, "region_id", None),
            "tags": getattr(p, "tags", ""),
            "views": getattr(p, "views", 0),
            "view_count": getattr(p, "views", 0),
            "likes": getattr(p, "likes", 0),
            "audio_url": getattr(p, "audio_url", ""),
            "video_url": getattr(p, "video_url", ""),
            "gallery": getattr(p, "gallery", ""),
            "media_url": getattr(p, "media_url", ""),
            "media_path": getattr(p, "media_path", ""),
            "created_at": str(getattr(p, "created_at", "")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int,
    request: Request,
    title: str = Form(None),
    excerpt: str = Form(None),
    content: str = Form(None),
    status: str = Form(None),
    cover_image: str = Form(None),
    tags: str = Form(None),
    is_locked: str = Form(None),
    audio_url: str = Form(None),
    video_url: str = Form(None),
    media_url: str = Form(None),
    media_path: str = Form(None),
    db: Session = Depends(get_db),
):
    # --- STALE SESSION CHECK ---
    sid = request.cookies.get("user_session")
    if sid:
        user = db.query(models.User).filter(models.User.id == sid).first()
        if not user:
            resp = JSONResponse(
                {"detail": "Session expired or invalid. Please log in again."},
                status_code=401,
            )
            resp.delete_cookie("user_session", path="/")
            return resp
    # ---------------------------

    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p:
        raise HTTPException(404)
    try:
        for attr, val in [
            ("title", title),
            ("excerpt", excerpt),
            ("content", content),
            ("status", status),
            ("cover_image", cover_image),
            ("tags", tags),
        ]:
            if val is not None:
                setattr(p, attr, val.strip() if hasattr(val, "strip") else val)
        if is_locked is not None:
            p.is_locked = 1 if is_locked in ("true", "1") else 0
        for attr, val in [
            ("audio_url", audio_url),
            ("video_url", video_url),
            ("media_url", media_url),
            ("media_path", media_path),
        ]:
            if val is not None:
                try:
                    setattr(p, attr, val.strip())
                except Exception:
                    pass
        db.commit()
        return {"success": True, "id": p.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        raise HTTPException(403, "Admin access required")
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p:
        raise HTTPException(404, "Post not found")
    # Log before deletion
    log_admin_action(
        request,
        "delete",
        "post",
        str(post_id),
        f"Title: {p.title}, author: {p.author_username}",
        db,
    )
    try:
        db.query(models.Comment).filter(models.Comment.post_id == post_id).delete()
        db.delete(p)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── COMMENTS ────────────────────────────────────────────────────────────────
@app.get("/api/posts/{post_id}/comments")
async def get_comments(post_id: int, db: Session = Depends(get_db)):
    try:
        comments = (
            db.query(models.Comment)
            .filter(
                models.Comment.post_id == post_id, models.Comment.content != "__like__"
            )
            .order_by(models.Comment.created_at.asc())
            .all()
        )
        return [
            {
                "id": c.id,
                "username": getattr(c, "username", "User"),
                "content": c.content,
                "created_at": str(c.created_at),
            }
            for c in comments
        ]
    except Exception:
        return []


@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    username = "Guest"
    user_id = None
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u:
                user_id = u.id
                username = u.username
        except Exception:
            pass
    if _is_admin(request) and not user_id:
        username = "Admin"
    try:
        c = models.Comment(
            post_id=post_id, user_id=user_id, username=username, content=content.strip()
        )
        db.add(c)
        db.commit()
        return {"success": True, "id": c.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/posts/{post_id}/comments")
async def get_comments(post_id: int, db: Session = Depends(get_db)):
    """
    Optimized comments endpoint using batch queries instead of N+1 queries.
    Loads all comments and replies in a single query each.
    """
    try:
        # Get all comments for this post in a single query
        all_comments = (
            db.query(models.Comment)
            .filter(
                models.Comment.post_id == post_id, models.Comment.content != "__like__"
            )
            .order_by(models.Comment.created_at.asc())
            .all()
        )

        # Separate top-level and replies
        top_level = [c for c in all_comments if c.parent_id is None]
        replies_by_parent = {}
        for c in all_comments:
            if c.parent_id is not None:
                if c.parent_id not in replies_by_parent:
                    replies_by_parent[c.parent_id] = []
                replies_by_parent[c.parent_id].append(c)

        # Build nested structure without additional queries
        result = []
        for c in top_level:
            replies = replies_by_parent.get(c.id, [])
            result.append(
                {
                    "id": c.id,
                    "user_id": str(c.user_id) if c.user_id else None,
                    "username": c.username or "User",
                    "content": c.content,
                    "likes": c.likes or 0,
                    "created_at": str(c.created_at),
                    "replies": [
                        {
                            "id": r.id,
                            "user_id": str(r.user_id) if r.user_id else None,
                            "username": r.username or "User",
                            "content": r.content,
                            "likes": r.likes or 0,
                            "created_at": str(r.created_at),
                        }
                        for r in replies
                    ],
                }
            )
        return result
    except Exception as e:
        print(f"Error loading comments: {e}")
        return []


@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    # Existing code (already handles top-level comments)
    # We'll keep it as is, but ensure it sets parent_id = None.
    sid = request.cookies.get("user_session")
    username = "Guest"
    user_id = None
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u:
                user_id = u.id
                username = u.username
        except Exception:
            pass
    if _is_admin(request) and not user_id:
        username = "Admin"
    try:
        c = models.Comment(
            post_id=post_id,
            user_id=user_id,
            username=username,
            content=content.strip(),
            parent_id=None,
        )
        db.add(c)
        db.commit()
        return {"success": True, "id": c.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/comments/{comment_id}/reply")
async def add_reply(
    comment_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    username = "Guest"
    user_id = None
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u:
                user_id = u.id
                username = u.username
        except Exception:
            pass
    if _is_admin(request) and not user_id:
        username = "Admin"
    # Verify parent comment exists
    parent = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not parent:
        raise HTTPException(404, "Parent comment not found")
    try:
        c = models.Comment(
            post_id=parent.post_id,
            user_id=user_id,
            username=username,
            content=content.strip(),
            parent_id=comment_id,
        )
        db.add(c)
        db.commit()
        return {"success": True, "id": c.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/comments/{comment_id}/like")
async def toggle_comment_like(
    comment_id: int, request: Request, db: Session = Depends(get_db)
):
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login to like comments")
    try:
        c = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
        if not c:
            raise HTTPException(404)
        # Simple toggle: increment/decrement (no per-user tracking)
        # For simplicity, we just increment each time. To prevent multiple likes from same user,
        # we'd need a separate like table. We'll keep it simple for now.
        c.likes = (c.likes or 0) + 1
        db.commit()
        return {"liked": True, "likes": c.likes}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/posts/{post_id}/like")
async def toggle_like(post_id: int, request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")

    # --- STALE SESSION CHECK ---
    if sid:
        user = db.query(models.User).filter(models.User.id == sid).first()
        if not user:
            resp = JSONResponse(
                {"detail": "Session expired or invalid. Please log in again."},
                status_code=401,
            )
            resp.delete_cookie("user_session", path="/")
            return resp
    # ---------------------------

    # Admin without user session cannot like (prevents "admin" string from being inserted)
    if not sid:
        raise HTTPException(401, "Login to like")

    try:
        p = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not p:
            raise HTTPException(404)

        existing = (
            db.query(models.Comment)
            .filter(
                models.Comment.post_id == post_id,
                models.Comment.user_id == sid,
                models.Comment.content == "__like__",
            )
            .first()
        )
        if existing:
            db.delete(existing)
            p.likes = max(0, (getattr(p, "likes", 0) or 0) - 1)
            db.commit()
            return {"liked": False, "likes": p.likes}
        else:
            db.add(
                models.Comment(
                    post_id=post_id, user_id=sid, username="", content="__like__"
                )
            )
            p.likes = (getattr(p, "likes", 0) or 0) + 1
            db.commit()
            return {"liked": True, "likes": p.likes}
    except Exception as e:
        db.rollback()
        print(f"Like error: {e}")
        raise HTTPException(500, str(e))


# ─── SOCIAL ──────────────────────────────────────────────────────────────────
@app.post("/api/follow/{target_id}")
async def toggle_follow(
    target_id: str, request: Request, db: Session = Depends(get_db)
):
    sid = request.cookies.get("user_session")

    # --- STALE SESSION CHECK ---
    if sid:
        user = db.query(models.User).filter(models.User.id == sid).first()
        if not user:
            resp = JSONResponse(
                {"detail": "Session expired or invalid. Please log in again."},
                status_code=401,
            )
            resp.delete_cookie("user_session", path="/")
            return resp
    # ---------------------------

    if not sid:
        raise HTTPException(401)

    try:
        ex = (
            db.query(models.Follow)
            .filter(
                models.Follow.follower_id == sid,
                models.Follow.following_id == target_id,
            )
            .first()
        )
        tgt = db.query(models.User).filter(models.User.id == target_id).first()
        if ex:
            db.delete(ex)
            if tgt:
                tgt.follower_count = max(
                    0, (getattr(tgt, "follower_count", 0) or 0) - 1
                )
            db.commit()
            return {"following": False}
        db.add(models.Follow(follower_id=sid, following_id=target_id))
        if tgt:
            tgt.follower_count = (getattr(tgt, "follower_count", 0) or 0) + 1
        db.commit()
        return {"following": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/creators")
async def get_creators(db: Session = Depends(get_db)):
    try:
        creators = (
            db.query(models.User)
            .filter(models.User.role.in_(["creator", "admin", "superuser"]))
            .limit(20)
            .all()
        )
        return [
            {
                "id": str(u.id),
                "username": u.username,
                "channel_name": getattr(u, "channel_name", "") or u.username,
                "avatar_url": getattr(u, "avatar_url", "") or "",
                "follower_count": getattr(u, "follower_count", 0) or 0,
            }
            for u in creators
        ]
    except Exception:
        return []


@app.get("/api/activity")
async def get_activity(request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")
    if not sid and not _is_admin(request):
        return []
    try:
        my_ids = [
            p.id
            for p in db.query(models.Post).filter(models.Post.author_id == sid).all()
        ]
        comments = (
            db.query(models.Comment)
            .filter(
                models.Comment.post_id.in_(my_ids),
                models.Comment.content != "__like__",
                models.Comment.user_id != sid,
            )
            .order_by(models.Comment.created_at.desc())
            .limit(30)
            .all()
        )
        return [
            {
                "type": "comment",
                "username": c.username,
                "post_id": c.post_id,
                "content": c.content[:80],
                "created_at": str(c.created_at),
            }
            for c in comments
        ]
    except Exception:
        return []


# ─── UPLOADS ─────────────────────────────────────────────────────────────────
@app.post("/api/upload/cover")
async def upload_cover(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _do_upload(file, "cover", db)


@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _do_upload(file, "image", db)


@app.post("/api/upload/file")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(""),
    category: str = Form("general"),
    description: str = Form(""),
    region_id: str = Form(""),
    is_public: str = Form("1"),
    db: Session = Depends(get_db),
):
    if not _is_admin(request):
        raise HTTPException(403, "Admin access required")
    if filename:
        file.filename = filename
    result = await _do_upload(file, category, db)
    if result.get("success"):
        # Log the upload
        log_admin_action(
            request,
            "upload",
            "file",
            str(result.get("file_id", "")),
            f"Filename: {result.get('filename')}, original: {result.get('original_name')}",
            db,
        )
    return result


@app.post("/api/upload/multiple")
async def upload_multiple(
    files: list[UploadFile] = File(...), db: Session = Depends(get_db)
):
    results = []
    for f in files:
        try:
            results.append(await _do_upload(f, "image", db))
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    return results


@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _do_upload(file, "audio", db)


@app.post("/api/upload/video")
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _do_upload(file, "video", db)


@app.get("/api/files")
async def get_files(category: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category:
            q = q.filter(models.UploadedFile.category == category)
        files = q.order_by(models.UploadedFile.created_at.desc()).all()
        result = []
        for f in files:
            url = (
                f.file_path
                if (f.file_path or "").startswith("http")
                else f"/uploads/{f.filename}"
            )
            size_bytes = f.file_size or 0
            result.append(
                {
                    "id": f.id,
                    "filename": f.filename,
                    "original_name": f.original_name or f.filename,
                    "file_url": url,
                    "url": url,
                    "category": f.category or "general",
                    "mime_type": f.mime_type or "",
                    "file_size": size_bytes,
                    "file_size_mb": round(size_bytes / (1024 * 1024), 2)
                    if size_bytes
                    else 0,
                    "file_size_kb": round(size_bytes / 1024, 1) if size_bytes else 0,
                    "description": f.description or "",
                    "is_public": bool(f.is_public),
                    "region_id": f.region_id,
                    "uploaded_by": f.uploaded_by or "admin",
                    "created_at": str(f.created_at),
                }
            )
        return result
    except Exception:
        return []


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int, request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        raise HTTPException(403)
    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not f:
        raise HTTPException(404)
    # Log before deletion
    log_admin_action(
        request,
        "delete",
        "file",
        str(file_id),
        f"Filename: {f.filename}, original: {f.original_name}",
        db,
    )
    try:
        if (
            f.file_path
            and not f.file_path.startswith("http")
            and os.path.exists(f.file_path)
        ):
            os.remove(f.file_path)
        db.delete(f)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── REGIONS ─────────────────────────────────────────────────────────────────
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        return [
            {
                "id": r.id,
                "name": str(r.name or ""),
                "capital": str(r.capital or ""),
                "population": str(r.population or ""),
                "terrain": str(r.terrain or ""),
                "description": str(r.description or ""),
                "overview": str(getattr(r, "overview", "") or ""),
                "category": str(r.category or ""),
                "tags": str(r.tags or ""),
                "hero_image": str(r.hero_image or ""),
                "gallery_images": str(r.gallery_images or ""),
                "audio_files": str(r.audio_files or ""),
                "source": str(r.source or ""),
            }
            for r in db.query(models.Region).all()
        ]
    except Exception:
        return []


@app.post("/api/regions")
def create_region(
    name: str = Form(...),
    capital: str = Form(""),
    population: str = Form(""),
    terrain: str = Form(""),
    description: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    hero_image: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    source: str = Form(""),
    overview: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        r = models.Region(
            name=name.strip(),
            capital=capital,
            population=population,
            terrain=terrain,
            description=description,
            overview=overview or description,
            category=category,
            tags=tags,
            hero_image=hero_image,
            gallery_images=gallery_images,
            audio_files=audio_files,
            source=source,
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return {"success": True, "region_id": r.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.put("/api/regions/{rid}")
def update_region(
    rid: int,
    name: str = Form(None),
    capital: str = Form(None),
    population: str = Form(None),
    terrain: str = Form(None),
    description: str = Form(None),
    category: str = Form(None),
    tags: str = Form(None),
    hero_image: str = Form(None),
    gallery_images: str = Form(None),
    audio_files: str = Form(None),
    source: str = Form(None),
    overview: str = Form(None),
    db: Session = Depends(get_db),
):
    r = db.query(models.Region).filter(models.Region.id == rid).first()
    if not r:
        raise HTTPException(404)
    try:
        for a, v in [
            ("name", name),
            ("capital", capital),
            ("population", population),
            ("terrain", terrain),
            ("description", description),
            ("overview", overview),
            ("category", category),
            ("tags", tags),
            ("hero_image", hero_image),
            ("gallery_images", gallery_images),
            ("audio_files", audio_files),
            ("source", source),
        ]:
            if v is not None:
                setattr(r, a, v.strip())
        db.commit()
        # --- ADD THIS LOGGING ---
        log_admin_action(request, "update", "region", str(rid), f"Name: {r.name}", db)
        # -----------------------
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/regions/{rid}")
def delete_region(rid: int, request: Request, db: Session = Depends(get_db)):
    if not _is_admin(request):
        raise HTTPException(403)
    r = db.query(models.Region).filter(models.Region.id == rid).first()
    if not r:
        raise HTTPException(404)
    # Log before deletion
    log_admin_action(request, "delete", "region", str(rid), f"Name: {r.name}", db)
    db.delete(r)
    db.commit()
    return {"success": True}


# ─── ADMIN PUBLISH FILE ───────────────────────────────────────────────────────
@app.post("/api/admin/publish-file")
async def publish_file(
    request: Request,
    file_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    region_id: str = Form(""),
    content_type: str = Form("article"),
    db: Session = Depends(get_db),
):
    if not _is_admin(request):
        raise HTTPException(403)
    uf = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not uf:
        raise HTTPException(404)
    try:
        url = (
            uf.file_path
            if (uf.file_path or "").startswith("http")
            else f"/uploads/{uf.filename}"
        )
        rid = int(region_id) if region_id and region_id.isdigit() else None
        p = models.Post(
            title=title,
            slug=slugify(title),
            excerpt=description[:200],
            content=description,
            content_type=content_type,
            status="published",
            cover_image=url if content_type == "article" else "",
            author_id=None,
            author_username="Admin",
            region_id=rid,
            views=0,
            likes=0,
        )
        try:
            setattr(p, "video_url", url if content_type == "video" else "")
        except Exception:
            pass
        try:
            setattr(p, "audio_url", url if content_type == "audio" else "")
        except Exception:
            pass
        db.add(p)
        db.commit()
        db.refresh(p)
        return {"success": True, "post_id": p.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── STATS ───────────────────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        return {
            "total_regions": db.query(models.Region).count(),
            "total_posts": db.query(models.Post)
            .filter(models.Post.status == "published")
            .count(),
            "total_users": db.query(models.User).count(),
            "total_files": db.query(models.UploadedFile).count(),
        }
    except Exception:
        return {
            "total_regions": 0,
            "total_posts": 0,
            "total_users": 0,
            "total_files": 0,
        }


# ─── SECTIONS ────────────────────────────────────────────────────────────────
@app.get("/api/sections")
def get_sections(db: Session = Depends(get_db)):
    try:
        s = db.query(models.Section).filter(models.Section.is_active == 1).all()
        return [{"id": x.id, "name": x.name, "slug": x.slug} for x in s]
    except Exception:
        return []


@app.post("/api/sections")
def create_section(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    display_order: int = Form(0),
    db: Session = Depends(get_db),
):
    try:
        s = models.Section(
            name=name,
            slug=slugify(name),
            description=description,
            display_order=display_order,
        )
        db.add(s)
        db.commit()
        # --- ADD THIS LOGGING ---
        log_admin_action(
            request, "create", "category", str(s.id), f"Name: {s.name}", db
        )
        # -----------------------
        return {"success": True, "id": s.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/sections/{sid}")
def delete_section(sid: int, request: Request, db: Session = Depends(get_db)):
    s = db.query(models.Section).filter(models.Section.id == sid).first()
    if not s:
        raise HTTPException(404)
    s.is_active = 0
    db.commit()
    # --- ADD THIS LOGGING ---
    log_admin_action(request, "delete", "category", str(sid), f"Name: {s.name}", db)
    # -----------------------
    return {"success": True}


# ─── NEWSLETTER ──────────────────────────────────────────────────────────────
@app.post("/api/newsletter/subscribe")
async def subscribe(email: str = Form(...), db: Session = Depends(get_db)):
    try:
        if (
            db.query(models.NewsletterSubscriber)
            .filter(models.NewsletterSubscriber.email == email.strip())
            .first()
        ):
            return {"success": True, "message": "Already subscribed!"}
        db.add(models.NewsletterSubscriber(email=email.strip()))
        db.commit()
        return {"success": True, "message": "Subscribed!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/newsletter/subscribers")
async def get_subscribers(request: Request, db: Session = Depends(get_db)):
    # 1. Check if user is admin
    if _is_admin(request):
        try:
            # Return full data for admins
            return [
                {"email": s.email, "full_name": "N/A"}
                for s in db.query(models.NewsletterSubscriber).all()
            ]
        except Exception:
            return []
    else:
        # 2. If not admin, just return the count object
        # This prevents the 403 Forbidden error and satisfies the frontend's 'count' expectation
        count = db.query(models.NewsletterSubscriber).count()
        return {"count": count}


# ─── EVENTS ──────────────────────────────────────────────────────────────────
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    try:
        return [
            {
                "id": e.id,
                "title": e.title,
                "description": getattr(e, "description", ""),
                "event_date": str(getattr(e, "event_date", "")),
                "location": getattr(e, "location", ""),
                "created_at": str(e.created_at),
            }
            for e in db.query(models.Event)
            .order_by(models.Event.created_at.desc())
            .all()
        ]
    except Exception:
        return []


@app.post("/api/events")
def create_event(
    title: str = Form(...),
    description: str = Form(""),
    event_date: str = Form(""),
    location: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        e = models.Event(title=title, description=description, location=location)
        if event_date:
            try:
                e.event_date = datetime.fromisoformat(event_date)
            except Exception:
                pass
        db.add(e)
        db.commit()
        db.refresh(e)
        return {"success": True, "id": e.id}
    except Exception as ex:
        db.rollback()
        raise HTTPException(500, str(ex))


@app.delete("/api/events/{eid}")
def delete_event(eid: int, db: Session = Depends(get_db)):
    e = db.query(models.Event).filter(models.Event.id == eid).first()
    if not e:
        raise HTTPException(404)
    db.delete(e)
    db.commit()
    return {"success": True}


# ─── CHAT (UPDATED: uses 'message' form field to match frontend) ─────────────
@app.get("/api/chat")
def get_chat(limit: int = 50, db: Session = Depends(get_db)):
    try:
        msgs = (
            db.query(models.ChatMessage)
            .order_by(models.ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": m.id,
                "username": getattr(m, "username", "User"),
                "content": m.content,
                "created_at": str(m.created_at),
            }
            for m in reversed(msgs)
        ]
    except Exception:
        return []


@app.post("/api/chat")
async def post_chat(
    request: Request, message: str = Form(...), db: Session = Depends(get_db)
):
    sid = request.cookies.get("user_session")
    username = "Guest"
    user_id = None
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u:
                user_id = u.id
                username = u.username
        except Exception:
            pass
    if _is_admin(request) and not user_id:
        username = "Admin"
    try:
        db.add(
            models.ChatMessage(
                content=message.strip(), username=username, user_id=user_id
            )
        )
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


def is_following(follower_id: str, creator_id: str, db: Session) -> bool:
    return (
        db.query(models.Follow)
        .filter(
            models.Follow.follower_id == follower_id,
            models.Follow.following_id == creator_id,
        )
        .first()
        is not None
    )


@app.get("/api/creator-chat/{creator_id}")
async def get_creator_chat(
    creator_id: str, request: Request, limit: int = 50, db: Session = Depends(get_db)
):
    # Who is requesting?
    sid = request.cookies.get("user_session")
    if not sid and not _is_admin(request):
        raise HTTPException(401, "Login required")

    # Verify the creator exists
    creator = db.query(models.User).filter(models.User.id == creator_id).first()
    if not creator:
        raise HTTPException(404, "Creator not found")

    # Check permission: only the creator themself, an admin, or a follower can view
    if sid:
        if sid == creator_id or _is_admin(request) or is_following(sid, creator_id, db):
            pass  # allowed
        else:
            raise HTTPException(403, "You must follow this creator to see their chat")
    elif _is_admin(request):
        pass  # admin without session is also allowed (if you want)
    else:
        raise HTTPException(403, "Not authorized")

    # Fetch messages
    messages = (
        db.query(models.CreatorChatMessage)
        .filter(models.CreatorChatMessage.creator_id == creator_id)
        .order_by(models.CreatorChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    # Return in chronological order
    return [
        {
            "id": m.id,
            "user_id": str(m.user_id) if m.user_id else None,
            "username": m.username,
            "content": m.content,
            "created_at": m.created_at.isoformat(),
        }
        for m in reversed(messages)
    ]


@app.post("/api/creator-chat/{creator_id}")
async def post_creator_chat(
    creator_id: str,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    if not sid and not _is_admin(request):
        raise HTTPException(401, "Login required")

    creator = db.query(models.User).filter(models.User.id == creator_id).first()
    if not creator:
        raise HTTPException(404, "Creator not found")

    username = "Guest"
    user_id = None
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u:
                user_id = u.id
                username = u.username
        except Exception:
            pass
    if _is_admin(request) and not user_id:
        username = "Admin"

    if sid:
        if (
            sid != creator_id
            and not _is_admin(request)
            and not is_following(sid, creator_id, db)
        ):
            raise HTTPException(403, "You must follow this creator to chat")

    msg = models.CreatorChatMessage(
        creator_id=creator_id,
        user_id=user_id,
        username=username,
        content=content.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"success": True, "id": msg.id}


@app.post("/api/stories")
async def submit_story(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    region: str = Form(""),
    media: UploadFile = File(None),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    author = "Anonymous"
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u:
                author = u.username
        except Exception:
            pass

    try:
        media_url = ""
        if media:
            upload_res = await _do_upload(media, "stories", db)
            if upload_res.get("success"):
                media_url = upload_res.get("url")

        try:
            data = json.loads(content)
            data["media_url"] = media_url or data.get("media_url", "")
            final_content = json.dumps(data)
        except Exception:
            final_content = content

        db.add(
            models.StorySubmission(
                title=title,
                content=final_content,
                region=region,
                author_name=author,
                status="pending",
            )
        )
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/chatbot")
async def chatbot_endpoint(request: Request, data: dict, db: Session = Depends(get_db)):
    """
    Premium EchoBot AI: Context-aware synthesis with relevant post linking.
    """
    sid = request.cookies.get("user_session")
    user = db.query(models.User).filter(models.User.id == sid).first() if sid else None
    is_premium = user and (user.role in ["admin", "creator"] or user.is_premium == 1)

    if not is_premium:
        return {
            "success": False,
            "response": "EchoBot is a Premium feature. Upgrade your account to chat with me!",
            "locked": True,
        }

    message = data.get("message", "").strip()
    if not message:
        return {
            "success": True,
            "response": "Akwaaba! I'm EchoBot, your guide to Ghana's rich cultural heritage. Ask me about traditions, languages, history, or any of Ghana's 16 regions!",
        }

    # ── Greeting detection – respond instantly without database search ──────────
    greetings = [
        "hi",
        "hello",
        "hey",
        "akwaaba",
        "meda ase",
        "thank you",
        "thanks",
        "good morning",
        "good afternoon",
        "good evening",
        "how are you",
        "who are you",
        "what can you do",
        "help",
    ]
    msg_lower = message.lower()
    is_greeting = any(
        msg_lower == g or msg_lower.startswith(g + " ") for g in greetings
    )

    if is_greeting:
        # Customize greeting based on time of day
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting_time = "Good morning!"
        elif 12 <= hour < 17:
            greeting_time = "Good afternoon!"
        else:
            greeting_time = "Good evening!"

        return {
            "success": True,
            "response": f"{greeting_time} Akwaaba! I'm EchoBot, your AI guide to Ghana's heritage. I can answer questions about traditions, festivals, history, languages, and connect you with relevant posts in our archive. What would you like to explore?",
            "sources": [],
        }

    # ── Search Context ──────────────────────────────────────────────────────────
    search_context = []
    sources = []
    posts_found = 0
    faqs_found = 0

    try:
        posts = (
            db.query(models.Post)
            .filter(
                models.Post.status == "published",
                or_(
                    models.Post.title.ilike(f"%{message}%"),
                    models.Post.content.ilike(f"%{message}%"),
                ),
            )
            .limit(3)
            .all()
        )
        for p in posts:
            search_context.append(f"POST: {p.title}\n{p.content[:500]}")
            sources.append(
                {"title": f"📖 {p.title}", "url": f"/post/{p.id}", "type": "post"}
            )
            posts_found += 1

        faqs = (
            db.query(models.FAQ)
            .filter(
                or_(
                    models.FAQ.question.ilike(f"%{message}%"),
                    models.FAQ.answer.ilike(f"%{message}%"),
                )
            )
            .limit(2)
            .all()
        )
        for f in faqs:
            search_context.append(f"FAQ: {f.question}\n{f.answer}")
            sources.append(
                {
                    "title": f"❓ {f.question[:40]}",
                    "url": f"/post/{f.post_id}" if f.post_id else "/explore",
                    "type": "faq",
                }
            )
            faqs_found += 1
    except Exception as e:
        print(f"Chatbot search error: {e}")

    # ── Build System Prompt ─────────────────────────────────────────────────────
    has_context = bool(search_context)
    if has_context:
        context_block = "\n\n".join(search_context)
        system_prompt = (
            "You are EchoBot, Ghana's premium cultural AI assistant. "
            "Use the provided archive excerpts to answer the user's question. "
            "Be warm, conversational, and informative. "
            "Always cite relevant sources naturally in your response (e.g., 'According to our archives...'). "
            "Keep responses concise but thorough (3-5 sentences typically). "
            "If the context doesn't fully answer, supplement with general knowledge about Ghanaian culture. "
            "Never mention 'I found X results' – just weave the information naturally."
        )
        user_input = f"USER QUERY: {message}\n\nARCHIVE EXCERPTS:\n{context_block}"
    else:
        system_prompt = (
            "You are EchoBot, a friendly AI guide to Ghanaian heritage. "
            "No specific posts in our archive match this query. "
            "Respond conversationally with general knowledge about Ghanaian culture, traditions, history, or regions. "
            "You may suggest exploring a broad topic or ask a clarifying question. "
            "Do NOT claim to have checked archives or found information that wasn't provided."
        )
        user_input = f"USER QUERY: {message}"

    # ── Try External AI (Gemini) ─────────────────────────────────────────────────
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if GOOGLE_API_KEY:
        try:
            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
            payload = {
                "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_input}"}]}],
                "generationConfig": {"temperature": 0.5, "maxOutputTokens": 600},
            }
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(api_url, json=payload)
                if res.status_code == 200:
                    ai_text = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return {"success": True, "response": ai_text, "sources": sources}
        except Exception as e:
            print(f"Gemini error: {e}")

    # ── Fallback Local Response ─────────────────────────────────────────────────
    if has_context:
        # We have sources but AI failed; summarize what was found
        response = (
            f"I found {posts_found} post(s) and {faqs_found} FAQ(s) that might help:\n\n"
            f"Here's what our archives contain:\n"
        )
        for i, src in enumerate(sources, 1):
            response += f"{i}. {src['title']}\n"
        response += "\nClick on any source above to read more."
    else:
        # No relevant content in archives
        response = (
            "I couldn't find specific information about that in our archives yet. "
            "Would you like to ask about another aspect of Ghanaian culture? "
            "I'm great with questions about traditions, festivals, history, languages, or the 16 regions!"
        )

    return {"success": True, "response": response, "sources": sources}


# ─── PAYMENTS ────────────────────────────────────────────────────────────────
@app.post("/api/payments/initialize")
async def init_payment(
    request: Request,
    amount: int = Form(4900),
    email: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                "https://api.paystack.co/transaction/initialize",
                headers={
                    "Authorization": f"Bearer {PAYSTACK_SECRET}",
                    "Content-Type": "application/json",
                },
                json={
                    "email": email,
                    "amount": amount * 100,
                    "callback_url": f"{request.base_url}payment/callback",
                },
            )
        d = r.json()
        if d.get("status"):
            return {
                "success": True,
                "authorization_url": d["data"]["authorization_url"],
                "reference": d["data"]["reference"],
            }
        raise HTTPException(400, "Payment init failed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/payment/callback")
async def payment_callback(reference: str, db: Session = Depends(get_db)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"https://api.paystack.co/transaction/verify/{reference}",
                headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"},
            )
        d = r.json()
        if d.get("status") and d["data"]["status"] == "success":
            email = d["data"]["customer"]["email"]
            u = db.query(models.User).filter(models.User.email == email).first()
            if u:
                u.is_premium = True
                db.commit()
        return RedirectResponse("/dashboard?upgraded=1")
    except Exception:
        return RedirectResponse("/premium?error=1")


# ─── IMPORT/EXPORT ───────────────────────────────────────────────────────────
@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    try:
        items = data if isinstance(data, list) else [data]
        imported = 0
        for item in items:
            try:
                db.add(models.Region(**item))
                imported += 1
            except Exception:
                pass
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── TOPICS ──────────────────────────────────────────────────────────────────
@app.get("/api/topics")
def get_topics(db: Session = Depends(get_db)):
    try:
        topics = db.query(models.Topic).order_by(models.Topic.name).all()
        return [{"id": t.id, "name": t.name} for t in topics]
    except Exception:
        return []


# ─── SITE SETTINGS (No-Code Theme & Branding) ────────────────────────────────
@app.get("/api/admin/settings")
def get_site_settings(db: Session = Depends(get_db)):
    """Get all site settings grouped by category."""
    try:
        settings = db.query(models.SiteSetting).all()
        result = {"branding": {}, "seo": {}, "theme": {}, "general": {}}
        for s in settings:
            if s.category not in result:
                result[s.category] = {}
            # Try to parse JSON value, otherwise use plain text
            try:
                result[s.category][s.key] = json.loads(s.value)
            except (json.JSONDecodeError, TypeError):
                result[s.category][s.key] = s.value
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/admin/settings")
def update_site_settings(
    request: Request, settings: dict, db: Session = Depends(get_db)
):
    """Update site settings (branding, theme, seo, etc)."""
    try:
        for category, items in settings.items():
            for key, value in items.items():
                # Serialize complex values to JSON
                if isinstance(value, (dict, list)):
                    val_str = json.dumps(value)
                else:
                    val_str = str(value)

                existing = (
                    db.query(models.SiteSetting)
                    .filter(models.SiteSetting.key == key)
                    .first()
                )

                if existing:
                    existing.value = val_str
                    existing.category = category
                    existing.updated_at = datetime.utcnow()
                else:
                    new_setting = models.SiteSetting(
                        key=key, value=val_str, category=category
                    )
                    db.add(new_setting)

        db.commit()
        log_admin_action(
            request,
            "update",
            "site_settings",
            "bulk",
            f"Updated {category} settings",
            db,
        )
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── PAGE CONTENT EDITOR ─────────────────────────────────────────────────────
@app.get("/api/admin/pages")
def get_page_contents(db: Session = Depends(get_db)):
    """Get all page content sections."""
    try:
        pages = (
            db.query(models.PageContent)
            .filter(models.PageContent.is_active == 1)
            .order_by(models.PageContent.page_name, models.PageContent.display_order)
            .all()
        )

        result = {}
        for p in pages:
            if p.page_name not in result:
                result[p.page_name] = []
            try:
                content_data = json.loads(p.content)
            except (json.JSONDecodeError, TypeError):
                content_data = {"html": p.content}

            result[p.page_name].append(
                {
                    "id": p.id,
                    "section": p.section,
                    "content": content_data,
                    "display_order": p.display_order,
                }
            )

        return result
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/admin/pages")
def update_page_content(
    request: Request,
    page_name: str,
    section: str,
    content: dict,
    display_order: int = 0,
    db: Session = Depends(get_db),
):
    """Update or create a page section."""
    try:
        existing = (
            db.query(models.PageContent)
            .filter(
                models.PageContent.page_name == page_name,
                models.PageContent.section == section,
            )
            .first()
        )

        content_str = json.dumps(content)

        if existing:
            existing.content = content_str
            existing.display_order = display_order
            existing.updated_at = datetime.utcnow()
        else:
            new_page = models.PageContent(
                page_name=page_name,
                section=section,
                content=content_str,
                display_order=display_order,
                is_active=1,
            )
            db.add(new_page)

        db.commit()
        log_admin_action(
            request,
            "update",
            "page_content",
            f"{page_name}/{section}",
            f"Updated {page_name} - {section}",
            db,
        )
        return {"success": True, "message": "Page content updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/admin/pages/{page_id}")
def delete_page_content(request: Request, page_id: int, db: Session = Depends(get_db)):
    """Delete a page content section."""
    try:
        page = (
            db.query(models.PageContent)
            .filter(models.PageContent.id == page_id)
            .first()
        )

        if not page:
            raise HTTPException(404, "Page content not found")

        db.delete(page)
        db.commit()
        log_admin_action(
            request,
            "delete",
            "page_content",
            str(page_id),
            f"Deleted {page.page_name}/{page.section}",
            db,
        )
        return {"success": True, "message": "Page content deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── NAVIGATION MENU BUILDER ─────────────────────────────────────────────────
@app.get("/api/admin/navigation")
def get_navigation(db: Session = Depends(get_db)):
    """Get all navigation menu items."""
    try:
        items = (
            db.query(models.NavigationItem)
            .filter(models.NavigationItem.is_active == 1)
            .order_by(models.NavigationItem.display_order)
            .all()
        )

        return [
            {
                "id": i.id,
                "label": i.label,
                "url": i.url,
                "target": i.target,
                "parent_id": i.parent_id,
                "display_order": i.display_order,
            }
            for i in items
        ]
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/admin/navigation")
def create_navigation_item(
    request: Request,
    label: str,
    url: str,
    target: str = "_self",
    parent_id: int = None,
    display_order: int = 0,
    db: Session = Depends(get_db),
):
    """Create a new navigation menu item."""
    try:
        new_item = models.NavigationItem(
            label=label,
            url=url,
            target=target,
            parent_id=parent_id,
            display_order=display_order,
            is_active=1,
        )
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        log_admin_action(
            request,
            "create",
            "navigation",
            str(new_item.id),
            f"Added menu item: {label}",
            db,
        )
        return {
            "success": True,
            "item": {
                "id": new_item.id,
                "label": new_item.label,
                "url": new_item.url,
                "target": new_item.target,
                "parent_id": new_item.parent_id,
                "display_order": new_item.display_order,
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.put("/api/admin/navigation/{item_id}")
def update_navigation_item(
    request: Request,
    item_id: int,
    label: str = None,
    url: str = None,
    target: str = None,
    parent_id: int = None,
    display_order: int = None,
    db: Session = Depends(get_db),
):
    """Update a navigation menu item."""
    try:
        item = (
            db.query(models.NavigationItem)
            .filter(models.NavigationItem.id == item_id)
            .first()
        )

        if not item:
            raise HTTPException(404, "Navigation item not found")

        if label is not None:
            item.label = label
        if url is not None:
            item.url = url
        if target is not None:
            item.target = target
        if parent_id is not None:
            item.parent_id = parent_id
        if display_order is not None:
            item.display_order = display_order

        db.commit()
        log_admin_action(
            request,
            "update",
            "navigation",
            str(item_id),
            f"Updated menu item: {item.label}",
            db,
        )
        return {"success": True, "message": "Navigation item updated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/admin/navigation/{item_id}")
def delete_navigation_item(
    request: Request, item_id: int, db: Session = Depends(get_db)
):
    """Delete a navigation menu item."""
    try:
        item = (
            db.query(models.NavigationItem)
            .filter(models.NavigationItem.id == item_id)
            .first()
        )

        if not item:
            raise HTTPException(404, "Navigation item not found")

        db.delete(item)
        db.commit()
        log_admin_action(
            request,
            "delete",
            "navigation",
            str(item_id),
            f"Deleted menu item: {item.label}",
            db,
        )
        return {"success": True, "message": "Navigation item deleted"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── ANALYTICS (Placeholder for future integration) ──────────────────────────
@app.get("/api/admin/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Get basic site analytics (placeholder)."""
    try:
        total_users = db.query(models.User).count()
        total_posts = (
            db.query(models.Post).filter(models.Post.status == "published").count()
        )
        total_views = db.query(func.sum(models.Post.views)).scalar() or 0

        return {
            "total_users": total_users,
            "total_posts": total_posts,
            "total_views": int(total_views),
            "unique_visitors": random.randint(500, 2000),
            "avg_time_on_site": "3:24",
            "bounce_rate": "42%",
            "top_pages": [
                {"path": "/", "views": random.randint(100, 500)},
                {"path": "/dashboard", "views": random.randint(80, 300)},
                {"path": "/regions", "views": random.randint(50, 200)},
            ],
            "referrers": [
                {"source": "Google", "visits": random.randint(200, 800)},
                {"source": "Direct", "visits": random.randint(100, 400)},
                {"source": "Social", "visits": random.randint(50, 200)},
            ],
        }
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── BACKUP & RESTORE ────────────────────────────────────────────────────────
@app.get("/api/admin/backup")
def create_backup(db: Session = Depends(get_db)):
    """Create a backup of site settings and content."""
    try:
        backup_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "settings": db.query(models.SiteSetting).all(),
            "pages": db.query(models.PageContent).all(),
            "navigation": db.query(models.NavigationItem).all(),
        }

        def serialize(obj):
            if hasattr(obj, "__dict__"):
                d = {}
                for k, v in obj.__dict__.items():
                    if k != "_sa_instance_state":
                        if isinstance(v, datetime):
                            d[k] = v.isoformat()
                        else:
                            d[k] = v
                return d
            return obj

        backup_serializable = {
            "timestamp": backup_data["timestamp"],
            "settings": [serialize(s) for s in backup_data["settings"]],
            "pages": [serialize(p) for p in backup_data["pages"]],
            "navigation": [serialize(n) for n in backup_data["navigation"]],
        }

        return {
            "success": True,
            "backup": backup_serializable,
            "filename": f"echostack_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json",
        }
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/admin/restore")
def restore_backup(request: Request, backup_data: dict, db: Session = Depends(get_db)):
    """Restore site from backup data."""
    try:
        if "settings" in backup_data:
            for s in backup_data["settings"]:
                existing = (
                    db.query(models.SiteSetting)
                    .filter(models.SiteSetting.key == s.get("key"))
                    .first()
                )
                if existing:
                    existing.value = s.get("value", "")
                    existing.category = s.get("category", "general")
                else:
                    db.add(models.SiteSetting(**s))

        if "navigation" in backup_data:
            for n in backup_data["navigation"]:
                if "id" in n:
                    del n["id"]
                db.add(models.NavigationItem(**n))

        db.commit()
        log_admin_action(
            request, "restore", "backup", "bulk", "Restored site from backup", db
        )
        return {"success": True, "message": "Backup restored successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# NEW FEATURES: Bookmarks, Notifications, Search, Trending, Recommendations,
#               Collections, User Settings, Direct Messages, Tips, Subscriptions,
#               Badges, Shares
# ═══════════════════════════════════════════════════════════════════════════════


# ─── BOOKMARKS ────────────────────────────────────────────────────────────────
@app.get("/api/bookmarks")
async def get_bookmarks(request: Request, db: Session = Depends(get_db)):
    """Get all bookmarks for the current user."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        bookmarks = (
            db.query(models.Bookmark)
            .filter(models.Bookmark.user_id == sid)
            .order_by(models.Bookmark.created_at.desc())
            .all()
        )

        result = []
        for b in bookmarks:
            post = db.query(models.Post).filter(models.Post.id == b.post_id).first()
            if post:
                result.append(
                    {
                        "id": b.id,
                        "post_id": b.post_id,
                        "title": post.title,
                        "excerpt": post.excerpt or "",
                        "cover_image": post.cover_image or "",
                        "content_type": post.content_type or "article",
                        "author_username": post.author_username or "",
                        "created_at": str(b.created_at),
                    }
                )
        return result
    except Exception as e:
        print(f"Bookmarks error: {e}")
        return []


@app.post("/api/bookmarks/{post_id}")
async def toggle_bookmark(
    post_id: int, request: Request, db: Session = Depends(get_db)
):
    """Toggle bookmark for a post."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        existing = (
            db.query(models.Bookmark)
            .filter(models.Bookmark.user_id == sid, models.Bookmark.post_id == post_id)
            .first()
        )

        if existing:
            db.delete(existing)
            db.commit()
            return {"bookmarked": False}

        bookmark = models.Bookmark(user_id=sid, post_id=post_id)
        db.add(bookmark)
        db.commit()
        return {"bookmarked": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── NOTIFICATIONS ─────────────────────────────────────────────────────────────
@app.get("/api/notifications")
async def get_notifications(
    request: Request, limit: int = 50, db: Session = Depends(get_db)
):
    """Get notifications for the current user."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        notifications = (
            db.query(models.Notification)
            .filter(models.Notification.user_id == sid)
            .order_by(models.Notification.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": n.id,
                "type": n.type or "info",
                "title": n.title or "",
                "message": n.message or "",
                "link": n.link or "",
                "is_read": bool(n.is_read),
                "actor_username": n.actor_username or "",
                "created_at": str(n.created_at),
            }
            for n in notifications
        ]
    except Exception as e:
        print(f"Notifications error: {e}")
        return []


@app.post("/api/notifications/read-all")
async def mark_all_read(request: Request, db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        db.query(models.Notification).filter(
            models.Notification.user_id == sid, models.Notification.is_read == 0
        ).update({models.Notification.is_read: 1})
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.post("/api/notifications/{notification_id}/read")
async def mark_read(
    notification_id: int, request: Request, db: Session = Depends(get_db)
):
    """Mark a single notification as read."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        notif = (
            db.query(models.Notification)
            .filter(
                models.Notification.id == notification_id,
                models.Notification.user_id == sid,
            )
            .first()
        )
        if notif:
            notif.is_read = 1
            db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/notifications/unread-count")
async def unread_count(request: Request, db: Session = Depends(get_db)):
    """Get count of unread notifications."""
    sid = request.cookies.get("user_session")
    if not sid:
        return {"count": 0}
    try:
        count = (
            db.query(models.Notification)
            .filter(
                models.Notification.user_id == sid, models.Notification.is_read == 0
            )
            .count()
        )
        return {"count": count}
    except Exception:
        return {"count": 0}


def create_notification(
    user_id,
    notif_type: str,
    title: str,
    message: str,
    link: str = "",
    actor_id=None,
    actor_username="",
    db=None,
):
    """Helper to create a notification."""
    try:
        notif = models.Notification(
            user_id=user_id,
            type=notif_type,
            title=title,
            message=message,
            link=link,
            actor_id=actor_id,
            actor_username=actor_username,
        )
        db.add(notif)
        db.commit()
    except Exception as e:
        print(f"Notification error: {e}")


# ─── SEARCH ──────────────────────────────────────────────────────────────────
@app.get("/api/search")
async def search(
    request: Request,
    q: str = "",
    content_type: str = "",
    region_id: str = "",
    sort: str = "recent",
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """Advanced search with filters."""
    if not q or len(q) < 2:
        return {"posts": [], "users": [], "regions": []}

    try:
        posts_q = db.query(models.Post).filter(
            models.Post.status == "published",
            or_(
                models.Post.title.ilike(f"%{q}%"),
                models.Post.content.ilike(f"%{q}%"),
                models.Post.excerpt.ilike(f"%{q}%"),
                models.Post.tags.ilike(f"%{q}%"),
            ),
        )

        if content_type:
            posts_q = posts_q.filter(models.Post.content_type == content_type)
        if region_id and region_id.isdigit():
            posts_q = posts_q.filter(models.Post.region_id == int(region_id))

        if sort == "popular":
            posts_q = posts_q.order_by(models.Post.likes.desc())
        elif sort == "views":
            posts_q = posts_q.order_by(models.Post.views.desc())
        else:
            posts_q = posts_q.order_by(models.Post.created_at.desc())

        posts = posts_q.offset(offset).limit(limit).all()

        users = (
            db.query(models.User)
            .filter(
                or_(
                    models.User.username.ilike(f"%{q}%"),
                    models.User.channel_name.ilike(f"%{q}%"),
                )
            )
            .limit(10)
            .all()
        )

        regions = (
            db.query(models.Region)
            .filter(
                or_(
                    models.Region.name.ilike(f"%{q}%"),
                    models.Region.description.ilike(f"%{q}%"),
                )
            )
            .limit(5)
            .all()
        )

        return {
            "posts": [
                {
                    "id": p.id,
                    "title": p.title or "",
                    "slug": p.slug or "",
                    "excerpt": p.excerpt or "",
                    "cover_image": p.cover_image or "",
                    "content_type": p.content_type or "article",
                    "author_username": p.author_username or "",
                    "likes": p.likes or 0,
                    "views": p.views or 0,
                    "created_at": str(p.created_at),
                }
                for p in posts
            ],
            "users": [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "channel_name": u.channel_name or u.username,
                    "avatar_url": u.avatar_url or "",
                    "follower_count": u.follower_count or 0,
                }
                for u in users
            ],
            "regions": [
                {"id": r.id, "name": r.name or "", "description": r.description or ""}
                for r in regions
            ],
        }
    except Exception as e:
        print(f"Search error: {e}")
        return {"posts": [], "users": [], "regions": []}


# ─── TRENDING ────────────────────────────────────────────────────────────────
# ─── STORIES ──────────────────────────────────────────────────────────────────
@app.get("/api/stories")
async def get_stories(db: Session = Depends(get_db)):
    try:
        now = datetime.utcnow()
        # Fetch stories that are not expired
        stories = (
            db.query(models.Story)
            .filter(or_(models.Story.expires_at > now, models.Story.expires_at == None))
            .order_by(models.Story.created_at.desc())
            .all()
        )

        result = []
        for s in stories:
            user = db.query(models.User).filter(models.User.id == s.user_id).first()
            result.append(
                {
                    "id": s.id,
                    "user_id": str(s.user_id),
                    "username": user.username if user else "Unknown",
                    "avatar_url": getattr(user, "avatar_url", "") if user else "",
                    "media_url": s.media_url,
                    "media_type": s.media_type,
                    "caption": s.caption,
                    "created_at": str(s.created_at),
                }
            )
        return result
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return []


@app.post("/api/stories")
async def create_story(
    request: Request,
    media_url: str = Form(...),
    media_type: str = Form("image"),
    caption: str = Form(""),
    db: Session = Depends(get_db),
):
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login to post stories")

    try:
        # Check if user exists
        user = db.query(models.User).filter(models.User.id == sid).first()
        if not user:
            raise HTTPException(401, "Invalid session")

        expires_at = datetime.utcnow() + timedelta(hours=24)
        new_story = models.Story(
            user_id=sid,
            media_url=media_url,
            media_type=media_type,
            caption=caption,
            expires_at=expires_at,
            is_approved=True,
        )
        db.add(new_story)
        db.commit()
        return {"success": True, "story_id": new_story.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/trending")
async def get_trending(limit: int = 10, db: Session = Depends(get_db)):
    """Get trending posts (most liked/shared in last 7 days)."""
    try:
        posts = (
            db.query(models.Post)
            .filter(models.Post.status == "published")
            .order_by((models.Post.likes + models.Post.views / 10).desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": p.id,
                "title": p.title or "",
                "slug": p.slug or "",
                "excerpt": p.excerpt or "",
                "cover_image": p.cover_image or "",
                "content_type": p.content_type or "article",
                "author_username": p.author_username or "",
                "likes": p.likes or 0,
                "views": p.views or 0,
                "score": (p.likes or 0) + (p.views or 0) / 10,
            }
            for p in posts
        ]
    except Exception as e:
        print(f"Trending error: {e}")
        return []


# ─── RECOMMENDATIONS ─────────────────────────────────────────────────────────
@app.get("/api/recommendations")
async def get_recommendations(
    request: Request, limit: int = 10, db: Session = Depends(get_db)
):
    """Get personalized recommendations based on followed users and topics."""
    sid = request.cookies.get("user_session")
    try:
        if sid:
            followed = (
                db.query(models.Follow.following_id)
                .filter(models.Follow.follower_id == sid)
                .all()
            )
            following_ids = [f[0] for f in followed]

            if following_ids:
                posts = (
                    db.query(models.Post)
                    .filter(
                        models.Post.status == "published",
                        models.Post.author_id.in_(following_ids),
                    )
                    .order_by(models.Post.created_at.desc())
                    .limit(limit)
                    .all()
                )
            else:
                posts = (
                    db.query(models.Post)
                    .filter(models.Post.status == "published")
                    .order_by(models.Post.likes.desc())
                    .limit(limit)
                    .all()
                )
        else:
            posts = (
                db.query(models.Post)
                .filter(models.Post.status == "published")
                .order_by(models.Post.likes.desc())
                .limit(limit)
                .all()
            )

        return [
            {
                "id": p.id,
                "title": p.title or "",
                "slug": p.slug or "",
                "excerpt": p.excerpt or "",
                "cover_image": p.cover_image or "",
                "content_type": p.content_type or "article",
                "author_username": p.author_username or "",
                "likes": p.likes or 0,
            }
            for p in posts
        ]
    except Exception as e:
        print(f"Recommendations error: {e}")
        return []


# ─── COLLECTIONS ────────────────────────────────────────────────────────────
@app.get("/api/collections")
async def get_collections(request: Request, db: Session = Depends(get_db)):
    """Get user's collections."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        collections = (
            db.query(models.Collection)
            .filter(models.Collection.user_id == sid)
            .order_by(models.Collection.updated_at.desc())
            .all()
        )

        result = []
        for c in collections:
            item_count = (
                db.query(models.CollectionItem)
                .filter(models.CollectionItem.collection_id == c.id)
                .count()
            )
            result.append(
                {
                    "id": c.id,
                    "name": c.name or "",
                    "description": c.description or "",
                    "cover_image": c.cover_image or "",
                    "is_public": bool(c.is_public),
                    "item_count": item_count,
                    "created_at": str(c.created_at),
                }
            )
        return result
    except Exception as e:
        print(f"Collections error: {e}")
        return []


@app.post("/api/collections")
async def create_collection(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    cover_image: str = Form(""),
    is_public: str = Form("1"),
    db: Session = Depends(get_db),
):
    """Create a new collection."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        collection = models.Collection(
            user_id=sid,
            name=name.strip(),
            description=description.strip(),
            cover_image=cover_image.strip(),
            is_public=1 if is_public in ("1", "true", "True") else 0,
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return {"success": True, "id": collection.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/collections/{collection_id}")
async def get_collection(collection_id: int, db: Session = Depends(get_db)):
    """Get a collection with its posts."""
    try:
        collection = (
            db.query(models.Collection)
            .filter(models.Collection.id == collection_id)
            .first()
        )
        if not collection:
            raise HTTPException(404, "Collection not found")

        items = (
            db.query(models.CollectionItem)
            .filter(models.CollectionItem.collection_id == collection_id)
            .order_by(models.CollectionItem.display_order)
            .all()
        )

        posts = []
        for item in items:
            post = db.query(models.Post).filter(models.Post.id == item.post_id).first()
            if post:
                posts.append(
                    {
                        "id": post.id,
                        "title": post.title or "",
                        "slug": post.slug or "",
                        "excerpt": post.excerpt or "",
                        "cover_image": post.cover_image or "",
                        "content_type": post.content_type or "article",
                        "author_username": post.author_username or "",
                    }
                )

        return {
            "id": collection.id,
            "name": collection.name or "",
            "description": collection.description or "",
            "cover_image": collection.cover_image or "",
            "is_public": bool(collection.is_public),
            "posts": posts,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/collections/{collection_id}/posts/{post_id}")
async def add_to_collection(
    collection_id: int, post_id: int, request: Request, db: Session = Depends(get_db)
):
    """Add a post to a collection."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        collection = (
            db.query(models.Collection)
            .filter(
                models.Collection.id == collection_id, models.Collection.user_id == sid
            )
            .first()
        )
        if not collection:
            raise HTTPException(404, "Collection not found")

        existing = (
            db.query(models.CollectionItem)
            .filter(
                models.CollectionItem.collection_id == collection_id,
                models.CollectionItem.post_id == post_id,
            )
            .first()
        )
        if existing:
            return {"success": True, "message": "Already in collection"}

        item = models.CollectionItem(
            collection_id=collection_id, post_id=post_id, display_order=0
        )
        db.add(item)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/collections/{collection_id}/posts/{post_id}")
async def remove_from_collection(
    collection_id: int, post_id: int, request: Request, db: Session = Depends(get_db)
):
    """Remove a post from a collection."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        collection = (
            db.query(models.Collection)
            .filter(
                models.Collection.id == collection_id, models.Collection.user_id == sid
            )
            .first()
        )
        if not collection:
            raise HTTPException(404, "Collection not found")

        db.query(models.CollectionItem).filter(
            models.CollectionItem.collection_id == collection_id,
            models.CollectionItem.post_id == post_id,
        ).delete()
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── USER SETTINGS (Dark Mode, etc.) ─────────────────────────────────────────
@app.get("/api/settings")
async def get_user_settings(request: Request, db: Session = Depends(get_db)):
    """Get user settings."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        settings = (
            db.query(models.UserSetting)
            .filter(models.UserSetting.user_id == sid)
            .first()
        )

        if not settings:
            settings = models.UserSetting(user_id=sid)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return {
            "dark_mode": bool(settings.dark_mode),
            "language": settings.language or "en",
            "email_notifications": bool(settings.email_notifications),
            "push_notifications": bool(settings.push_notifications),
            "show_follower_count": bool(settings.show_follower_count),
            "show_post_stats": bool(settings.show_post_stats),
        }
    except Exception as e:
        print(f"Settings error: {e}")
        return {
            "dark_mode": False,
            "language": "en",
            "email_notifications": True,
            "push_notifications": True,
            "show_follower_count": True,
            "show_post_stats": True,
        }


@app.put("/api/settings")
async def update_user_settings(
    request: Request,
    dark_mode: str = Form(None),
    language: str = Form(None),
    email_notifications: str = Form(None),
    push_notifications: str = Form(None),
    show_follower_count: str = Form(None),
    show_post_stats: str = Form(None),
    db: Session = Depends(get_db),
):
    """Update user settings."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        settings = (
            db.query(models.UserSetting)
            .filter(models.UserSetting.user_id == sid)
            .first()
        )

        if not settings:
            settings = models.UserSetting(user_id=sid)
            db.add(settings)

        if dark_mode is not None:
            settings.dark_mode = 1 if dark_mode in ("1", "true", "True") else 0
        if language is not None:
            settings.language = language
        if email_notifications is not None:
            settings.email_notifications = (
                1 if email_notifications in ("1", "true", "True") else 0
            )
        if push_notifications is not None:
            settings.push_notifications = (
                1 if push_notifications in ("1", "true", "True") else 0
            )
        if show_follower_count is not None:
            settings.show_follower_count = (
                1 if show_follower_count in ("1", "true", "True") else 0
            )
        if show_post_stats is not None:
            settings.show_post_stats = (
                1 if show_post_stats in ("1", "true", "True") else 0
            )

        settings.updated_at = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "settings": {
                "dark_mode": bool(settings.dark_mode),
                "language": settings.language,
                "email_notifications": bool(settings.email_notifications),
                "push_notifications": bool(settings.push_notifications),
                "show_follower_count": bool(settings.show_follower_count),
                "show_post_stats": bool(settings.show_post_stats),
            },
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── DIRECT MESSAGES ─────────────────────────────────────────────────────────
@app.get("/api/messages")
async def get_conversations(request: Request, db: Session = Depends(get_db)):
    """
    Optimized conversations endpoint using batch queries.
    Loads all users in a single query instead of N+1 queries.
    """
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        messages = (
            db.query(models.DirectMessage)
            .filter(
                or_(
                    models.DirectMessage.sender_id == sid,
                    models.DirectMessage.receiver_id == sid,
                )
            )
            .order_by(models.DirectMessage.created_at.desc())
            .all()
        )

        # Collect all unique user IDs first
        other_ids = set()
        for m in messages:
            other_id = m.receiver_id if m.sender_id == sid else m.sender_id
            other_ids.add(other_id)

        # Batch load all users in a single query
        users = {}
        if other_ids:
            user_list = (
                db.query(models.User.id, models.User.username, models.User.avatar_url)
                .filter(models.User.id.in_(other_ids))
                .all()
            )
            users = {
                u.id: {"username": u.username, "avatar_url": u.avatar_url or ""}
                for u in user_list
            }

        # Build conversations without additional queries
        conversations = {}
        for m in messages:
            other_id = m.receiver_id if m.sender_id == sid else m.sender_id
            if other_id not in conversations and other_id in users:
                conversations[other_id] = {
                    "user_id": str(other_id),
                    "username": users[other_id]["username"],
                    "avatar_url": users[other_id]["avatar_url"],
                    "last_message": m.content,
                    "last_message_at": str(m.created_at),
                    "unread_count": 0,
                }
            if m.sender_id != sid and not m.is_read and other_id in conversations:
                conversations[other_id]["unread_count"] = (
                    conversations[other_id].get("unread_count", 0) + 1
                )

        return list(conversations.values())
    except Exception as e:
        print(f"Messages error: {e}")
        return []


@app.get("/api/messages/{user_id}")
async def get_messages(
    user_id: str, request: Request, limit: int = 50, db: Session = Depends(get_db)
):
    """Get messages with a specific user."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        messages = (
            db.query(models.DirectMessage)
            .filter(
                or_(
                    and_(
                        models.DirectMessage.sender_id == sid,
                        models.DirectMessage.receiver_id == user_id,
                    ),
                    and_(
                        models.DirectMessage.sender_id == user_id,
                        models.DirectMessage.receiver_id == sid,
                    ),
                )
            )
            .order_by(models.DirectMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        db.query(models.DirectMessage).filter(
            models.DirectMessage.sender_id == user_id,
            models.DirectMessage.receiver_id == sid,
            models.DirectMessage.is_read == 0,
        ).update({models.DirectMessage.is_read: 1})
        db.commit()

        return [
            {
                "id": m.id,
                "sender_id": str(m.sender_id),
                "receiver_id": str(m.receiver_id),
                "content": m.content,
                "is_read": bool(m.is_read),
                "created_at": str(m.created_at),
                "is_mine": str(m.sender_id) == sid,
            }
            for m in reversed(messages)
        ]
    except Exception as e:
        print(f"Messages error: {e}")
        return []


@app.post("/api/messages/{user_id}")
async def send_message(
    user_id: str,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db),
):
    """Send a direct message."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        receiver = db.query(models.User).filter(models.User.id == user_id).first()
        if not receiver:
            raise HTTPException(404, "User not found")

        sender = db.query(models.User).filter(models.User.id == sid).first()

        message = models.DirectMessage(
            sender_id=sid, receiver_id=user_id, content=content.strip()
        )
        db.add(message)
        db.commit()
        db.refresh(message)

        create_notification(
            user_id=user_id,
            notif_type="message",
            title="New message",
            message=f"{sender.username if sender else 'Someone'} sent you a message",
            link="/messages",
            actor_id=sid,
            actor_username=sender.username if sender else "",
            db=db,
        )

        return {"success": True, "id": message.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── TIPS ─────────────────────────────────────────────────────────────────────
@app.post("/api/tips/{user_id}")
async def send_tip(
    user_id: str,
    request: Request,
    amount: int = Form(100),
    message: str = Form(""),
    db: Session = Depends(get_db),
):
    """Send a tip to a creator."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    if amount < 1:
        raise HTTPException(400, "Minimum tip is 1")
    try:
        receiver = db.query(models.User).filter(models.User.id == user_id).first()
        if not receiver:
            raise HTTPException(404, "User not found")

        sender = db.query(models.User).filter(models.User.id == sid).first()

        tip = models.Tip(
            sender_id=sid,
            receiver_id=user_id,
            amount=amount,
            message=message.strip(),
            status="pending",
        )
        db.add(tip)
        db.commit()
        db.refresh(tip)

        create_notification(
            user_id=user_id,
            notif_type="tip",
            title="You received a tip!",
            message=f"{sender.username if sender else 'Someone'} sent you a tip of {amount}",
            link="/tips",
            actor_id=sid,
            actor_username=sender.username if sender else "",
            db=db,
        )

        return {
            "success": True,
            "tip_id": tip.id,
            "message": "Tip sent! (Payment integration pending)",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/tips")
async def get_tips(request: Request, db: Session = Depends(get_db)):
    """Get tips sent/received by user."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        sent = db.query(models.Tip).filter(models.Tip.sender_id == sid).all()
        received = db.query(models.Tip).filter(models.Tip.receiver_id == sid).all()

        return {
            "sent": [
                {
                    "id": t.id,
                    "receiver_id": str(t.receiver_id),
                    "amount": t.amount,
                    "message": t.message or "",
                    "status": t.status,
                    "created_at": str(t.created_at),
                }
                for t in sent
            ],
            "received": [
                {
                    "id": t.id,
                    "sender_id": str(t.sender_id),
                    "amount": t.amount,
                    "message": t.message or "",
                    "status": t.status,
                    "created_at": str(t.created_at),
                }
                for t in received
            ],
        }
    except Exception as e:
        print(f"Tips error: {e}")
        return {"sent": [], "received": []}


# ─── SUBSCRIPTIONS ────────────────────────────────────────────────────────────
@app.post("/api/subscribe/{creator_id}")
async def subscribe_to_creator(
    creator_id: str,
    request: Request,
    tier: str = Form("free"),
    db: Session = Depends(get_db),
):
    """Subscribe to a creator."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        existing = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.subscriber_id == sid,
                models.Subscription.creator_id == creator_id,
            )
            .first()
        )

        if existing:
            existing.tier = tier
            existing.status = "active"
            db.commit()
            return {"success": True, "message": f"Updated to {tier} tier"}

        subscription = models.Subscription(
            subscriber_id=sid, creator_id=creator_id, tier=tier, status="active"
        )
        db.add(subscription)
        db.commit()

        creator = db.query(models.User).filter(models.User.id == creator_id).first()
        if creator:
            create_notification(
                user_id=creator_id,
                notif_type="subscribe",
                title="New subscriber!",
                message=f"Someone subscribed to your content as {tier}",
                link="/subscribers",
                actor_id=sid,
                actor_username="",
                db=db,
            )

        return {"success": True, "message": f"Subscribed as {tier}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.delete("/api/subscribe/{creator_id}")
async def unsubscribe_from_creator(
    creator_id: str, request: Request, db: Session = Depends(get_db)
):
    """Unsubscribe from a creator."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        db.query(models.Subscription).filter(
            models.Subscription.subscriber_id == sid,
            models.Subscription.creator_id == creator_id,
        ).update({models.Subscription.status: "cancelled"})
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/subscriptions")
async def get_my_subscriptions(request: Request, db: Session = Depends(get_db)):
    """Get user's subscriptions to creators."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        subs = (
            db.query(models.Subscription)
            .filter(
                models.Subscription.subscriber_id == sid,
                models.Subscription.status == "active",
            )
            .all()
        )

        result = []
        for s in subs:
            creator = (
                db.query(models.User).filter(models.User.id == s.creator_id).first()
            )
            if creator:
                result.append(
                    {
                        "creator_id": str(s.creator_id),
                        "username": creator.username,
                        "channel_name": creator.channel_name or creator.username,
                        "avatar_url": creator.avatar_url or "",
                        "tier": s.tier,
                        "expires_at": str(s.expires_at) if s.expires_at else None,
                    }
                )
        return result
    except Exception as e:
        print(f"Subscriptions error: {e}")
        return []


# ─── BADGES ───────────────────────────────────────────────────────────────────
@app.get("/api/badges")
async def get_badges(db: Session = Depends(get_db)):
    """Get all available badges."""
    badge_types = [
        {"type": "verified", "name": "Verified Creator", "icon": "fa-check-circle"},
        {
            "type": "ambassador",
            "name": "Cultural Ambassador",
            "icon": "fa-globe-africa",
        },
        {"type": "top_contributor", "name": "Top Contributor", "icon": "fa-star"},
        {"type": "storyteller", "name": "Master Storyteller", "icon": "fa-book-open"},
        {"type": "supporter", "name": "Top Supporter", "icon": "fa-heart"},
        {"type": "early_adopter", "name": "Early Adopter", "icon": "fa-rocket"},
    ]
    return badge_types


@app.get("/api/users/{user_id}/badges")
async def get_user_badges(user_id: str, db: Session = Depends(get_db)):
    """Get badges for a specific user."""
    try:
        badges = (
            db.query(models.UserBadge).filter(models.UserBadge.user_id == user_id).all()
        )
        return [
            {
                "type": b.badge_type,
                "name": b.badge_name,
                "icon": b.badge_icon,
                "awarded_at": str(b.awarded_at),
            }
            for b in badges
        ]
    except Exception as e:
        print(f"Badges error: {e}")
        return []


@app.post("/api/admin/users/{user_id}/badge")
async def award_badge(
    user_id: str,
    request: Request,
    badge_type: str = Form(...),
    badge_name: str = Form(""),
    badge_icon: str = Form(""),
    db: Session = Depends(get_db),
):
    """Award a badge to a user (admin only)."""
    if not _is_admin(request):
        raise HTTPException(403)
    try:
        existing = (
            db.query(models.UserBadge)
            .filter(
                models.UserBadge.user_id == user_id,
                models.UserBadge.badge_type == badge_type,
            )
            .first()
        )

        if existing:
            return {"success": True, "message": "Badge already awarded"}

        badge = models.UserBadge(
            user_id=user_id,
            badge_type=badge_type,
            badge_name=badge_name,
            badge_icon=badge_icon,
        )
        db.add(badge)
        db.commit()

        user = db.query(models.User).filter(models.User.id == user_id).first()
        if user:
            create_notification(
                user_id=user_id,
                notif_type="badge",
                title="New badge earned!",
                message=f"You received the '{badge_name}' badge",
                link="/profile",
                actor_id=None,
                actor_username="EchoStack",
                db=db,
            )

        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


# ─── SHARES ───────────────────────────────────────────────────────────────────
@app.post("/api/share/{post_id}")
async def share_post(
    post_id: int,
    request: Request,
    platform: str = Form("internal"),
    db: Session = Depends(get_db),
):
    """Record a share."""
    sid = request.cookies.get("user_session")
    try:
        share = models.Share(
            user_id=sid if sid else None, post_id=post_id, platform=platform
        )
        db.add(share)

        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if post:
            post.views = (post.views or 0) + 1
        db.commit()

        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(500, str(e))


@app.get("/api/posts/{post_id}/share-url")
async def get_share_url(post_id: int, request: Request, db: Session = Depends(get_db)):
    """Get shareable URL for a post."""
    try:
        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not post:
            raise HTTPException(404, "Post not found")

        base_url = str(request.base_url).rstrip("/")
        return {
            "url": f"{base_url}/post/{post_id}",
            "title": post.title or "",
            "text": f"Check out '{post.title}' on EchoStack Ghana",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── USER PROFILE ─────────────────────────────────────────────────────────────
@app.get("/api/users/{username}")
async def get_user_profile(
    username: str, request: Request, db: Session = Depends(get_db)
):
    """
    Optimized user profile endpoint using batch queries.
    Loads posts, badges, and follow status efficiently.
    """
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")

        # Batch load posts
        posts = (
            db.query(models.Post)
            .filter(models.Post.author_id == user.id, models.Post.status == "published")
            .order_by(models.Post.created_at.desc())
            .limit(20)
            .all()
        )

        # Batch load badges
        badges = (
            db.query(models.UserBadge).filter(models.UserBadge.user_id == user.id).all()
        )

        # Check follow status
        is_following = False
        sid = request.cookies.get("user_session")
        if sid and user.id:
            follow = (
                db.query(models.Follow)
                .filter(
                    models.Follow.follower_id == sid,
                    models.Follow.following_id == user.id,
                )
                .first()
            )
            is_following = follow is not None

        return {
            "id": str(user.id),
            "username": user.username,
            "bio": user.bio or "",
            "avatar_url": user.avatar_url or "",
            "channel_name": user.channel_name or user.username,
            "channel_desc": user.channel_desc or "",
            "follower_count": user.follower_count or 0,
            "is_premium": bool(user.is_premium),
            "created_at": str(user.created_at),
            "is_following": is_following,
            "badges": [
                {"type": b.badge_type, "name": b.badge_name, "icon": b.badge_icon}
                for b in badges
            ],
            "posts": [
                {
                    "id": p.id,
                    "title": p.title or "",
                    "slug": p.slug or "",
                    "excerpt": p.excerpt or "",
                    "cover_image": p.cover_image or "",
                    "content_type": p.content_type or "article",
                    "likes": p.likes or 0,
                    "views": p.views or 0,
                    "created_at": str(p.created_at),
                }
                for p in posts
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ─── FOLLOWERS / FOLLOWING ─────────────────────────────────────────────────────
@app.get("/api/users/{username}/followers")
async def get_followers(username: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get followers of a user."""
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")

        follows = (
            db.query(models.Follow)
            .filter(models.Follow.following_id == user.id)
            .limit(limit)
            .all()
        )

        result = []
        for f in follows:
            follower = (
                db.query(models.User).filter(models.User.id == f.follower_id).first()
            )
            if follower:
                result.append(
                    {
                        "id": str(follower.id),
                        "username": follower.username,
                        "avatar_url": follower.avatar_url or "",
                        "channel_name": follower.channel_name or follower.username,
                    }
                )
        return result
    except HTTPException:
        raise
    except Exception as e:
        return []


@app.get("/api/users/{username}/following")
async def get_following(username: str, limit: int = 50, db: Session = Depends(get_db)):
    """Get users that a user follows."""
    try:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            raise HTTPException(404, "User not found")

        follows = (
            db.query(models.Follow)
            .filter(models.Follow.follower_id == user.id)
            .limit(limit)
            .all()
        )

        result = []
        for f in follows:
            following = (
                db.query(models.User).filter(models.User.id == f.following_id).first()
            )
            if following:
                result.append(
                    {
                        "id": str(following.id),
                        "username": following.username,
                        "avatar_url": following.avatar_url or "",
                        "channel_name": following.channel_name or following.username,
                    }
                )
        return result
    except HTTPException:
        raise
    except Exception as e:
        return []


# ─── LIKED POSTS ──────────────────────────────────────────────────────────────
@app.get("/api/likes")
async def get_liked_posts(
    request: Request, limit: int = 50, db: Session = Depends(get_db)
):
    """Get posts liked by current user."""
    sid = request.cookies.get("user_session")
    if not sid:
        raise HTTPException(401, "Login required")
    try:
        likes = (
            db.query(models.Comment)
            .filter(models.Comment.user_id == sid, models.Comment.content == "__like__")
            .order_by(models.Comment.created_at.desc())
            .limit(limit)
            .all()
        )

        posts = []
        for like in likes:
            post = db.query(models.Post).filter(models.Post.id == like.post_id).first()
            if post:
                posts.append(
                    {
                        "id": post.id,
                        "title": post.title or "",
                        "slug": post.slug or "",
                        "excerpt": post.excerpt or "",
                        "cover_image": post.cover_image or "",
                        "content_type": post.content_type or "article",
                        "author_username": post.author_username or "",
                        "likes": post.likes or 0,
                        "created_at": str(post.created_at),
                    }
                )
        return posts
    except Exception as e:
        print(f"Likes error: {e}")
        return []


# ─── CATCH-ALL ROUTE (must be last) ────────────────────────────────────────────
@app.get("/{full_path:path}")
async def catch_all(full_path: str, request: Request):
    """Catch any unmatched route and serve appropriate error page."""
    # Ignore API routes - they already have explicit handlers
    if full_path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")

    # For static files that might be missing, let them 404 naturally
    if any(
        full_path.endswith(ext)
        for ext in [
            ".css",
            ".js",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".webp",
            ".woff",
            ".woff2",
            ".ttf",
        ]
    ):
        raise HTTPException(404, "Static asset not found")

    # For all other paths, serve 404 page
    return _serve_error_page(404)
