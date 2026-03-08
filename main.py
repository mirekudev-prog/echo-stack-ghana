# ============================================
# ECHOSTACK GHANA - COMPLETE BACKEND (main.py)
# ============================================
from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from sqlalchemy.orm import Session
import os, json, re, hashlib, datetime, urllib.request, uuid
from pathlib import Path

# ============================================
# DATABASE SETUP
# ============================================
from database import engine, get_db, Base, SessionLocal
import models

# ── Step 1: create brand-new tables ──────────────────────────
Base.metadata.create_all(bind=engine)

# ── Step 2: safe ALTER TABLE migrations for existing tables ──
def _run_migrations():
    """Add missing columns to existing PostgreSQL tables without data loss."""
    from sqlalchemy import text

    def col_exists(conn, tbl, col):
        r = conn.execute(text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ), {"t": tbl, "c": col})
        return r.fetchone() is not None

    def tbl_exists(conn, tbl):
        r = conn.execute(text(
            "SELECT 1 FROM information_schema.tables WHERE table_name=:t"
        ), {"t": tbl})
        return r.fetchone() is not None

    def add(conn, tbl, col, typ, default=None):
        if tbl_exists(conn, tbl) and not col_exists(conn, tbl, col):
            dflt = f" DEFAULT {default}" if default is not None else ""
            conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN {col} {typ}{dflt}"))
            print(f"  migration: added {tbl}.{col}")

    migrations = [
        # regions
        ("regions", "video_files",  "TEXT",         None),
        ("regions", "documents",    "TEXT",         None),
        ("regions", "overview",     "TEXT",         None),
        # users
        ("users", "full_name",      "VARCHAR(200)", None),
        ("users", "bio",            "TEXT",         None),
        ("users", "interests",      "TEXT",         None),
        ("users", "avatar_url",     "VARCHAR(500)", None),
        ("users", "role",           "VARCHAR(20)",  "'user'"),
        ("users", "is_premium",     "BOOLEAN",      "FALSE"),
        ("users", "is_active",      "BOOLEAN",      "TRUE"),
        ("users", "updated_at",     "TIMESTAMP",    "NOW()"),
        # posts
        ("posts", "author_username","VARCHAR(80)",  "''"),
        ("posts", "audio_url",      "VARCHAR(500)", None),
        ("posts", "video_url",      "VARCHAR(500)", None),
        ("posts", "gallery",        "TEXT",         None),
        ("posts", "tags",           "VARCHAR",      None),
        ("posts", "views",          "INTEGER",      "0"),
        ("posts", "likes",          "INTEGER",      "0"),
        ("posts", "comment_count",  "INTEGER",      "0"),
        ("posts", "published_at",   "TIMESTAMP",    None),
        ("posts", "updated_at",     "TIMESTAMP",    "NOW()"),
        # story_submissions
        ("story_submissions", "user_id",    "VARCHAR(36)", None),
        ("story_submissions", "updated_at", "TIMESTAMP",   "NOW()"),
        # uploaded_files
        ("uploaded_files", "updated_at", "TIMESTAMP", "NOW()"),
        # creator_channels
        ("creator_channels", "channel_desc", "TEXT",         None),
        ("creator_channels", "cover_image",  "VARCHAR(500)", None),
        ("creator_channels", "avatar_url",   "VARCHAR(500)", None),
        ("creator_channels", "updated_at",   "TIMESTAMP",    "NOW()"),
        # comments
        ("comments", "author_username", "VARCHAR(80)", "''"),
        ("comments", "is_approved",     "INTEGER",     "1"),
        # events
        ("events", "updated_at", "TIMESTAMP", "NOW()"),
        ("events", "is_active",  "BOOLEAN",   "TRUE"),
        # payments
        ("payments", "updated_at", "TIMESTAMP", "NOW()"),
    ]

    with engine.connect() as conn:
        for tbl, col, typ, dflt in migrations:
            try:
                add(conn, tbl, col, typ, dflt)
            except Exception as e:
                print(f"  migration warning ({tbl}.{col}): {e}")
        conn.commit()

try:
    _run_migrations()
    print("✅ Migrations complete")
except Exception as _me:
    print(f"Migration warning (non-fatal): {_me}")

# ============================================
# APP SETUP
# ============================================
app = FastAPI(title="EchoStack API")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads: {e}")

# Config
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "THE ADMIN")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# ============================================
# HELPERS
# ============================================
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def verify_password(p: str, h: str) -> bool:
    return hash_password(p) == h

def get_user_from_request(request: Request, db: Session):
    user_id = request.cookies.get("user_session")
    if not user_id:
        return None
    try:
        uid = uuid.UUID(str(user_id))
        return db.query(models.User).filter(models.User.id == uid).first()
    except (ValueError, AttributeError, TypeError):
        try:
            return db.query(models.User).filter(models.User.id == int(user_id)).first()
        except:
            return None

def require_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token != "ADMIN_AUTHORIZED":
        raise HTTPException(status_code=403, detail="Not authorized")

async def save_upload(file: UploadFile) -> str:
    content = await file.read()
    safe = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename.replace(' ', '_')}"
    path = UPLOAD_DIR / safe
    with open(path, "wb") as f:
        f.write(content)
    return f"/uploads/{safe}"

def get_db_knowledge(db: Session) -> str:
    try:
        regions = db.query(models.Region).all()
        knowledge = "GHANA REGIONS DATABASE:\n"
        for r in regions:
            knowledge += f"- {r.name}"
            if r.capital: knowledge += f" (Capital: {r.capital})"
            if r.population: knowledge += f", Pop: {r.population}"
            if r.terrain: knowledge += f", Terrain: {r.terrain}"
            if r.category: knowledge += f", Category: {r.category}"
            if r.description:
                desc = r.description[:200].replace("\n", " ")
                knowledge += f"\n  Info: {desc}"
            knowledge += "\n"
        return knowledge[:3000]
    except:
        return "Region data unavailable."

