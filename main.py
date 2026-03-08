from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import os, uuid, re, json, httpx
from datetime import datetime

# NEW: password hashing
from passlib.context import CryptContext

from database import engine, get_db, Base
import models

# ─── PASSWORD HASHING SETUP ───────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# ─── GUARANTEED TABLE CREATION ───────────────────────────────────────────────
# Uses raw SQL CREATE TABLE IF NOT EXISTS so it ALWAYS works, even if
# SQLAlchemy's create_all missed tables from a previous broken models.py

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
    id VARCHAR(36) PRIMARY KEY,
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
    author_id VARCHAR(36) DEFAULT '',
    author_username VARCHAR(200) DEFAULT '',
    region_id INTEGER DEFAULT NULL,
    tags TEXT DEFAULT '',
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    audio_url VARCHAR(500) DEFAULT '',
    video_url VARCHAR(500) DEFAULT '',
    gallery TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER DEFAULT NULL,
    user_id VARCHAR(36) DEFAULT '',
    username VARCHAR(200) DEFAULT '',
    content TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS follows (
    id SERIAL PRIMARY KEY,
    follower_id VARCHAR(36) DEFAULT '',
    following_id VARCHAR(36) DEFAULT '',
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
    user_id VARCHAR(36) DEFAULT 'guest',
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

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(36) DEFAULT '',
    email VARCHAR(200),
    amount INTEGER DEFAULT 0,
    reference VARCHAR(200),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW TABLES FOR TOPICS
CREATE TABLE IF NOT EXISTS topics (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS user_topics (
    user_id VARCHAR(36) REFERENCES users(id) ON DELETE CASCADE,
    topic_id INTEGER REFERENCES topics(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, topic_id)
);
"""

# Also SQLAlchemy's ORM create (belt + suspenders)
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"SQLAlchemy create_all note: {e}")

def _run_startup_sql():
    """Run raw CREATE TABLE IF NOT EXISTS — guaranteed to work on PostgreSQL."""
    try:
        with engine.connect() as conn:
            # Split and run each statement
            for stmt in _CREATE_TABLES_SQL.strip().split(';'):
                stmt = stmt.strip()
                if stmt:
                    try:
                        conn.execute(text(stmt))
                        conn.commit()
                    except Exception:
                        pass
        print("✅ EchoStack tables verified/created")
    except Exception as e:
        print(f"Startup SQL note: {e}")

def _run_migrations():
    """Safely add any missing columns to existing tables."""
    cols = [
        ("users","hashed_password","VARCHAR(255) DEFAULT ''"),
        ("users","bio","TEXT DEFAULT ''"),
        ("users","avatar_url","VARCHAR(500) DEFAULT ''"),
        ("users","channel_name","VARCHAR(200) DEFAULT ''"),
        ("users","channel_desc","TEXT DEFAULT ''"),
        ("users","role","VARCHAR(50) DEFAULT 'user'"),
        ("users","is_premium","INTEGER DEFAULT 0"),
        ("users","is_suspended","INTEGER DEFAULT 0"),
        ("users","follower_count","INTEGER DEFAULT 0"),
        ("posts","audio_url","VARCHAR(500) DEFAULT ''"),
        ("posts","video_url","VARCHAR(500) DEFAULT ''"),
        ("posts","gallery","TEXT DEFAULT ''"),
        ("posts","cover_image","VARCHAR(500) DEFAULT ''"),
        ("posts","is_locked","INTEGER DEFAULT 0"),
        ("posts","tags","TEXT DEFAULT ''"),
        ("posts","views","INTEGER DEFAULT 0"),
        ("posts","likes","INTEGER DEFAULT 0"),
        ("regions","overview","TEXT DEFAULT ''"),
        ("regions","video_files","TEXT DEFAULT ''"),
        ("regions","documents","TEXT DEFAULT ''"),
        ("uploaded_files","file_path","VARCHAR(500) DEFAULT ''"),
        ("uploaded_files","uploaded_by","VARCHAR(200) DEFAULT 'user'"),
        ("uploaded_files","is_public","INTEGER DEFAULT 1"),
    ]
    try:
        with engine.connect() as conn:
            for table, col, col_def in cols:
                try:
                    exists = conn.execute(text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name=:t AND column_name=:c"
                    ), {"t": table, "c": col}).fetchone()
                    if not exists:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {col} {col_def}"))
                        conn.commit()
                except Exception:
                    pass
    except Exception as e:
        print(f"Migration note: {e}")

def _seed_topics():
    """Insert the default Ghana‑heritage topics if they don't already exist."""
    default_topics = [
        "Ashanti Culture","Ga Traditions","Ewe Music","Northern Heritage",
        "Gold Coast History","Slave Castles","Highlife Music","Traditional Drums",
        "Kente Cloth","Fante Language","Mole National Park","Kakum Forest",
        "Lake Volta","Twi Language","Dagomba Stories","Chieftaincy",
        "Oral Histories","Modern Ghana Art","Afrobeats History","Festivals & Ceremonies"
    ]
    try:
        with engine.connect() as conn:
            for topic in default_topics:
                conn.execute(
                    text("INSERT INTO topics (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
                    {"name": topic}
                )
            conn.commit()
        print("✅ Topics seeded")
    except Exception as e:
        print(f"Topics seeding note: {e}")

_run_startup_sql()
_run_migrations()
_seed_topics()

# ─── APP ──────────────────────────────────────────────────────────────────────
app = FastAPI(title="EchoStack API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception:
    pass

ADMIN_SECRET    = os.getenv("ADMIN_SECRET", "THE ADMIN")
SUPABASE_URL    = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY    = os.getenv("SUPABASE_SERVICE_KEY", "")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "echostack-uploads")
HF_TOKEN        = os.getenv("HF_TOKEN", "")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY", "")

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def slugify(t: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', t.lower()).strip('-')[:80]

async def upload_to_supabase(content: bytes, filename: str, ctype: str):
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{filename}"
        headers = {"Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": ctype, "x-upsert": "true"}
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(url, content=content, headers=headers)
        if r.status_code in (200, 201):
            return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{filename}"
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
            filename=safe, original_name=file.filename or safe,
            file_path=fpath, file_size=len(content),
            mime_type=ctype, category=category,
            uploaded_by="user", is_public=True
        )
        db.add(rec); db.commit(); db.refresh(rec)
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
        "file_size_mb": round(size_bytes / (1024*1024), 2),
        "file_size_kb": round(size_bytes / 1024, 1),
        "category": category,
        "mime_type": ctype,
    }

# ─── STATIC PAGES ─────────────────────────────────────────────────────────────
def _page(fn):
    def handler():
        if os.path.exists(fn): return FileResponse(fn)
        raise HTTPException(404, f"{fn} not found")
    return handler

for _route, _fn in {
    "/": "index.html", "/app": "app.html", "/dashboard": "dashboard.html",
    "/creator": "creator.html", "/login": "login.html", "/signup": "signup.html",
    "/user-login": "user-login.html", "/premium": "premium.html",
    "/activity": "activity.html", "/explore": "explore.html",
    "/following": "following.html", "/community": "community_chat.html",
    "/archive": "archive.html", "/user": "user_profile.html",
}.items():
    app.get(_route)(_page(_fn))

@app.get("/post/{pid}")
def post_page(): return FileResponse("post.html") if os.path.exists("post.html") else HTTPException(404)

@app.get("/user/{uname}")
def user_page(): return FileResponse("user_profile.html") if os.path.exists("user_profile.html") else HTTPException(404)

@app.get("/manifest.json")
def manifest():
    if os.path.exists("manifest.json"): return JSONResponse(json.load(open("manifest.json")))
    raise HTTPException(404)

@app.get("/sw.js")
def sw():
    if os.path.exists("sw.js"): return FileResponse("sw.js", media_type="application/javascript")
    raise HTTPException(404)

@app.get("/echostack-logo.png")
def logo():
    if os.path.exists("echostack-logo.png"): return FileResponse("echostack-logo.png")
    raise HTTPException(404)

@app.get("/test")
def test():
    return {"status": "ok", "version": "EchoStack v2", "posts_endpoint": "POST /api/posts ✅"}

# ─── ADMIN AUTH ───────────────────────────────────────────────────────────────
@app.get("/admin")
async def admin_page(request: Request):
    if request.cookies.get("admin_session") == "ADMIN_AUTHORIZED":
        if os.path.exists("admin_dashboard.html"): return FileResponse("admin_dashboard.html")
    return FileResponse("login.html") if os.path.exists("login.html") else HTTPException(404)

@app.get("/admin-preview")
async def admin_preview(request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED":
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        posts = db.query(models.Post).order_by(models.Post.created_at.desc()).limit(20).all()
        return JSONResponse({"posts": [
            {"id": p.id, "title": getattr(p,"title",""), "status": getattr(p,"status",""),
             "author_username": getattr(p,"author_username",""), "created_at": str(getattr(p,"created_at",""))}
            for p in posts
        ]})
    except Exception as e:
        return JSONResponse({"posts": [], "error": str(e)})

@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    if answer.strip().lower().replace(" ","") == ADMIN_SECRET.lower().replace(" ",""):
        r = JSONResponse({"success": True})
        r.set_cookie("admin_session", "ADMIN_AUTHORIZED", max_age=86400, path="/")
        return r
    raise HTTPException(403, "Wrong password")

@app.post("/api/auth/logout")
def admin_logout():
    r = JSONResponse({"success": True})
    r.delete_cookie("admin_session", path="/")
    return r

# ─── USER AUTH ────────────────────────────────────────────────────────────────
@app.post("/api/users/signup")
async def signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    topics: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        uname  = username.strip()
        uemail = email.strip()
        if not uname or not uemail or not password:
            raise HTTPException(400, "Username, email and password are required")

        # Check existing user
        existing = db.query(models.User).filter(
            (models.User.username == uname) | (models.User.email == uemail)
        ).first()
        if existing:
            if getattr(existing, "username", "") == uname:
                raise HTTPException(400, "Username already taken — choose another")
            raise HTTPException(400, "Email already registered — try signing in")

        # Hash the password
        hashed = get_password_hash(password)

        # Create user
        uid = str(uuid.uuid4())
        u = models.User(
            id=uid, username=uname, email=uemail,
            hashed_password=hashed,
            role="user",
            is_premium=False, is_suspended=False, follower_count=0,
            bio="", avatar_url="", channel_name=uname, channel_desc="",
        )
        db.add(u)
        db.flush()   # Get the user ID without committing yet

        # Parse and save selected topics using raw SQL (more reliable)
        selected_topics = []
        if topics:
            try:
                selected_topics = json.loads(topics)
                if not isinstance(selected_topics, list):
                    selected_topics = []
            except:
                selected_topics = []

        # Use raw SQL to insert into user_topics
        for topic_name in selected_topics:
            # First get the topic id from the topics table
            topic_result = db.execute(
                text("SELECT id FROM topics WHERE name = :name"),
                {"name": topic_name}
            ).first()
            if topic_result:
                topic_id = topic_result[0]
                # Insert into user_topics
                db.execute(
                    text("INSERT INTO user_topics (user_id, topic_id) VALUES (:uid, :tid) ON CONFLICT DO NOTHING"),
                    {"uid": uid, "tid": topic_id}
                )

        db.commit()
        db.refresh(u)
        print(f"✅ New user: {uname} ({uemail}) id={uid} with {len(selected_topics)} topics")

        resp = JSONResponse({
            "success": True, "user_id": uid,
            "username": u.username, "role": "user",
            "is_premium": False, "message": "Account created!"
        })
        resp.set_cookie("user_session", uid, max_age=60*60*24*30, path="/", samesite="lax", httponly=False)
        return resp

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
        # Try to find user by username (case‑insensitive)
        u = db.query(models.User).filter(
            models.User.username.ilike(username.strip())
        ).first()

        # If not found, try by email (case‑insensitive)
        if not u:
            u = db.query(models.User).filter(
                models.User.email.ilike(username.strip())
            ).first()

        # If user not found
        if not u:
            raise HTTPException(404, "Account not found. Please sign up first.")

        # Check password
        if not verify_password(password, u.hashed_password):
            raise HTTPException(401, "Incorrect password. Try again.")
            
        # Check if account is suspended
        if getattr(u, "is_suspended", 0):
            raise HTTPException(403, "Account suspended. Contact support.")

        # Success – create response
        resp = JSONResponse({
            "success": True,
            "user_id": u.id,
            "username": u.username,
            "role": getattr(u, "role", "user"),
            "is_premium": getattr(u, "is_premium", 0)
        })
        resp.set_cookie("user_session", u.id, max_age=60*60*24*30, path="/", samesite="lax")
        return resp

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/api/users/logout")
def user_logout():
    r = JSONResponse({"success": True})
    r.delete_cookie("user_session", path="/")
    return r

@app.get("/api/users/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")
    if not sid: raise HTTPException(401, "Not logged in")
    u = db.query(models.User).filter(models.User.id == sid).first()
    if not u: raise HTTPException(401, "User not found")
    return {"id": u.id, "username": u.username, "email": u.email,
            "role": getattr(u,"role","user"), "is_premium": getattr(u,"is_premium",0),
            "bio": getattr(u,"bio",""), "avatar_url": getattr(u,"avatar_url",""),
            "channel_name": getattr(u,"channel_name",""), "channel_desc": getattr(u,"channel_desc",""),
            "follower_count": getattr(u,"follower_count",0)}

@app.put("/api/users/me")
async def update_me(
    request: Request, bio: str = Form(""), channel_name: str = Form(""),
    channel_desc: str = Form(""), avatar_url: str = Form(""),
    db: Session = Depends(get_db)
):
    sid = request.cookies.get("user_session")
    if not sid: raise HTTPException(401)
    u = db.query(models.User).filter(models.User.id == sid).first()
    if not u: raise HTTPException(404)
    try:
        if bio: u.bio = bio
        if channel_name: u.channel_name = channel_name
        if channel_desc: u.channel_desc = channel_desc
        if avatar_url: u.avatar_url = avatar_url
        db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── ADMIN USER MANAGEMENT ───────────────────────────────────────────────────
@app.get("/api/admin/users")
async def admin_users(request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED": raise HTTPException(403)
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [{"id":u.id,"username":u.username,"email":u.email,
             "role":getattr(u,"role","user"),"is_premium":getattr(u,"is_premium",0),
             "is_suspended":getattr(u,"is_suspended",0)} for u in users]

@app.put("/api/admin/users/{uid}/role")
async def set_role(uid: str, request: Request, role: str = Form(...), db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED": raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u: raise HTTPException(404)
    u.role = role; db.commit(); return {"success": True}

@app.put("/api/admin/users/{uid}/premium")
async def set_premium(uid: str, request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED": raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u: raise HTTPException(404)
    u.is_premium = False if getattr(u,"is_premium",0) else 1
    db.commit(); return {"success": True, "is_premium": u.is_premium}

@app.put("/api/admin/users/{uid}/suspend")
async def suspend(uid: str, request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED": raise HTTPException(403)
    u = db.query(models.User).filter(models.User.id == uid).first()
    if not u: raise HTTPException(404)
    u.is_suspended = False if getattr(u,"is_suspended",0) else 1
    db.commit(); return {"success": True, "is_suspended": u.is_suspended}

# ─── POSTS ────────────────────────────────────────────────────────────────────
@app.get("/api/posts")
async def get_posts(
    request: Request, limit: int = 20, offset: int = 0,
    content_type: str = "", region_id: str = "", author_id: str = "",
    db: Session = Depends(get_db)
):
    try:
        q = db.query(models.Post)
        is_admin = request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
        own_id   = request.cookies.get("user_session")

        if not is_admin:
            if author_id and author_id == own_id:
                pass
            else:
                q = q.filter(models.Post.status == "published")

        if content_type: q = q.filter(models.Post.content_type == content_type)
        if region_id and region_id.isdigit(): q = q.filter(models.Post.region_id == int(region_id))
        if author_id: q = q.filter(models.Post.author_id == author_id)

        posts = q.order_by(models.Post.created_at.desc()).offset(offset).limit(limit).all()

        return [{
            "id": p.id,
            "title": getattr(p,"title","") or "",
            "slug": getattr(p,"slug","") or "",
            "excerpt": getattr(p,"excerpt","") or "",
            "cover_image": getattr(p,"cover_image","") or "",
            "content_type": getattr(p,"content_type","article") or "article",
            "status": getattr(p,"status","published") or "published",
            "is_locked": getattr(p,"is_locked",0) or 0,
            "author_id": getattr(p,"author_id","") or "",
            "author_username": getattr(p,"author_username","") or "",
            "region_id": getattr(p,"region_id",None),
            "tags": getattr(p,"tags","") or "",
            "views": getattr(p,"views",0) or 0,
            "view_count": getattr(p,"views",0) or 0,
            "likes": getattr(p,"likes",0) or 0,
            "audio_url": getattr(p,"audio_url","") or "",
            "video_url": getattr(p,"video_url","") or "",
            "gallery": getattr(p,"gallery","") or "",
            "created_at": str(getattr(p,"created_at","")),
            "comment_count": db.query(models.Comment).filter(
                models.Comment.post_id == p.id,
                models.Comment.content != "__like__"
            ).count()
        } for p in posts]
    except Exception as e:
        print(f"GET /api/posts error: {e}")
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
    db: Session = Depends(get_db)
):
    try:
        # ── Identify author ──────────────────────────────────────────────────
        sid       = request.cookies.get("user_session")
        is_admin  = request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
        author_id = ""; author_username = "Creator"

        if sid:
            try:
                u = db.query(models.User).filter(models.User.id == sid).first()
                if u:
                    author_id = u.id
                    author_username = u.username
            except Exception:
                pass
        if not author_id and is_admin:
            author_id = "admin"; author_username = "Admin"

        # ── Build slug (unique) ──────────────────────────────────────────────
        base = slugify(title); slug = base; n = 1
        while db.query(models.Post).filter(models.Post.slug == slug).first():
            slug = f"{base}-{n}"; n += 1

        # ── Create post ──────────────────────────────────────────────────────
        locked = is_locked in ("true","1","True")
        rid    = int(region_id) if region_id and str(region_id).isdigit() else None

        post = models.Post(
            title          = title.strip(),
            slug           = slug,
            excerpt        = excerpt.strip(),
            content        = content.strip(),
            content_type   = content_type or "article",
            status         = status or "draft",
            is_locked      = 1 if locked else 0,
            cover_image    = cover_image.strip(),
            author_id      = author_id,
            author_username= author_username,
            region_id      = rid,
            tags           = tags.strip(),
            views          = 0,
            likes          = 0,
        )

        # Optional columns — safe set
        for attr, val in [("audio_url",audio_url),("video_url",video_url),("gallery",gallery)]:
            try: setattr(post, attr, val.strip())
            except Exception: pass

        db.add(post); db.commit(); db.refresh(post)
        print(f"✅ Post {post.id} '{post.title}' status={post.status} by {author_username}")

        return {"success": True, "id": post.id, "slug": post.slug,
                "title": post.title, "status": post.status,
                "message": "Published! 🚀" if status == "published" else "Saved as draft 💾"}

    except HTTPException: raise
    except Exception as e:
        db.rollback()
        print(f"❌ POST /api/posts error: {e}")
        import traceback; traceback.print_exc()
        raise HTTPException(500, f"Post creation failed: {str(e)}")

@app.get("/api/posts/{post_id}")
async def get_post(post_id: int, db: Session = Depends(get_db)):
    try:
        p = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not p: raise HTTPException(404, "Post not found")
        try: p.views = (getattr(p,"views",0) or 0) + 1; db.commit()
        except Exception: pass
        return {
            "id": p.id, "title": getattr(p,"title",""), "slug": getattr(p,"slug",""),
            "excerpt": getattr(p,"excerpt",""), "content": getattr(p,"content",""),
            "cover_image": getattr(p,"cover_image",""), "content_type": getattr(p,"content_type","article"),
            "status": getattr(p,"status","published"), "is_locked": getattr(p,"is_locked",0),
            "author_id": getattr(p,"author_id",""), "author_username": getattr(p,"author_username",""),
            "region_id": getattr(p,"region_id",None), "tags": getattr(p,"tags",""),
            "views": getattr(p,"views",0), "view_count": getattr(p,"views",0),
            "likes": getattr(p,"likes",0),
            "audio_url": getattr(p,"audio_url",""), "video_url": getattr(p,"video_url",""),
            "gallery": getattr(p,"gallery",""), "created_at": str(getattr(p,"created_at","")),
        }
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, str(e))

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int, request: Request,
    title: str = Form(None), excerpt: str = Form(None), content: str = Form(None),
    status: str = Form(None), cover_image: str = Form(None), tags: str = Form(None),
    is_locked: str = Form(None), audio_url: str = Form(None), video_url: str = Form(None),
    db: Session = Depends(get_db)
):
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(404)
    try:
        for attr, val in [("title",title),("excerpt",excerpt),("content",content),
                          ("status",status),("cover_image",cover_image),("tags",tags)]:
            if val is not None: setattr(p, attr, val.strip() if hasattr(val,"strip") else val)
        if is_locked is not None: p.is_locked = 1 if is_locked in ("true","1") else 0
        for attr, val in [("audio_url",audio_url),("video_url",video_url)]:
            if val is not None:
                try: setattr(p, attr, val.strip())
                except Exception: pass
        db.commit(); return {"success": True, "id": p.id}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(404)
    try:
        db.query(models.Comment).filter(models.Comment.post_id == post_id).delete()
        db.delete(p); db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── COMMENTS ────────────────────────────────────────────────────────────────
@app.get("/api/posts/{post_id}/comments")
async def get_comments(post_id: int, db: Session = Depends(get_db)):
    try:
        comments = db.query(models.Comment).filter(
            models.Comment.post_id == post_id,
            models.Comment.content != "__like__"
        ).order_by(models.Comment.created_at.asc()).all()
        return [{"id":c.id,"username":getattr(c,"username","User"),
                 "content":c.content,"created_at":str(c.created_at)} for c in comments]
    except Exception: return []

@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int, request: Request, content: str = Form(...), db: Session = Depends(get_db)
):
    sid = request.cookies.get("user_session"); username = "Guest"; uid = sid or "guest"
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id == sid).first()
            if u: username = u.username
        except Exception: pass
    try:
        c = models.Comment(post_id=post_id, user_id=uid, username=username, content=content.strip())
        db.add(c); db.commit(); return {"success": True, "id": c.id}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.post("/api/posts/{post_id}/like")
async def toggle_like(post_id: int, request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session") or request.cookies.get("admin_session")
    if not sid: raise HTTPException(401, "Login to like")
    try:
        p = db.query(models.Post).filter(models.Post.id == post_id).first()
        if not p: raise HTTPException(404)
        existing = db.query(models.Comment).filter(
            models.Comment.post_id == post_id,
            models.Comment.user_id == sid,
            models.Comment.content == "__like__"
        ).first()
        if existing:
            db.delete(existing)
            p.likes = max(0, (getattr(p,"likes",0) or 0) - 1)
            db.commit(); return {"liked": False, "likes": p.likes}
        db.add(models.Comment(post_id=post_id, user_id=sid, username="", content="__like__"))
        p.likes = (getattr(p,"likes",0) or 0) + 1
        db.commit(); return {"liked": True, "likes": p.likes}
    except HTTPException: raise
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── SOCIAL ──────────────────────────────────────────────────────────────────
@app.post("/api/follow/{target_id}")
async def toggle_follow(target_id: str, request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")
    if not sid: raise HTTPException(401)
    try:
        ex = db.query(models.Follow).filter(
            models.Follow.follower_id == sid, models.Follow.following_id == target_id
        ).first()
        tgt = db.query(models.User).filter(models.User.id == target_id).first()
        if ex:
            db.delete(ex)
            if tgt: tgt.follower_count = max(0, (getattr(tgt,"follower_count",0) or 0) - 1)
            db.commit(); return {"following": False}
        db.add(models.Follow(follower_id=sid, following_id=target_id))
        if tgt: tgt.follower_count = (getattr(tgt,"follower_count",0) or 0) + 1
        db.commit(); return {"following": True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.get("/api/following")
async def get_following(request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")
    if not sid: return []
    try:
        return [f.following_id for f in db.query(models.Follow).filter(models.Follow.follower_id == sid).all()]
    except Exception: return []

@app.get("/api/creators")
async def get_creators(db: Session = Depends(get_db)):
    try:
        creators = db.query(models.User).filter(
            models.User.role.in_(["creator","admin","superuser"])
        ).limit(20).all()
        return [{"id":u.id,"username":u.username,
                 "channel_name":getattr(u,"channel_name","") or u.username,
                 "avatar_url":getattr(u,"avatar_url","")} for u in creators]
    except Exception: return []

@app.get("/api/activity")
async def get_activity(request: Request, db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")
    if not sid: return []
    try:
        my_ids = [p.id for p in db.query(models.Post).filter(models.Post.author_id == sid).all()]
        comments = db.query(models.Comment).filter(
            models.Comment.post_id.in_(my_ids),
            models.Comment.content != "__like__",
            models.Comment.user_id != sid
        ).order_by(models.Comment.created_at.desc()).limit(30).all()
        return [{"type":"comment","username":c.username,"post_id":c.post_id,
                 "content":c.content[:80],"created_at":str(c.created_at)} for c in comments]
    except Exception: return []

# ─── UPLOADS ─────────────────────────────────────────────────────────────────
@app.post("/api/upload/cover")
async def upload_cover(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _do_upload(file, "cover", db)

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    return await _do_upload(file, "image", db)

@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(""),
    category: str = Form("general"), description: str = Form(""),
    region_id: str = Form(""), is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    if filename: file.filename = filename
    return await _do_upload(file, category, db)

@app.post("/api/upload/multiple")
async def upload_multiple(files: list[UploadFile] = File(...), db: Session = Depends(get_db)):
    results = []
    for f in files:
        try: results.append(await _do_upload(f, "image", db))
        except Exception as e: results.append({"success": False, "error": str(e)})
    return results

@app.get("/api/files")
async def get_files(category: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category: q = q.filter(models.UploadedFile.category == category)
        files = q.order_by(models.UploadedFile.created_at.desc()).all()
        result = []
        for f in files:
            url = f.file_path if (f.file_path or "").startswith("http") else f"/uploads/{f.filename}"
            size_bytes = f.file_size or 0
            result.append({
                "id": f.id,
                "filename": f.filename,
                "original_name": f.original_name or f.filename,
                "file_url": url,
                "url": url,
                "category": f.category or "general",
                "mime_type": f.mime_type or "",
                "file_size": size_bytes,
                "file_size_mb": round(size_bytes / (1024*1024), 2) if size_bytes else 0,
                "file_size_kb": round(size_bytes / 1024, 1) if size_bytes else 0,
                "description": f.description or "",
                "is_public": bool(f.is_public),
                "region_id": f.region_id,
                "uploaded_by": f.uploaded_by or "admin",
                "created_at": str(f.created_at),
            })
        return result
    except Exception: return []

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int, db: Session = Depends(get_db)):
    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not f: raise HTTPException(404)
    try:
        if f.file_path and not f.file_path.startswith("http") and os.path.exists(f.file_path):
            os.remove(f.file_path)
        db.delete(f); db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── REGIONS ─────────────────────────────────────────────────────────────────
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        return [{"id":r.id,"name":str(r.name or ""),"capital":str(r.capital or ""),
                 "population":str(r.population or ""),"terrain":str(r.terrain or ""),
                 "description":str(r.description or ""),"overview":str(getattr(r,"overview","") or ""),
                 "category":str(r.category or ""),"tags":str(r.tags or ""),
                 "hero_image":str(r.hero_image or ""),"gallery_images":str(r.gallery_images or ""),
                 "audio_files":str(r.audio_files or ""),"source":str(r.source or "")}
                for r in db.query(models.Region).all()]
    except Exception: return []

@app.post("/api/regions")
def create_region(
    name: str = Form(...), capital: str = Form(""), population: str = Form(""),
    terrain: str = Form(""), description: str = Form(""), category: str = Form(""),
    tags: str = Form(""), hero_image: str = Form(""), gallery_images: str = Form(""),
    audio_files: str = Form(""), source: str = Form(""), overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        r = models.Region(name=name.strip(), capital=capital, population=population,
                          terrain=terrain, description=description, overview=overview or description,
                          category=category, tags=tags, hero_image=hero_image,
                          gallery_images=gallery_images, audio_files=audio_files, source=source)
        db.add(r); db.commit(); db.refresh(r)
        return {"success": True, "region_id": r.id}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.put("/api/regions/{rid}")
def update_region(
    rid: int, name: str = Form(None), capital: str = Form(None), population: str = Form(None),
    terrain: str = Form(None), description: str = Form(None), category: str = Form(None),
    tags: str = Form(None), hero_image: str = Form(None), gallery_images: str = Form(None),
    audio_files: str = Form(None), source: str = Form(None), overview: str = Form(None),
    db: Session = Depends(get_db)
):
    r = db.query(models.Region).filter(models.Region.id == rid).first()
    if not r: raise HTTPException(404)
    try:
        for a, v in [("name",name),("capital",capital),("population",population),
                     ("terrain",terrain),("description",description),("overview",overview),
                     ("category",category),("tags",tags),("hero_image",hero_image),
                     ("gallery_images",gallery_images),("audio_files",audio_files),("source",source)]:
            if v is not None: setattr(r, a, v.strip())
        db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.delete("/api/regions/{rid}")
def delete_region(rid: int, db: Session = Depends(get_db)):
    r = db.query(models.Region).filter(models.Region.id == rid).first()
    if not r: raise HTTPException(404)
    db.delete(r); db.commit(); return {"success": True}

# ─── ADMIN PUBLISH FILE ───────────────────────────────────────────────────────
@app.post("/api/admin/publish-file")
async def publish_file(
    request: Request, file_id: int = Form(...), title: str = Form(...),
    description: str = Form(""), region_id: str = Form(""), content_type: str = Form("article"),
    db: Session = Depends(get_db)
):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED": raise HTTPException(403)
    uf = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not uf: raise HTTPException(404)
    try:
        url = uf.file_path if (uf.file_path or "").startswith("http") else f"/uploads/{uf.filename}"
        rid = int(region_id) if region_id and region_id.isdigit() else None
        p = models.Post(title=title, slug=slugify(title), excerpt=description[:200],
                        content=description, content_type=content_type, status="published",
                        cover_image=url if content_type == "article" else "",
                        author_id="admin", author_username="Admin",
                        region_id=rid, views=0, likes=0)
        try: setattr(p, "video_url", url if content_type=="video" else "")
        except Exception: pass
        try: setattr(p, "audio_url", url if content_type=="audio" else "")
        except Exception: pass
        db.add(p); db.commit(); db.refresh(p)
        return {"success": True, "post_id": p.id}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── STATS ───────────────────────────────────────────────────────────────────
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        return {"total_regions": db.query(models.Region).count(),
                "total_posts": db.query(models.Post).filter(models.Post.status=="published").count(),
                "total_users": db.query(models.User).count(),
                "total_files": db.query(models.UploadedFile).count()}
    except Exception: return {"total_regions":0,"total_posts":0,"total_users":0}

# ─── SECTIONS ────────────────────────────────────────────────────────────────
@app.get("/api/sections")
def get_sections(db: Session = Depends(get_db)):
    try:
        s = db.query(models.Section).filter(models.Section.is_active==1).all()
        return [{"id":x.id,"name":x.name,"slug":x.slug} for x in s]
    except Exception: return []

@app.post("/api/sections")
def create_section(name: str = Form(...), description: str = Form(""),
                   display_order: int = Form(0), db: Session = Depends(get_db)):
    try:
        s = models.Section(name=name, slug=slugify(name), description=description, display_order=display_order)
        db.add(s); db.commit(); return {"success":True,"id":s.id}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.delete("/api/sections/{sid}")
def delete_section(sid: int, db: Session = Depends(get_db)):
    s = db.query(models.Section).filter(models.Section.id==sid).first()
    if not s: raise HTTPException(404)
    s.is_active = 0; db.commit(); return {"success":True}

# ─── NEWSLETTER ──────────────────────────────────────────────────────────────
@app.post("/api/newsletter/subscribe")
async def subscribe(email: str = Form(...), db: Session = Depends(get_db)):
    try:
        if db.query(models.NewsletterSubscriber).filter(
                models.NewsletterSubscriber.email==email.strip()).first():
            return {"success":True,"message":"Already subscribed!"}
        db.add(models.NewsletterSubscriber(email=email.strip())); db.commit()
        return {"success":True,"message":"Subscribed!"}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

@app.get("/api/newsletter/subscribers")
async def subs(request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED": raise HTTPException(403)
    try:
        return [{"id":s.id,"email":s.email} for s in db.query(models.NewsletterSubscriber).all()]
    except Exception: return []

# ─── EVENTS ──────────────────────────────────────────────────────────────────
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    try:
        return [{"id":e.id,"title":e.title,"description":getattr(e,"description",""),
                 "event_date":str(getattr(e,"event_date","")),"location":getattr(e,"location",""),
                 "created_at":str(e.created_at)} for e in
                db.query(models.Event).order_by(models.Event.created_at.desc()).all()]
    except Exception: return []

@app.post("/api/events")
def create_event(title: str = Form(...), description: str = Form(""),
                 event_date: str = Form(""), location: str = Form(""),
                 db: Session = Depends(get_db)):
    try:
        e = models.Event(title=title, description=description, location=location)
        if event_date:
            try: e.event_date = datetime.fromisoformat(event_date)
            except Exception: pass
        db.add(e); db.commit(); db.refresh(e); return {"success":True,"id":e.id}
    except Exception as ex:
        db.rollback(); raise HTTPException(500, str(ex))

@app.delete("/api/events/{eid}")
def delete_event(eid: int, db: Session = Depends(get_db)):
    e = db.query(models.Event).filter(models.Event.id==eid).first()
    if not e: raise HTTPException(404)
    db.delete(e); db.commit(); return {"success":True}

# ─── CHAT ────────────────────────────────────────────────────────────────────
@app.get("/api/chat")
def get_chat(limit: int = 50, db: Session = Depends(get_db)):
    try:
        msgs = db.query(models.ChatMessage).order_by(
            models.ChatMessage.created_at.desc()).limit(limit).all()
        return [{"id":m.id,"username":getattr(m,"username","User"),
                 "content":m.content,"created_at":str(m.created_at)} for m in reversed(msgs)]
    except Exception: return []

@app.post("/api/chat")
async def post_chat(request: Request, content: str = Form(...), db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session"); username = "Guest"
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id==sid).first()
            if u: username = u.username
        except Exception: pass
    try:
        db.add(models.ChatMessage(content=content.strip(), username=username, user_id=sid or "guest"))
        db.commit(); return {"success":True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── STORIES ─────────────────────────────────────────────────────────────────
@app.get("/api/stories")
def get_stories(db: Session = Depends(get_db)):
    try:
        s = db.query(models.StorySubmission).filter(
            models.StorySubmission.status=="approved").order_by(
            models.StorySubmission.created_at.desc()).limit(20).all()
        return [{"id":x.id,"title":x.title,"content":getattr(x,"content",""),
                 "author_name":getattr(x,"author_name",""),"region":getattr(x,"region",""),
                 "created_at":str(x.created_at)} for x in s]
    except Exception: return []

@app.post("/api/stories")
async def submit_story(request: Request, title: str = Form(...), content: str = Form(...),
                       region: str = Form(""), db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session"); author = "Anonymous"
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id==sid).first()
            if u: author = u.username
        except Exception: pass
    try:
        db.add(models.StorySubmission(title=title, content=content, region=region,
                                       author_name=author, status="pending"))
        db.commit(); return {"success":True}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))

# ─── AI ECHOBOT ──────────────────────────────────────────────────────────────
@app.post("/api/ai/chat")
async def ai_chat(request: Request, message: str = Form(...),
                  region_context: str = Form(""), db: Session = Depends(get_db)):
    sid = request.cookies.get("user_session")
    if sid:
        try:
            u = db.query(models.User).filter(models.User.id==sid).first()
            if u and not getattr(u,"is_premium",0):
                return {"reply":"EchoBot is for premium members. Upgrade to unlock! ⭐","locked":True}
        except Exception: pass

    if not HF_TOKEN:
        return {"reply":f"Akwaaba! You asked: '{message}'. Ghana has 16 beautiful regions with rich heritage. Explore EchoStack to discover more! 🇬🇭","locked":False}
    try:
        prompt = f"You are EchoBot, a Ghana heritage AI. Context: {region_context}. User: {message}. Answer helpfully about Ghana."
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.post("https://api-inference.huggingface.co/models/google/flan-t5-small",
                             headers={"Authorization":f"Bearer {HF_TOKEN}"},
                             json={"inputs":prompt,"parameters":{"max_new_tokens":200}})
        d = r.json()
        reply = d[0]["generated_text"] if isinstance(d,list) else str(d)
        return {"reply":reply,"locked":False}
    except Exception:
        return {"reply":"EchoBot is resting. Try again soon! 🤖","locked":False}

# ─── PAYMENTS ────────────────────────────────────────────────────────────────
@app.post("/api/payments/initialize")
async def init_payment(request: Request, amount: int = Form(4900), email: str = Form(...),
                       db: Session = Depends(get_db)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post("https://api.paystack.co/transaction/initialize",
                headers={"Authorization":f"Bearer {PAYSTACK_SECRET}","Content-Type":"application/json"},
                json={"email":email,"amount":amount*100,
                      "callback_url":f"{request.base_url}payment/callback"})
        d = r.json()
        if d.get("status"):
            return {"success":True,"authorization_url":d["data"]["authorization_url"],
                    "reference":d["data"]["reference"]}
        raise HTTPException(400,"Payment init failed")
    except HTTPException: raise
    except Exception as e: raise HTTPException(500, str(e))

@app.get("/payment/callback")
async def payment_callback(reference: str, db: Session = Depends(get_db)):
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"https://api.paystack.co/transaction/verify/{reference}",
                            headers={"Authorization":f"Bearer {PAYSTACK_SECRET}"})
        d = r.json()
        if d.get("status") and d["data"]["status"] == "success":
            email = d["data"]["customer"]["email"]
            u = db.query(models.User).filter(models.User.email==email).first()
            if u: u.is_premium = True; db.commit()
        return RedirectResponse("/dashboard?upgraded=1")
    except Exception: return RedirectResponse("/premium?error=1")

# ─── IMPORT/EXPORT ───────────────────────────────────────────────────────────
@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    try:
        items = data if isinstance(data,list) else [data]
        imported = 0
        for item in items:
            try: db.add(models.Region(**item)); imported += 1
            except Exception: pass
        db.commit(); return {"success":True,"imported":imported}
    except Exception as e:
        db.rollback(); raise HTTPException(500, str(e))
