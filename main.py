# main.py — FINAL STABLE VERSION FOR ECHOSTACK GHANA
from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os, json, re, hashlib, datetime, hmac, urllib.request, uuid
from pathlib import Path
from typing import Optional, List
from database import engine, get_db, Base
import models

# ───────────────────────────────────────────────
# DATABASE SETUP
# ───────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API", docs_url=None, redoc_url=None)

# ───────────────────────────────────────────────
# CONFIG
# ───────────────────────────────────────────────
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
except Exception as e:
    print(f"[WARN] Failed to mount uploads: {e}")

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "THE ADMIN")
PAYSTACK_SECRET = os.getenv("PAYSTACK_SECRET_KEY", "")
HF_TOKEN = os.getenv("HF_TOKEN", "")

# ───────────────────────────────────────────────
# HELPERS
# ───────────────────────────────────────────────
def hash_password(p: str) -> str:
    return hashlib.sha256(p.encode()).hexdigest()

def verify_password(p: str, h: str) -> bool:
    return hash_password(p) == h

def get_user_from_request(request: Request, db: Session) -> Optional[models.User]:
    user_id = request.cookies.get("user_session")
    if not user_id:
        return None
    try:
        # Try UUID first (modern)
        uid = uuid.UUID(str(user_id))
        return db.query(models.User).filter(models.User.id == uid).first()
    except (ValueError, AttributeError):
        # Fallback to int (legacy)
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

# ───────────────────────────────────────────────
# STATIC PAGES
# ───────────────────────────────────────────────
def serve_file(filename: str):
    full_path = Path(filename)
    if full_path.exists():
        return FileResponse(full_path)
    raise HTTPException(status_code=404, detail=f"{filename} not found")

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
    
    # Ensure at least one superuser exists
    admin_user = db.query(models.User).filter(
        models.User.role.in_(["superuser", "admin"])
    ).first()
    if not admin_user:
        admin_user = models.User(
            username="admin",
            email="admin@echostack.gh",
            password_hash=hash_password("admin_temp"),
            role="superuser",
            is_active=True,
            is_premium=True
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    
    # Return HTML that sets localStorage + redirects
    html = f"""<!DOCTYPE html>
<html><head><title>Loading...</title></head><body>
<script>
localStorage.setItem('es_user', JSON.stringify({{
    loggedIn: true,
    user_id: "{admin_user.id}",
    username: "{admin_user.username}",
    email: "admin@echostack.gh",
    role: "{admin_user.role}",
    plan: "premium",
    is_premium: 1
}});
window.location.href = '/app';
</script>
</body></html>"""
    resp = HTMLResponse(content=html)
    resp.set_cookie(key="user_session", value=str(admin_user.id), max_age=3600, path="/")
    return resp

# ───────────────────────────────────────────────
# AUTH
# ───────────────────────────────────────────────
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

@app.post("/api/users/signup")
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    interests: str = Form(""),
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
            username=username,
            email=email,
            password_hash=hash_password(password),
            interests=interests or "",
            role="user",
            is_active=True
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        resp = JSONResponse(content={
            "success": True,
            "user_id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "is_premium": new_user.is_premium or False
        })
        resp.set_cookie(key="user_session", value=str(new_user.id),
                       max_age=86400 * 7, path="/")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Signup failed: {e}")
        raise HTTPException(status_code=500, detail="Server error")

@app.post("/api/users/login")
async def user_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        login_val = username.lower().strip()
        user = db.query(models.User).filter(
            (models.User.email == login_val) | (models.User.username == login_val)
        ).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        
        resp = JSONResponse(content={
            "success": True,
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role or "user",
            "is_premium": user.is_premium or False
        })
        resp.set_cookie(key="user_session", value=str(user.id),
                       max_age=86400 * 7, path="/")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        raise HTTPException(status_code=500, detail="Server error")

# ───────────────────────────────────────────────
# POSTS — CORE FIX
# ───────────────────────────────────────────────
@app.post("/api/posts")
async def create_post(
    title: str = Form(...),
    excerpt: str = Form(""),
    content: str = Form(""),
    cover_image: str = Form(""),
    content_type: str = Form("article"),
    region_id: str = Form(""),
    status: str = Form("draft"),
    is_premium: str Form("0"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    try:
        user = get_user_from_request(request, db)
        if not user:
            # If no user, check for admin session
            if request.cookies.get("admin_session") == "ADMIN_AUTHORIZED":
                # Auto-create admin user if needed
                user = db.query(models.User).filter(
                    models.User.role.in_(["superuser", "admin"])
                ).first()
                if not user:
                    user = models.User(
                        username="admin",
                        email="admin@echostack.gh",
                        password_hash="ADMIN_SESSION_ONLY",
                        role="admin",
                        is_active=True,
                        is_premium=True
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
            else:
                raise HTTPException(status_code=401, detail="Login required")

        # ✅ Critical fix: author_id is UUID → store as UUID, not int
        author_id = user.id  # This is UUID (from models.py)
        author_name = user.username

        # Parse region_id safely
        region_id_int = None
        if region_id and region_id.isdigit():
            region_id_int = int(region_id)

        # Create post
        post = models.Post(
            author_id=author_id,               # UUID — matches model
            author_username=author_name,
            title=title.strip(),
            excerpt=excerpt.strip(),
            content=content.strip(),
            cover_image=cover_image.strip(),
            content_type=content_type,
            region_id=region_id_int,
            status=status,
            is_premium=bool(int(is_premium))
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        return {"success": True, "post_id": post.id, "status": post.status}
    except Exception as e:
        db.rollback()
        print(f"[CRITICAL] POST CREATE FAILED: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(post)
    db.commit()
    return {"success": True}

# ───────────────────────────────────────────────
# OTHER ENDPOINTS (minimal — just enough to work)
# ───────────────────────────────────────────────
@app.get("/api/posts")
def get_posts(status: str = "published", limit: int = 20, db: Session = Depends(get_db)):
    try:
        q = db.query(models.Post)
        if status != "all":
            q = q.filter(models.Post.status == status)
        posts = q.order_by(models.Post.created_at.desc()).limit(limit).all()
        return [{
            "id": p.id,
            "title": p.title,
            "excerpt": p.excerpt or "",
            "cover_image": p.cover_image or "",
            "author_username": p.author_username or "",
            "status": p.status,
            "created_at": str(p.created_at)
        } for p in posts]
    except Exception as e:
        print(f"[ERROR] Get posts: {e}")
        return []

@app.get("/api/users/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {
        "id": str(user.id),
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "is_premium": user.is_premium
    }

# ───────────────────────────────────────────────
# ADDITIONAL ROUTES (for completeness)
# ───────────────────────────────────────────────
@app.get("/subscriptions")
async def subscriptions_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("subscriptions.html")

@app.get("/following")
async def following_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("following.html")

@app.get("/activity")
async def activity_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("activity.html")

@app.get("/explore")
async def explore_page(request: Request):
    return serve_file("explore.html")

@app.get("/archive")
async def archive_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("archive.html")

# ───────────────────────────────────────────────
# FINAL: HTMLResponse for dynamic JS responses
# ───────────────────────────────────────────────
from fastapi.responses import HTMLResponse