# ============================================
# STATIC PAGE HELPER
# ============================================
def serve_file(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename)
    raise HTTPException(status_code=404, detail=f"{filename} not found")

# ============================================
# PUBLIC PAGES
# ============================================
@app.get("/")
def homepage(): return serve_file("index.html")

@app.get("/signup")
def signup_page(): return serve_file("signup.html")

@app.get("/user-login")
def user_login_page(): return serve_file("user-login.html")

@app.get("/dashboard")
async def dashboard_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("dashboard.html")

@app.get("/creator")
async def creator_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("creator.html")

@app.get("/post/{post_id}")
async def post_page(post_id: int, request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("post.html")

@app.get("/app")
async def app_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("app.html")

@app.get("/admin")
async def admin_page(request: Request):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED":
        return serve_file("login.html")
    return serve_file("admin_dashboard.html")

@app.get("/admin-preview")
async def admin_preview(request: Request, db: Session = Depends(get_db)):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED":
        return RedirectResponse(url="/admin")
    try:
        admin_user = db.query(models.User).filter(
            models.User.role.in_(["superuser", "admin"])
        ).first()
        if not admin_user:
            # Try to create admin user
            try:
                admin_user = models.User(
                    username="admin",
                    email="admin@echostack.gh",
                    password_hash=hash_password("admin_temp_password"),
                    role="superuser",
                )
                # Set optional fields safely
                try: admin_user.is_premium = True
                except: pass
                try: admin_user.is_active = True
                except: pass
                db.add(admin_user)
                db.commit()
                db.refresh(admin_user)
            except Exception as create_err:
                db.rollback()
                print(f"Admin preview create error: {create_err}")
                # Fall through with a fake ID so at least the redirect works
                fake_html = """<!DOCTYPE html><html><head><title>EchoStack</title></head><body>
<script>
localStorage.setItem('es_user', JSON.stringify({loggedIn:true,username:'admin',role:'superuser',is_premium:1}));
window.location.href = '/app';
</script><p>Redirecting to app...</p></body></html>"""
                return HTMLResponse(content=fake_html)

        user_id = str(admin_user.id)
        username = str(admin_user.username)
    except Exception as e:
        print(f"Admin preview error: {e}")
        fallback = """<!DOCTYPE html><html><head><title>EchoStack</title></head><body>
<script>
localStorage.setItem('es_user', JSON.stringify({loggedIn:true,username:'admin',role:'superuser',is_premium:1}));
window.location.href = '/app';
</script><p>Redirecting...</p></body></html>"""
        return HTMLResponse(content=fallback)

    html = f"""<!DOCTYPE html><html><head><title>Loading EchoStack...</title></head><body>
<script>
localStorage.setItem('es_user', JSON.stringify({{
    loggedIn: true, user_id: "{user_id}", username: "{username}",
    role: "superuser", is_premium: 1
}}));
document.cookie = "user_session={user_id}; path=/; max-age=604800";
window.location.href = '/app';
</script><p>Redirecting...</p></body></html>"""
    resp = HTMLResponse(content=html)
    resp.set_cookie(key="user_session", value=user_id, max_age=3600, path="/")
    return resp

@app.get("/test")
def test_endpoint(): return {"status": "ok", "backend": "working"}

@app.get("/echostack-logo.png")
def serve_logo(): return serve_file("echostack-logo.png")

@app.get("/sw.js")
def serve_sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript",
                            headers={"Service-Worker-Allowed": "/"})
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404)

@app.get("/map")
async def map_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return RedirectResponse(url="/app")

@app.get("/archive")
async def archive_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("archive.html") if os.path.exists("archive.html") else RedirectResponse(url="/explore")

@app.get("/subscriptions")
async def subscriptions_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("subscriptions.html") if os.path.exists("subscriptions.html") else RedirectResponse(url="/app")

@app.get("/subscribers")
async def subscribers_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("subscribers.html") if os.path.exists("subscribers.html") else RedirectResponse(url="/following")

@app.get("/user-settings")
async def user_settings_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    if os.path.exists("user_settings.html"):
        return serve_file("user_settings.html")
    html = """<!DOCTYPE html><html><head><title>Settings — EchoStack</title>
<style>body{font-family:sans-serif;padding:40px;background:#f9fafb;max-width:600px;margin:0 auto;}
h1{color:#0D1B2A;}a.btn{display:inline-block;padding:10px 20px;background:#C8962E;color:white;
border-radius:8px;margin-top:20px;text-decoration:none;}</style></head>
<body><h1>⚙️ User Settings</h1>
<p style="color:#666;margin-top:12px;">Settings page coming soon.</p>
<a class="btn" href="/user-profile">Go to My Profile</a>
<a class="btn" style="background:#0077b6;margin-left:10px;" href="/app">Back to Home</a>
</body></html>"""
    return HTMLResponse(content=html)

@app.get("/chat")
async def chat_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("community_chat.html")

@app.get("/activity")
async def activity_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("activity.html")

@app.get("/explore")
async def explore_page(request: Request):
    return serve_file("explore.html")

@app.get("/following")
async def following_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("following.html")

@app.get("/user-profile")
async def user_profile_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("user_profile.html")

@app.get("/premium")
async def premium_page(request: Request):
    return serve_file("premium.html")

# ============================================
# ADMIN AUTH
# ============================================
@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    cleaned = ADMIN_SECRET.lower().replace(" ", "")
    given = answer.strip().lower().replace(" ", "")
    if cleaned == given:
        resp = JSONResponse(content={"success": True})
        resp.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED",
                        max_age=86400, path="/", httponly=False)
        return resp
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout():
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(key="admin_session", path="/")
    return resp

# ============================================
# USER AUTH
# ============================================
@app.post("/api/users/signup")
async def user_signup(
    username: str = Form(...), email: str = Form(...),
    password: str = Form(...), interests: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        username = username.strip()
        email = email.lower().strip()
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        new_user = models.User(
            username=username, email=email,
            password_hash=hash_password(password),
            interests=interests or "", role="user", is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        resp = JSONResponse(content={
            "success": True, "user_id": str(new_user.id),
            "username": new_user.username, "email": new_user.email,
            "role": new_user.role, "is_premium": bool(new_user.is_premium)
        })
        resp.set_cookie(key="user_session", value=str(new_user.id), max_age=86400*7, path="/")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/login")
async def user_login(
    username: str = Form(...), password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        login_val = username.lower().strip()
        user = db.query(models.User).filter(
            (models.User.email == login_val) | (models.User.username == login_val)
        ).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        resp = JSONResponse(content={
            "success": True, "user_id": str(user.id),
            "username": user.username, "email": user.email,
            "role": user.role or "user", "is_premium": bool(user.is_premium)
        })
        resp.set_cookie(key="user_session", value=str(user.id), max_age=86400*7, path="/")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/logout")
def user_logout():
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(key="user_session", path="/")
    return resp

@app.get("/api/users/me")
async def get_current_user_api(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {
        "id": str(user.id), "username": user.username, "email": user.email,
        "full_name": user.full_name or "", "bio": user.bio or "",
        "interests": user.interests or "", "avatar_url": user.avatar_url or "",
        "role": user.role or "user", "is_premium": bool(user.is_premium),
        "created_at": str(user.created_at)
    }

@app.put("/api/users/me")
async def update_current_user(
    request: Request,
    full_name: str = Form(None), bio: str = Form(None),
    interests: str = Form(None), avatar_url: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    if full_name is not None: user.full_name = full_name.strip()
    if bio is not None: user.bio = bio.strip()
    if interests is not None: user.interests = interests.strip()
    if avatar_url is not None: user.avatar_url = avatar_url.strip()
    db.commit()
    return {"success": True}

# ============================================
# ADMIN USER MANAGEMENT
# ============================================
@app.get("/api/admin/users")
def get_all_users(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    try:
        users = db.query(models.User).order_by(models.User.created_at.desc()).all()
        return [{
            "id": str(u.id), "username": u.username, "email": u.email,
            "role": u.role or "user", "is_premium": bool(u.is_premium),
            "plan": "premium" if u.is_premium else "free",
            "is_active": bool(u.is_active) if u.is_active is not None else True,
            "created_at": str(u.created_at) if u.created_at else ""
        } for u in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/users/{user_id}/role")
def set_user_role(user_id: str, request: Request, role: str = Form(...), db: Session = Depends(get_db)):
    require_admin(request)
    try:
        user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
    except:
        raise HTTPException(status_code=404, detail="User not found")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ["user", "creator", "admin", "superuser"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = role
    db.commit()
    return {"success": True, "role": role}

@app.put("/api/admin/users/{user_id}/premium")
def toggle_premium(user_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    try:
        user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
    except:
        raise HTTPException(status_code=404, detail="User not found")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_premium = not bool(user.is_premium)
    db.commit()
    return {"success": True, "is_premium": user.is_premium}

@app.put("/api/admin/users/{user_id}/suspend")
def toggle_suspend(user_id: str, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    try:
        user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
    except:
        raise HTTPException(status_code=404, detail="User not found")
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not bool(user.is_active)
    db.commit()
    return {"success": True, "is_active": user.is_active}

# ============================================
# REGIONS
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        regions = db.query(models.Region).all()
        return [{
            "id": int(r.id), "name": str(r.name) if r.name else "",
            "capital": str(r.capital) if r.capital else "",
            "population": str(r.population) if r.population else "",
            "terrain": str(r.terrain) if r.terrain else "",
            "description": str(r.description) if r.description else "",
            "overview": str(r.overview) if r.overview else "",
            "category": str(r.category) if r.category else "",
            "tags": str(r.tags) if r.tags else "",
            "hero_image": str(r.hero_image) if r.hero_image else "",
            "gallery_images": str(r.gallery_images) if r.gallery_images else "",
            "audio_files": str(r.audio_files) if r.audio_files else "",
            "video_files": str(r.video_files) if r.video_files else "",
            "documents": str(r.documents) if r.documents else "",
            "source": str(r.source) if r.source else ""
        } for r in regions]
    except Exception as e:
        print(f"Error getting regions: {e}")
        return []

@app.get("/api/regions/{region_id}")
def get_region(region_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Region not found")
    return {
        "id": r.id, "name": r.name, "capital": r.capital or "",
        "description": r.description or "", "overview": r.overview or "",
        "hero_image": r.hero_image or "", "gallery_images": r.gallery_images or "",
        "audio_files": r.audio_files or "", "video_files": r.video_files or "",
        "documents": r.documents or "", "tags": r.tags or ""
    }

@app.post("/api/regions")
async def create_region(
    name: str = Form(...), capital: str = Form(""), population: str = Form(""),
    terrain: str = Form(""), description: str = Form(""), category: str = Form(""),
    tags: str = Form(""), hero_image: str = Form(""), gallery_images: str = Form(""),
    audio_files: str = Form(""), video_files: str = Form(""), documents: str = Form(""),
    source: str = Form(""), overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")
        r = models.Region(
            name=name.strip(), capital=capital.strip(), population=population.strip(),
            terrain=terrain.strip(), description=description.strip(),
            overview=overview.strip() or description.strip(), category=category.strip(),
            tags=tags.strip(), hero_image=hero_image.strip(),
            gallery_images=gallery_images.strip(), audio_files=audio_files.strip(),
            video_files=video_files.strip(), documents=documents.strip(),
            source=source.strip()
        )
        db.add(r)
        db.commit()
        db.refresh(r)
        return {"success": True, "region_id": r.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/regions/{region_id}")
async def update_region(
    region_id: int, name: str = Form(None), capital: str = Form(None),
    population: str = Form(None), terrain: str = Form(None), description: str = Form(None),
    category: str = Form(None), tags: str = Form(None), hero_image: str = Form(None),
    gallery_images: str = Form(None), audio_files: str = Form(None),
    video_files: str = Form(None), documents: str = Form(None),
    source: str = Form(None), overview: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        r = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Region not found")
        if name is not None and name.strip(): r.name = name.strip()
        if capital is not None: r.capital = capital.strip()
        if population is not None: r.population = population.strip()
        if terrain is not None: r.terrain = terrain.strip()
        if description is not None: r.description = description.strip()
        if overview is not None and overview.strip(): r.overview = overview.strip()
        if category is not None: r.category = category.strip()
        if tags is not None: r.tags = tags.strip()
        if hero_image is not None: r.hero_image = hero_image.strip()
        if gallery_images is not None: r.gallery_images = gallery_images.strip()
        if audio_files is not None: r.audio_files = audio_files.strip()
        if video_files is not None: r.video_files = video_files.strip()
        if documents is not None: r.documents = documents.strip()
        if source is not None: r.source = source.strip()
        db.commit()
        db.refresh(r)
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    try:
        r = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Region not found")
        db.delete(r)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FILE UPLOADS — 50MB limit
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(...),
    category: str = Form("general"), description: str = Form(""),
    region_id: str = Form(""), is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        content = await file.read()
        MAX_SIZE = 50 * 1024 * 1024
        if len(content) > MAX_SIZE:
            raise HTTPException(status_code=413, detail="File too large. Maximum 50MB.")
        safe_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename.replace(' ', '_')}"
        file_path = UPLOAD_DIR / safe_name
        with open(file_path, "wb") as f:
            f.write(content)
        uf = models.UploadedFile(
            filename=safe_name, original_name=filename, file_path=str(file_path),
            file_size=len(content), mime_type=file.content_type or "application/octet-stream",
            category=category,
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            description=description, uploaded_by="admin",
            is_public=int(is_public) if is_public else 1
        )
        db.add(uf)
        db.commit()
        db.refresh(uf)
        return {
            "success": True, "file_id": uf.id,
            "url": f"/uploads/{safe_name}", "filename": safe_name,
            "original_name": filename, "category": category,
            "size_bytes": len(content),
            "file_size_mb": round(len(content) / (1024*1024), 2),
            "mime_type": file.content_type
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/multiple")
async def upload_multiple_files(
    request: Request, category: str = Form("general"),
    description: str = Form(""), region_id: str = Form(""),
    is_public: str = Form("1"), db: Session = Depends(get_db)
):
    form = await request.form()
    files = form.getlist("files")
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    MAX_SIZE = 50 * 1024 * 1024
    results = []
    for file in files:
        try:
            content = await file.read()
            if len(content) > MAX_SIZE:
                results.append({"success": False, "filename": file.filename, "error": "Exceeds 50MB"})
                continue
            safe_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename.replace(' ', '_')}"
            file_path = UPLOAD_DIR / safe_name
            with open(file_path, "wb") as f:
                f.write(content)
            uf = models.UploadedFile(
                filename=safe_name, original_name=file.filename, file_path=str(file_path),
                file_size=len(content), mime_type=file.content_type or "application/octet-stream",
                category=category,
                region_id=int(region_id) if region_id and region_id.isdigit() else None,
                description=description, uploaded_by="admin", is_public=int(is_public) if is_public else 1
            )
            db.add(uf)
            db.commit()
            db.refresh(uf)
            results.append({
                "success": True, "file_id": uf.id, "url": f"/uploads/{safe_name}",
                "filename": safe_name, "original_name": file.filename,
                "file_size_mb": round(len(content) / (1024*1024), 2),
                "mime_type": file.content_type
            })
        except Exception as e:
            results.append({"success": False, "filename": getattr(file, "filename", "unknown"), "error": str(e)})
    return {"success": True, "uploaded": sum(1 for r in results if r.get("success")),
            "total": len(files), "results": results}

@app.get("/api/files")
def get_files(category: str = "", region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category: q = q.filter(models.UploadedFile.category == category)
        if region_id: q = q.filter(models.UploadedFile.region_id == int(region_id))
        return [{
            "id": f.id, "filename": f.filename, "original_name": f.original_name,
            "file_url": f"/uploads/{f.filename}",
            "file_size": f.file_size,
            "file_size_mb": round((f.file_size or 0) / (1024*1024), 2),
            "mime_type": f.mime_type, "category": f.category,
            "region_id": f.region_id, "description": f.description,
            "created_at": str(f.created_at)
        } for f in q.order_by(models.UploadedFile.created_at.desc()).all()]
    except Exception as e:
        print(f"Error getting files: {e}")
        return []

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    try:
        f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="File not found")
        if f.file_path and os.path.exists(f.file_path):
            os.remove(f.file_path)
        db.delete(f)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# POSTS
# ============================================
@app.get("/api/posts")
def get_posts(
    status: str = "published", content_type: str = "", limit: int = 50,
    author_id: str = "", is_premium: int = -1, db: Session = Depends(get_db)
):
    try:
        q = db.query(models.Post)
        if status and status != "all":
            q = q.filter(models.Post.status == status)
        if content_type:
            q = q.filter(models.Post.content_type == content_type)
        if author_id:
            try:
                q = q.filter(models.Post.author_id == uuid.UUID(author_id))
            except:
                pass
        if is_premium >= 0:
            q = q.filter(models.Post.is_premium == bool(is_premium))
        posts = q.order_by(models.Post.created_at.desc()).limit(limit).all()
        return [{
            "id": p.id, "title": p.title, "excerpt": p.excerpt or "",
            "cover_image": p.cover_image or "", "content_type": p.content_type or "article",
            "author_username": p.author_username or "",
            "author_id": str(p.author_id) if p.author_id else "",
            "status": p.status, "views": p.views or 0, "likes": p.likes or 0,
            "is_premium": bool(p.is_premium), "region_id": p.region_id,
            "created_at": str(p.created_at)
        } for p in posts]
    except Exception as e:
        print(f"Error getting posts: {e}")
        return []

@app.get("/api/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Post not found")
    p.views = (p.views or 0) + 1
    db.commit()
    return {
        "id": p.id, "title": p.title, "excerpt": p.excerpt or "",
        "content": p.content or "", "cover_image": p.cover_image or "",
        "content_type": p.content_type or "article", "audio_url": p.audio_url or "",
        "video_url": p.video_url or "", "gallery": p.gallery or "",
        "author_username": p.author_username or "",
        "author_id": str(p.author_id) if p.author_id else "",
        "status": p.status, "views": p.views or 0, "likes": p.likes or 0,
        "is_premium": bool(p.is_premium), "created_at": str(p.created_at)
    }

@app.post("/api/posts")
async def create_post(
    title: str = Form(...), excerpt: str = Form(""), content: str = Form(""),
    cover_image: str = Form(""), content_type: str = Form("article"),
    region_id: str = Form(""), status: str = Form("draft"), is_premium: str = Form("0"),
    request: Request = None, db: Session = Depends(get_db)
):
    is_admin_session = request and request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
    user = get_user_from_request(request, db)

    if is_admin_session and not user:
        user = db.query(models.User).filter(models.User.role.in_(["admin","superuser"])).first()
        if not user:
            try:
                user = models.User(
                    username="admin", email="admin@echostack.gh",
                    password_hash=hash_password("admin_temp_password"),
                    role="admin", is_active=True, is_premium=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            except:
                db.rollback()

    if not user and not is_admin_session:
        raise HTTPException(status_code=401, detail="Must be logged in")
    if user and user.role not in ["creator","superuser","admin"] and not is_admin_session:
        raise HTTPException(status_code=403, detail="Creator account required")

    author_id = user.id if user else None
    author_name = user.username if user else "Admin"

    try:
        post = models.Post(
            author_id=author_id, author_username=author_name,
            title=title.strip(), excerpt=excerpt.strip(), content=content.strip(),
            cover_image=cover_image.strip(), content_type=content_type,
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            status=status, is_premium=bool(int(is_premium))
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return {"success": True, "post_id": post.id, "status": post.status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int, status: str = Form(None), title: str = Form(None),
    request: Request = None, db: Session = Depends(get_db)
):
    require_admin(request)
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if status is not None: post.status = status
    if title is not None: post.title = title.strip()
    db.commit()
    return {"success": True}

@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    """Toggle like on a post. Returns updated like count + liked state."""
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to like")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    # Check if already liked (simple: use Comment table pattern with a Like tracker)
    # We store likes as a simple count — toggle by checking session
    # Use a lightweight approach: store liked post IDs in a pseudo-table via Comment with type='like'
    existing = db.query(models.Comment).filter(
        models.Comment.post_id == post_id,
        models.Comment.author_id == user.id,
        models.Comment.content == "__like__"
    ).first()
    if existing:
        db.delete(existing)
        post.likes = max(0, (post.likes or 0) - 1)
        db.commit()
        return {"success": True, "liked": False, "likes": post.likes}
    else:
        like_marker = models.Comment(
            post_id=post_id, author_id=user.id,
            author_username=user.username, content="__like__", is_approved=0
        )
        db.add(like_marker)
        post.likes = (post.likes or 0) + 1
        db.commit()
        return {"success": True, "liked": True, "likes": post.likes}

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"success": True}

# ============================================
# ADMIN PUBLISH FILE TO FEED
# ============================================
@app.post("/api/admin/publish-file")
async def admin_publish_file(
    request: Request, file_id: str = Form(...), title: str = Form(...),
    excerpt: str = Form(""), status: str = Form("published"),
    is_premium: str = Form("0"), db: Session = Depends(get_db)
):
    require_admin(request)
    try:
        file_record = db.query(models.UploadedFile).filter(
            models.UploadedFile.id == int(file_id)
        ).first()
        if not file_record:
            raise HTTPException(status_code=404, detail="File not found")

        mime = file_record.mime_type or ""
        if mime.startswith("video/"): content_type = "video"
        elif mime.startswith("audio/"): content_type = "audio"
        elif mime.startswith("image/"): content_type = "photo_essay"
        else: content_type = "article"

        file_url = f"/uploads/{file_record.filename}"
        if content_type == "video": content = f"[video]{file_url}[/video]"
        elif content_type == "audio": content = f"[audio]{file_url}[/audio]"
        elif content_type == "photo_essay": content = f"![{title}]({file_url})"
        else: content = f"[{file_record.original_name}]({file_url})"

        cover_image = file_url if content_type == "photo_essay" else ""

        admin_user = db.query(models.User).filter(
            models.User.role.in_(["admin","superuser"])
        ).first()
        author_id = admin_user.id if admin_user else None
        author_name = admin_user.username if admin_user else "Admin"

        post = models.Post(
            author_id=author_id, author_username=author_name,
            title=title.strip(), excerpt=excerpt.strip(), content=content,
            cover_image=cover_image, content_type=content_type,
            status=status, is_premium=bool(int(is_premium))
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        return {"success": True, "post_id": post.id, "status": post.status,
                "content_type": content_type, "file_url": file_url}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# STATS
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        return {
            "total_regions": db.query(models.Region).count(),
            "total_users": db.query(models.User).count(),
            "total_posts": db.query(models.Post).filter(models.Post.status == "published").count(),
            "total_creators": db.query(models.User).filter(models.User.role == "creator").count(),
            "total_comments": db.query(models.Comment).count(),
            "with_audio": db.query(models.UploadedFile).filter(models.UploadedFile.category == "audio").count(),
            "with_images": db.query(models.UploadedFile).filter(models.UploadedFile.category == "image").count(),
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {"total_regions": 0, "total_users": 0, "total_posts": 0,
                "total_creators": 0, "total_comments": 0, "with_audio": 0, "with_images": 0}

# ============================================
# STORIES
# ============================================
@app.get("/api/stories")
def get_stories(status: str = "pending", db: Session = Depends(get_db)):
    try:
        stories = db.query(models.StorySubmission).filter(
            models.StorySubmission.status == status
        ).order_by(models.StorySubmission.created_at.desc()).all()
        return [{
            "id": s.id, "title": s.title, "content": s.content or "",
            "username": s.username or "", "author": s.username or "",
            "region_id": s.region_id, "status": s.status,
            "created_at": str(s.created_at) if s.created_at else ""
        } for s in stories]
    except Exception as e:
        print(f"Stories error: {e}")
        return []

@app.post("/api/stories")
async def submit_story(
    title: str = Form(...), content: str = Form(...), region_id: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    is_admin_session = request and request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
    user = get_user_from_request(request, db)
    if not user and not is_admin_session:
        raise HTTPException(status_code=401, detail="Must be logged in to submit a story")
    author_name = user.username if user else "Admin"
    author_id = user.id if user else None
    auto_status = "approved" if is_admin_session else "pending"
    try:
        story = models.StorySubmission(
            title=title.strip(), content=content.strip(), username=author_name,
            user_id=str(author_id) if author_id else None,
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            status=auto_status
        )
        db.add(story)
        db.commit()
        db.refresh(story)
        return {"success": True, "story_id": story.id, "status": auto_status}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/stories/{story_id}/approve")
def approve_story(story_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    story = db.query(models.StorySubmission).filter(models.StorySubmission.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.status = "approved"
    db.commit()
    return {"success": True}

@app.put("/api/stories/{story_id}/reject")
def reject_story(story_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    story = db.query(models.StorySubmission).filter(models.StorySubmission.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.status = "rejected"
    db.commit()
    return {"success": True}

# ============================================
# NEWSLETTER
# ============================================
@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(
    email: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)
):
    try:
        existing = db.query(models.NewsletterSubscriber).filter(
            models.NewsletterSubscriber.email == email.lower()
        ).first()
        if existing:
            return {"success": True, "message": "Already subscribed!"}
        sub = models.NewsletterSubscriber(email=email.lower(), full_name=full_name)
        db.add(sub)
        db.commit()
        return {"success": True, "message": "Subscribed successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/newsletter/subscribers")
def get_newsletter_subscribers(request: Request, db: Session = Depends(get_db)):
    try:
        total_count = db.query(models.NewsletterSubscriber).count()
        is_admin = request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
        user = get_user_from_request(request, db)
        if is_admin or (user and user.role in ["admin","superuser"]):
            subs = db.query(models.NewsletterSubscriber).order_by(
                models.NewsletterSubscriber.subscribed_at.desc()
            ).all()
            return [{
                "id": s.id, "email": s.email, "full_name": s.full_name or "",
                "subscribed_at": str(s.subscribed_at) if s.subscribed_at else "",
                "created_at": str(s.subscribed_at) if s.subscribed_at else ""
            } for s in subs]
        return {"count": total_count}
    except Exception as e:
        print(f"Newsletter error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# EVENTS
# ============================================
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    try:
        events = db.query(models.Event).filter(models.Event.is_active == True).all()
        return [{"id": e.id, "title": e.title, "description": e.description or "",
                 "event_date": e.event_date or "", "location": e.location or "",
                 "image_url": e.image_url or ""} for e in events]
    except Exception as e:
        print(f"Events error: {e}")
        return []

@app.post("/api/events")
async def create_event(
    title: str = Form(...), description: str = Form(""), event_date: str = Form(""),
    location: str = Form(""), image_url: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    require_admin(request)
    try:
        event = models.Event(title=title, description=description, event_date=event_date,
                             location=location, image_url=image_url, is_active=True)
        db.add(event)
        db.commit()
        db.refresh(event)
        return {"success": True, "event_id": event.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)
    event.is_active = False
    db.commit()
    return {"success": True}

# ============================================
# CHAT
# ============================================
@app.get("/api/chat")
def get_messages(region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.is_approved == 1)
        if region_id:
            q = q.filter(models.ChatMessage.region_id == int(region_id))
        msgs = q.order_by(models.ChatMessage.created_at.desc()).limit(50).all()
        return [{"id": m.id, "username": m.username, "message": m.message,
                 "region_id": m.region_id, "created_at": str(m.created_at)} for m in msgs]
    except Exception as e:
        print(f"Chat error: {e}")
        return []

@app.post("/api/chat")
async def post_message(
    message: str = Form(...), region_id: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to chat")
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    msg = models.ChatMessage(
        user_id=user.id, username=user.username, message=message.strip()[:500],
        region_id=int(region_id) if region_id and region_id.isdigit() else None
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"success": True, "id": msg.id, "username": msg.username, "message": msg.message}

@app.delete("/api/chat/{message_id}")
async def delete_chat_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    msg = db.query(models.ChatMessage).filter(models.ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
    return {"success": True}

# ============================================
# SECTIONS
# ============================================
@app.get("/api/sections")
def get_sections(active_only: int = 1, db: Session = Depends(get_db)):
    try:
        q = db.query(models.Section)
        if active_only:
            q = q.filter(models.Section.is_active == 1).order_by(models.Section.display_order)
        return [{"id": s.id, "name": s.name, "slug": s.slug, "description": s.description}
                for s in q.all()]
    except Exception as e:
        print(f"Sections error: {e}")
        return []

@app.post("/api/sections")
def create_section(
    name: str = Form(...), description: str = Form(""),
    display_order: int = Form(0), db: Session = Depends(get_db)
):
    try:
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if db.query(models.Section).filter(models.Section.slug == slug).first():
            raise HTTPException(status_code=400, detail="Already exists")
        s = models.Section(name=name, slug=slug, description=description, display_order=display_order)
        db.add(s)
        db.commit()
        db.refresh(s)
        return {"success": True, "section_id": s.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    try:
        s = db.query(models.Section).filter(models.Section.id == section_id).first()
        if not s:
            raise HTTPException(status_code=404)
        s.is_active = False
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FOLLOW / SOCIAL
# ============================================
@app.post("/api/follow/{user_id}")
async def follow_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        target_id = uuid.UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    if user.id == target_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    try:
        existing = db.query(models.Follow).filter(
            models.Follow.follower_id == user.id,
            models.Follow.following_id == target_id
        ).first()
        if existing:
            db.delete(existing)
            db.commit()
            return {"success": True, "action": "unfollowed"}
        db.add(models.Follow(follower_id=user.id, following_id=target_id))
        db.commit()
        return {"success": True, "action": "followed"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/following")
async def get_following(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        follows = db.query(models.Follow).filter(models.Follow.follower_id == user.id).all()
        result = []
        for f in follows:
            followed = db.query(models.User).filter(models.User.id == f.following_id).first()
            if followed:
                post_count = db.query(models.Post).filter(
                    models.Post.author_id == followed.id, models.Post.status == "published"
                ).count()
                result.append({
                    "id": str(followed.id), "username": followed.username,
                    "full_name": followed.full_name or "", "role": followed.role,
                    "avatar_url": followed.avatar_url or "", "post_count": post_count
                })
        return result
    except Exception as e:
        print(f"Following error: {e}")
        return []

@app.get("/api/subscribers")
async def get_subscribers(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        follows = db.query(models.Follow).filter(models.Follow.following_id == user.id).all()
        return [{
            "id": str(f2.id), "username": f2.username,
            "full_name": f2.full_name or "", "role": f2.role,
            "avatar_url": f2.avatar_url or ""
        } for f in follows
          for f2 in [db.query(models.User).filter(models.User.id == f.follower_id).first()]
          if f2]
    except Exception as e:
        return []

@app.get("/api/activity")
async def get_activity(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Login required")
    try:
        follow_ids = [f.following_id for f in db.query(models.Follow).filter(
            models.Follow.follower_id == user.id).all()]
        posts = db.query(models.Post).filter(
            models.Post.author_id.in_(follow_ids),
            models.Post.status == "published"
        ).order_by(models.Post.created_at.desc()).limit(30).all()
        return [{"id": p.id, "title": p.title, "author_username": p.author_username or "",
                 "content_type": p.content_type, "created_at": str(p.created_at),
                 "cover_image": p.cover_image or "", "is_premium": bool(p.is_premium)} for p in posts]
    except Exception as e:
        return []

# ============================================
# CREATORS
# ============================================
@app.get("/api/creators")
def get_creators(db: Session = Depends(get_db)):
    try:
        channels = db.query(models.CreatorChannel).filter(
            models.CreatorChannel.is_active == 1
        ).all()
        result = []
        for c in channels:
            user = db.query(models.User).filter(models.User.id == c.user_id).first()
            post_count = db.query(models.Post).filter(
                models.Post.author_id == c.user_id, models.Post.status == "published"
            ).count()
            result.append({
                "id": c.id,
                "username": user.username if user else "unknown",
                "channel_name": c.channel_name or (user.username if user else ""),
                "follower_count": 0, "post_count": post_count,
                "role": user.role if user else "creator"
            })
        return result
    except Exception as e:
        print(f"Creators error: {e}")
        return []

# ============================================
# COMMENTS
# ============================================
@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    try:
        comments = db.query(models.Comment).filter(
            models.Comment.post_id == post_id,
            models.Comment.is_approved == 1,
            models.Comment.content != "__like__"
        ).order_by(models.Comment.created_at.asc()).all()
        return [{"id": c.id, "content": c.content, "author_username": c.author_username or "",
                 "created_at": str(c.created_at)} for c in comments]
    except Exception as e:
        return []

@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int, content: str = Form(...),
    request: Request = None, db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in")
    if not content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    comment = models.Comment(
        post_id=post_id, author_id=user.id,
        author_username=user.username, content=content.strip()
    )
    db.add(comment)
    # Increment comment count
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if post:
        post.comment_count = (post.comment_count or 0) + 1
    db.commit()
    db.refresh(comment)
    return {"success": True, "comment_id": comment.id}

# ============================================
# THEME & CONFIG
# ============================================
@app.get("/api/theme")
def get_theme():
    try:
        if os.path.exists("theme.json"):
            with open("theme.json", "r") as f:
                return json.load(f)
        return {}
    except:
        return {}

@app.post("/api/theme")
async def save_theme(request: Request):
    try:
        body = await request.json()
        with open("theme.json", "w") as f:
            json.dump(body, f)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/site-config")
async def get_site_config(request: Request):
    require_admin(request)
    try:
        if os.path.exists("site_config.json"):
            with open("site_config.json", "r") as f:
                return json.load(f)
        return {}
    except:
        return {}

@app.post("/api/site-config")
async def save_site_config(request: Request):
    require_admin(request)
    try:
        config = await request.json()
        with open("site_config.json", "w") as f:
            json.dump(config, f, indent=2)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# JSON IMPORT
# ============================================
@app.post("/api/import/json")
def import_json(data: list, db: Session = Depends(get_db)):
    try:
        imported = 0
        for rd in data:
            try:
                db.add(models.Region(**rd))
                imported += 1
            except:
                continue
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# AI CHAT (EchoBot)
# ============================================
@app.post("/api/ai/chat")
async def ai_chat(
    message: str = Form(...), region_context: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    try:
        user = get_user_from_request(request, db)
        is_admin_session = request and request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
        is_premium = (user and (bool(user.is_premium) or user.role in ["superuser","admin","creator"])) or is_admin_session

        if not user and not is_admin_session:
            return {"reply": "Please log in to use EchoBot!", "success": False, "locked": True}
        if not is_premium:
            return {"reply": "🔒 EchoBot is a Premium feature. Subscribe for GH₵150/month!",
                    "success": False, "locked": True, "upgrade_url": "/premium"}
        if not HF_TOKEN:
            return {"reply": "EchoBot is currently unavailable. Please configure HF_TOKEN.",
                    "success": False, "locked": False}

        db_knowledge = get_db_knowledge(db)
        system_prompt = f"""You are EchoBot, an AI guide for EchoStack Ghana Heritage Archive.
ONLY answer using the Ghana region data below. If not in data, say you don't have that info yet.

GHANA HERITAGE DATABASE:
{db_knowledge}

RULES:
- Answer ONLY based on the database above
- Keep answers short (2-4 sentences)
- If info not in database: "I don't have that information yet in our archive."
- Be warm and educational"""
        if region_context:
            system_prompt += f"\n\nUser is viewing: {region_context} region."

        full_prompt = f"{system_prompt}\n\nQuestion: {message}\n\nAnswer:"
        payload = json.dumps({
            "inputs": full_prompt,
            "parameters": {"max_new_tokens": 150, "temperature": 0.3,
                           "do_sample": False, "return_full_text": False}
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api-inference.huggingface.co/models/google/flan-t5-small",
            data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {HF_TOKEN}"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
                if isinstance(result, list) and result:
                    reply = result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    reply = result.get("generated_text", "Try again!").strip()
                else:
                    reply = "I'm thinking... please try again!"
                reply = reply.replace("[INST]", "").replace("[/INST]", "").replace("</s>", "").strip()
                if not reply:
                    reply = "I don't have that information in our Ghana heritage archive yet."
                return {"reply": reply, "success": True, "locked": False}
        except urllib.error.HTTPError as e:
            if e.code == 503:
                return {"reply": "EchoBot is warming up! Try again in 15 seconds.",
                        "success": False, "warming": True, "locked": False}
            return {"reply": "I'm having a moment — please try again!", "success": False, "locked": False}
    except Exception as e:
        print(f"AI chat error: {e}")
        return {"reply": "Something went wrong. Please try again!", "success": False, "locked": False}

# ============================================
# PAYSTACK PAYMENTS
# ============================================
@app.post("/api/payments/initialize")
async def initialize_payment(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")
    if not PAYSTACK_SECRET:
        raise HTTPException(status_code=500, detail="Paystack not configured.")
    payload = json.dumps({
        "email": user.email, "amount": 15000, "currency": "GHS",
        "callback_url": "https://echostack.onrender.com/payment/callback",
        "metadata": {"user_id": str(user.id), "plan": "premium"}
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.paystack.co/transaction/initialize", data=payload,
        headers={"Authorization": f"Bearer {PAYSTACK_SECRET}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Paystack error: {str(e)}")
    if not result.get("status"):
        raise HTTPException(status_code=400, detail="Payment initialization failed")
    ref = result["data"]["reference"]
    db.add(models.Payment(user_id=user.id, email=user.email, amount=15000,
                          reference=ref, status="pending", plan="premium"))
    db.commit()
    return {"success": True, "authorization_url": result["data"]["authorization_url"], "reference": ref}

@app.get("/payment/callback")
async def payment_callback(reference: str, request: Request, db: Session = Depends(get_db)):
    if not PAYSTACK_SECRET:
        return RedirectResponse("/dashboard?payment=error")
    req = urllib.request.Request(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"}, method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except:
        return RedirectResponse("/dashboard?payment=error")
    if result.get("status") and result["data"].get("status") == "success":
        user_id = result["data"].get("metadata", {}).get("user_id")
        if user_id:
            try:
                user = db.query(models.User).filter(models.User.id == uuid.UUID(user_id)).first()
                if user:
                    user.is_premium = True
                    payment = db.query(models.Payment).filter(
                        models.Payment.reference == reference).first()
                    if payment:
                        payment.status = "success"
                    db.commit()
            except:
                pass
        return RedirectResponse("/dashboard?upgraded=1")
    return RedirectResponse("/dashboard?payment=failed")

# ============================================
# PORT CONFIG FOR RENDER
# ============================================
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
