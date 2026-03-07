# ✅ ADD Response to the imports
from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os, json, re, hashlib, datetime, hmac, urllib.request
from pathlib import Path
from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)
app = FastAPI(title="EchoStack API")

# ============================================
# CONFIGURATION
# ============================================
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder: {e}")

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "THE ADMIN")
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# ============================================
# HELPERS
# ============================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def get_user_from_request(request: Request, db: Session):
    # Try user_session cookie first
    user_id = request.cookies.get("user_session")
    if user_id:
        try:
            return db.query(models.User).filter(models.User.id == int(user_id)).first()
        except:
            pass
    # If admin is logged in via admin_session, find their user record by role
    if request.cookies.get("admin_session") == "ADMIN_AUTHORIZED":
        try:
            # Return the first superuser/admin user record so admin can post, chat, etc.
            admin_user = db.query(models.User).filter(
                models.User.role.in_(["superuser", "admin"])
            ).first()
            if admin_user:
                return admin_user
        except:
            pass
    return None

def require_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token != "ADMIN_AUTHORIZED":
        raise HTTPException(status_code=403, detail="Not authorized")

async def save_upload(file: UploadFile) -> str:
    """Save an uploaded file and return its public URL."""
    content = await file.read()
    safe = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename.replace(' ', '_')}"
    with open(UPLOAD_DIR / safe, "wb") as f:
        f.write(content)
    return f"/uploads/{safe}"

# ============================================
# STATIC PAGES
# ============================================
def serve_file(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename)
    raise HTTPException(status_code=404, detail=f"{filename} not found")

@app.get("/")
def homepage(): return serve_file("index.html")

@app.get("/signup")
def signup_page(): return serve_file("signup.html")

@app.get("/user-login")
def user_login_page(): return serve_file("user-login.html")

def is_logged_in(request: Request) -> bool:
    """Returns True if user is logged in OR admin is previewing the site."""
    return bool(
        request.cookies.get("user_session") or
        request.cookies.get("admin_preview") or
        request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
    )

@app.get("/dashboard")
async def dashboard_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/user-login")
    return serve_file("dashboard.html")

@app.get("/creator")
async def creator_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/user-login")
    return serve_file("creator.html")

@app.get("/post/{post_id}")
async def post_page(post_id: int, request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/user-login")
    return serve_file("post.html")

@app.get("/app")
async def app_page(request: Request):
    if not is_logged_in(request):
        return RedirectResponse(url="/user-login")
    return serve_file("app.html")

@app.get("/admin")
async def admin_page(request: Request):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED":
        return serve_file("login.html")
    return serve_file("admin_dashboard.html")

@app.get("/client-login")
def client_login_page(): return serve_file("client_login.html")

@app.get("/client-dashboard")
async def client_dashboard_page(request: Request):
    if not request.cookies.get("client_session"):
        return RedirectResponse(url="/client-login")
    return serve_file("client_dashboard.html")

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

# ============================================
# ADMIN AUTH
# ============================================
@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    cleaned = ADMIN_SECRET.lower().replace(" ", "")
    given = answer.strip().lower().replace(" ", "")
    if cleaned == given:
        response = JSONResponse(content={"success": True})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED",
                            max_age=86400, path="/", httponly=False)
        return response
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout():
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(key="admin_session", path="/")
    return resp

# ============================================
# USER ACCOUNTS
# ============================================
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
            username=username, email=email,
            password_hash=hash_password(password),
            interests=interests or "", role="user", is_active=1
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        response = JSONResponse(content={
            "success": True, "user_id": new_user.id,
            "username": new_user.username, "email": new_user.email,
            "role": new_user.role, "is_premium": new_user.is_premium or 0
        })
        response.set_cookie(key="user_session", value=str(new_user.id),
                            max_age=86400 * 7, path="/")
        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        response = JSONResponse(content={
            "success": True, "user_id": user.id,
            "username": user.username, "email": user.email,
            "role": user.role or "user", "is_premium": user.is_premium or 0
        })
        response.set_cookie(key="user_session", value=str(user.id),
                            max_age=86400 * 7, path="/")
        return response
    except HTTPException:
        raise
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/logout")
def user_logout():
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(key="user_session", path="/")
    return resp

@app.get("/api/users/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {
        "id": user.id, "username": user.username, "email": user.email,
        "full_name": user.full_name or "", "bio": user.bio or "",
        "interests": user.interests or "", "avatar_url": user.avatar_url or "",
        "role": user.role or "user", "is_premium": user.is_premium or 0,
        "created_at": str(user.created_at)
    }

# ============================================
# ADMIN — USERS
# ============================================
@app.get("/api/admin/users")
def get_all_users(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    try:
        users = db.query(models.User).order_by(models.User.created_at.desc()).all()
        return [{
            "id": u.id, "username": u.username, "email": u.email,
            "role": u.role or "user", "is_premium": u.is_premium or 0,
            "plan": "premium" if u.is_premium else "free",
            "is_active": bool(u.is_active) if u.is_active is not None else True,
            "created_at": str(u.created_at) if u.created_at else ""
        } for u in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/users/{user_id}/role")
def set_user_role(user_id: int, request: Request, role: str = Form(...), db: Session = Depends(get_db)):
    require_admin(request)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role not in ["user", "creator", "admin", "superuser"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    user.role = role
    db.commit()
    return {"success": True, "role": role}

@app.put("/api/admin/users/{user_id}/premium")
def toggle_premium(user_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_premium = 0 if user.is_premium else 1
    db.commit()
    return {"success": True, "is_premium": user.is_premium}

@app.put("/api/admin/users/{user_id}/suspend")
def toggle_suspend(user_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    current = bool(user.is_active) if user.is_active is not None else True
    user.is_active = 0 if current else 1
    db.commit()
    return {"success": True, "is_active": bool(user.is_active)}

# ============================================
# REGIONS — with file upload OR URL support
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        regions = db.query(models.Region).all()
        return [{
            "id": int(r.id),
            "name": str(r.name) if r.name else "",
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
        "audio_files": r.audio_files or "", "tags": r.tags or ""
    }

@app.post("/api/regions")
async def create_region(
    name: str = Form(...),
    capital: str = Form(""),
    population: str = Form(""),
    terrain: str = Form(""),
    description: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    overview: str = Form(""),
    source: str = Form(""),
    # URL inputs (admin can paste a URL)
    hero_image: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    # File inputs (admin can upload from phone/computer)
    hero_file: UploadFile = File(None),
    gallery_file: UploadFile = File(None),
    audio_file: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")

        # Hero: uploaded file takes priority over URL
        final_hero = hero_image.strip()
        if hero_file and hero_file.filename:
            final_hero = await save_upload(hero_file)

        # Gallery: merge typed URLs + uploaded file
        gallery_list = [u.strip() for u in gallery_images.split(",") if u.strip()]
        if gallery_file and gallery_file.filename:
            gallery_list.append(await save_upload(gallery_file))
        final_gallery = ", ".join(gallery_list)

        # Audio: uploaded file takes priority over URL
        final_audio = audio_files.strip()
        if audio_file and audio_file.filename:
            final_audio = await save_upload(audio_file)

        r = models.Region(
            name=name.strip(), capital=capital.strip(), population=population.strip(),
            terrain=terrain.strip(), description=description.strip(),
            overview=overview.strip() or description.strip(),
            category=category.strip(), tags=tags.strip(),
            hero_image=final_hero, gallery_images=final_gallery,
            audio_files=final_audio, source=source.strip()
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
    region_id: int,
    name: str = Form(None),
    capital: str = Form(None),
    population: str = Form(None),
    terrain: str = Form(None),
    description: str = Form(None),
    category: str = Form(None),
    tags: str = Form(None),
    overview: str = Form(None),
    source: str = Form(None),
    # URL inputs
    hero_image: str = Form(None),
    gallery_images: str = Form(None),
    audio_files: str = Form(None),
    # File inputs
    hero_file: UploadFile = File(None),
    gallery_file: UploadFile = File(None),
    audio_file: UploadFile = File(None),
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
        if source is not None: r.source = source.strip()

        # Hero image
        if hero_file and hero_file.filename:
            r.hero_image = await save_upload(hero_file)
        elif hero_image is not None:
            r.hero_image = hero_image.strip()

        # Gallery images
        if gallery_file and gallery_file.filename:
            existing = [u.strip() for u in (r.gallery_images or "").split(",") if u.strip()]
            if gallery_images is not None:
                existing = [u.strip() for u in gallery_images.split(",") if u.strip()]
            existing.append(await save_upload(gallery_file))
            r.gallery_images = ", ".join(existing)
        elif gallery_images is not None:
            r.gallery_images = gallery_images.strip()

        # Audio files
        if audio_file and audio_file.filename:
            r.audio_files = await save_upload(audio_file)
        elif audio_files is not None:
            r.audio_files = audio_files.strip()

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
# FILE UPLOADS (general — images, video, audio, docs)
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(...),
    category: str = Form("general"),
    description: str = Form(""),
    region_id: str = Form(""),
    is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        safe_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename.replace(' ', '_')}"
        file_path = UPLOAD_DIR / safe_name
        content = await file.read()
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
            "file_size_mb": round(len(content) / (1024 * 1024), 2),
            "mime_type": file.content_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files(category: str = "", region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category:
            q = q.filter(models.UploadedFile.category == category)
        if region_id:
            q = q.filter(models.UploadedFile.region_id == int(region_id))
        return [{
            "id": f.id, "filename": f.filename, "original_name": f.original_name,
            "file_url": f"/uploads/{f.filename}",
            "file_size": f.file_size,
            "file_size_mb": round((f.file_size or 0) / (1024 * 1024), 2),
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
        if os.path.exists(f.file_path):
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
def get_posts(status: str = "published", content_type: str = "", limit: int = 20,
              db: Session = Depends(get_db)):
    try:
        q = db.query(models.Post).filter(models.Post.status == status)
        if content_type:
            q = q.filter(models.Post.content_type == content_type)
        posts = q.order_by(models.Post.created_at.desc()).limit(limit).all()
        return [{
            "id": p.id, "title": p.title, "excerpt": p.excerpt or "",
            "cover_image": p.cover_image or "", "content_type": p.content_type or "article",
            "author_username": p.author_username or "", "author_id": p.author_id,
            "status": p.status, "views": p.views or 0, "likes": p.likes or 0,
            "is_premium": p.is_premium or 0, "region_id": p.region_id,
            "created_at": str(p.created_at)
        } for p in posts]
    except Exception as e:
        print(f"Error getting posts: {e}")
        return []

@app.post("/api/posts")
async def create_post(
    title: str = Form(...), excerpt: str = Form(""), content: str = Form(""),
    cover_image: str = Form(""), content_type: str = Form("article"),
    region_id: str = Form(""), status: str = Form("draft"), is_premium: str = Form("0"),
    request: Request = None, db: Session = Depends(get_db)
):
    is_admin_session = request and request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
    user = get_user_from_request(request, db)

    # Admin can always post — use their user record or create a synthetic one
    if is_admin_session and not user:
        # Auto-create an admin user account if none exists
        try:
            admin_user = models.User(
                username="admin",
                email="admin@echostack.gh",
                password_hash="ADMIN_SESSION_ONLY",
                role="admin",
                is_active=1,
                is_premium=1
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            user = admin_user
        except Exception as e:
            db.rollback()
            # Try to get any existing admin
            user = db.query(models.User).filter(models.User.role.in_(["admin","superuser"])).first()

    if not user and not is_admin_session:
        raise HTTPException(status_code=401, detail="Must be logged in")
    if user and user.role not in ["creator", "superuser", "admin"] and not is_admin_session:
        raise HTTPException(status_code=403, detail="Creator account required")

    author_id = user.id if user else 0
    author_name = user.username if user else "Admin"

    post = models.Post(
        author_id=author_id, author_username=author_name,
        title=title.strip(), excerpt=excerpt.strip(), content=content.strip(),
        cover_image=cover_image.strip(), content_type=content_type,
        region_id=int(region_id) if region_id and region_id.isdigit() else None,
        status=status, is_premium=int(is_premium)
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"success": True, "post_id": post.id, "status": post.status}

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int, title: str = Form(None), excerpt: str = Form(None),
    content: str = Form(None), cover_image: str = Form(None),
    content_type: str = Form(None), status: str = Form(None),
    is_premium: str = Form(None), region_id: str = Form(None),
    request: Request = None, db: Session = Depends(get_db)
):
    is_admin = request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"
    user = get_user_from_request(request, db)
    if not is_admin and not user:
        raise HTTPException(status_code=401, detail="Not authorized")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if not is_admin and user and post.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not your post")
    if title is not None and title.strip(): post.title = title.strip()
    if excerpt is not None: post.excerpt = excerpt.strip()
    if content is not None: post.content = content.strip()
    if cover_image is not None: post.cover_image = cover_image.strip()
    if content_type is not None: post.content_type = content_type
    if status is not None: post.status = status
    if is_premium is not None: post.is_premium = int(is_premium)
    if region_id is not None:
        post.region_id = int(region_id) if region_id and region_id.isdigit() else None
    db.commit()
    db.refresh(post)
    return {"success": True, "post_id": post.id, "status": post.status}

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

    if not user and is_admin_session:
        # Auto-create admin user if needed
        try:
            admin_user = models.User(
                username="admin", email="admin@echostack.gh",
                password_hash="ADMIN_SESSION_ONLY",
                role="admin", is_active=1, is_premium=1
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            user = admin_user
        except:
            db.rollback()
            user = db.query(models.User).filter(models.User.role.in_(["admin","superuser"])).first()

    if not user and not is_admin_session:
        raise HTTPException(status_code=401, detail="Must be logged in to submit a story")

    author_name = user.username if user else "Admin"
    author_id = user.id if user else 0
    # Admin stories are auto-approved
    auto_status = "approved" if is_admin_session else "pending"

    try:
        story = models.StorySubmission(
            title=title.strip(), content=content.strip(), username=author_name,
            user_id=author_id,
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
async def newsletter_subscribe(email: str = Form(...), full_name: str = Form(""),
                               db: Session = Depends(get_db)):
    existing = db.query(models.NewsletterSubscriber).filter(
        models.NewsletterSubscriber.email == email.lower()).first()
    if existing:
        return {"success": True, "message": "Already subscribed!"}
    sub = models.NewsletterSubscriber(email=email.lower(), full_name=full_name)
    db.add(sub)
    db.commit()
    return {"success": True, "message": "Subscribed successfully!"}

@app.get("/api/newsletter/subscribers")
def get_newsletter_subscribers(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    try:
        subs = db.query(models.NewsletterSubscriber).order_by(
            models.NewsletterSubscriber.created_at.desc()).all()
        return [{
            "id": s.id, "email": s.email, "full_name": s.full_name or "",
            "created_at": str(s.created_at) if s.created_at else ""
        } for s in subs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# EVENTS
# ============================================
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    try:
        events = db.query(models.Event).filter(models.Event.is_active == 1).all()
        return [{"id": e.id, "title": e.title, "description": e.description,
                 "event_date": e.event_date, "location": e.location, "image_url": e.image_url}
                for e in events]
    except:
        return []

@app.post("/api/events")
async def create_event(
    title: str = Form(...), description: str = Form(""), event_date: str = Form(""),
    location: str = Form(""), image_url: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    require_admin(request)
    event = models.Event(title=title, description=description, event_date=event_date,
                         location=location, image_url=image_url)
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"success": True, "event_id": event.id}

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)
    event.is_active = 0
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
    except:
        return []

@app.post("/api/chat")
async def post_message(message: str = Form(...), region_id: str = Form(""),
                       request: Request = None, db: Session = Depends(get_db)):
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
# CREATORS
# ============================================
@app.get("/api/creators")
def get_creators(db: Session = Depends(get_db)):
    try:
        channels = db.query(models.CreatorChannel).filter(models.CreatorChannel.is_active == 1).all()
        result = []
        for c in channels:
            user = db.query(models.User).filter(models.User.id == c.user_id).first()
            post_count = db.query(models.Post).filter(models.Post.author_id == c.user_id).count()
            result.append({
                "id": c.user_id,
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
    except:
        return []

@app.post("/api/sections")
def create_section(name: str = Form(...), description: str = Form(""),
                   display_order: int = Form(0), db: Session = Depends(get_db)):
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
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
        s.is_active = 0
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

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
async def ai_chat(message: str = Form(...), region_context: str = Form(""),
                  request: Request = None, db: Session = Depends(get_db)):
    try:
        user = get_user_from_request(request, db)
        is_premium = user and (user.is_premium or user.role in ["superuser", "admin", "creator"])

        if not user:
            return {"reply": "EchoBot is a premium feature 🔒 Subscribe for GH₵150/month to unlock unlimited AI heritage assistance!", "success": False, "locked": True}
        if not is_premium:
            return {"reply": "EchoBot is a premium feature 🔒 Subscribe for GH₵150/month to unlock unlimited AI heritage assistance!", "success": False, "locked": True}
        if not HF_TOKEN:
            return {"reply": "EchoBot is not configured yet. Ask your admin to add HF_TOKEN to Render environment variables.", "success": False}

        # Load all regions from DB to give EchoBot site knowledge
        try:
            regions = db.query(models.Region).all()
            regions_summary = ""
            for r in regions:
                regions_summary += f"- {r.name}"
                if r.capital: regions_summary += f" (Capital: {r.capital})"
                if r.population: regions_summary += f", Population: {r.population}"
                if r.terrain: regions_summary += f", Terrain: {r.terrain}"
                if r.category: regions_summary += f", Category: {r.category}"
                if r.description: regions_summary += f"\n  Description: {r.description[:300]}"
                regions_summary += "\n"
        except:
            regions_summary = "Region data unavailable."

        # Load sections/categories
        try:
            sections = db.query(models.Section).all()
            sections_text = ", ".join([s.name for s in sections]) if sections else "None yet"
        except:
            sections_text = "Unknown"

        # Load events
        try:
            events = db.query(models.Event).limit(5).all() if hasattr(models, "Event") else []
            events_text = ""
            for ev in events:
                events_text += f"- {ev.title}"
                if hasattr(ev, "date") and ev.date: events_text += f" ({ev.date})"
                if hasattr(ev, "location") and ev.location: events_text += f" at {ev.location}"
                events_text += "\n"
            if not events_text: events_text = "No upcoming events."
        except:
            events_text = "Events unavailable."

        user_plan = "Premium" if is_premium else "Free"

        system_prompt = f"""You are EchoBot, the AI heritage guide for EchoStack — a platform dedicated to preserving and sharing Ghana's cultural heritage across all 16 regions.

ABOUT ECHOSTACK:
EchoStack is a Ghana heritage platform where users can explore the history, culture, traditions, music, festivals, and oral stories of Ghana's 16 regions. Content creators share heritage content and users can subscribe to creators, follow people, and engage with community chat.

THE USER:
- Plan: {user_plan}
- Premium users get unlimited AI assistance. Free users have limited access.

GHANA'S 16 REGIONS ON THIS PLATFORM (current site data):
{regions_summary if regions_summary else "No regions uploaded yet."}

SITE CATEGORIES: {sections_text}

UPCOMING EVENTS:
{events_text}

YOUR ROLE:
- Answer questions about Ghana's heritage, culture, history, traditions, festivals, food, music, language, and people.
- When asked about a specific region, use the data above. If a region has no data yet, say so honestly and share your own knowledge about it.
- You can explain how EchoStack works (exploring regions, creator subscriptions, community chat, premium features).
- Do NOT reveal or discuss any user's personal information, usernames, or accounts.
- Keep answers warm, educational, and concise (3-6 sentences unless more detail is needed).
- Use occasional Ghanaian greetings like "Akwaaba!" to feel authentic.
- If asked something unrelated to Ghana or EchoStack, gently redirect to heritage topics."""

        if region_context:
            system_prompt += f"\n\nCURRENT CONTEXT: The user is viewing the {region_context} region — prioritise information about this region."

        full_prompt = f"<s>[INST] {system_prompt}\n\nUser: {message} [/INST]"
        payload = json.dumps({
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 400,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False,
                "stop": ["[INST]", "</s>"]
            }
        }).encode("utf-8")

        # Retry up to 3 times to handle HuggingFace cold-start (503 model loading)
        last_error = ""
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
                    data=payload,
                    headers={"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=45) as response:
                    raw = response.read().decode("utf-8")
                    result = json.loads(raw)

                # Handle HuggingFace loading response
                if isinstance(result, dict) and result.get("error", "").lower().find("loading") != -1:
                    estimated = result.get("estimated_time", 20)
                    if attempt < 2:
                        import time
                        time.sleep(min(estimated, 15))
                        continue
                    return {"reply": f"EchoBot is loading (model cold start). Please wait about {int(estimated)} seconds and try again!", "success": False, "warming": True}

                reply = ""
                if isinstance(result, list) and result:
                    reply = result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    reply = result.get("generated_text", result.get("error", "")).strip()

                if reply:
                    # Clean up any leaked prompt fragments
                    reply = reply.replace("[INST]", "").replace("[/INST]", "").replace("</s>", "").strip()
                    return {"reply": reply, "success": True, "locked": False}
                else:
                    last_error = "Empty response"
                    break

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8") if e.fp else ""
                print(f"HF HTTP {e.code}: {body}")
                if e.code == 503:
                    last_error = "Model loading"
                    import time
                    time.sleep(10)
                    continue
                last_error = f"HTTP {e.code}"
                break
            except Exception as ex:
                last_error = str(ex)
                print(f"AI attempt {attempt} error: {ex}")
                break

        print(f"AI final error: {last_error}")
        return {"reply": "I'm having a moment — please try again! If this keeps happening, the AI model may need a minute to warm up.", "success": False}

    except Exception as e:
        print(f"AI chat outer error: {e}")
        return {"reply": "Something went wrong on my end. Please try again shortly!", "success": False}

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
    payload = json.dumps({"email": user.email, "amount": 15000, "currency": "GHS",
                          "callback_url": "https://echostackgh.onrender.com/payment/callback",
                          "metadata": {"user_id": user.id, "plan": "premium"}}).encode("utf-8")
    req = urllib.request.Request("https://api.paystack.co/transaction/initialize", data=payload,
                                 headers={"Authorization": f"Bearer {PAYSTACK_SECRET}", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Paystack error: {str(e)}")
    if not result.get("status"):
        raise HTTPException(status_code=400, detail="Payment initialization failed")
    return {"success": True, "authorization_url": result["data"]["authorization_url"],
            "reference": result["data"]["reference"]}

@app.post("/api/payments/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    try:
        data = json.loads(body.decode("utf-8"))
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    if data.get("event") == "charge.success":
        user_id = data["data"].get("metadata", {}).get("user_id")
        if user_id:
            try:
                user = db.query(models.User).filter(models.User.id == int(user_id)).first()
                if user:
                    user.is_premium = 1
                    db.commit()
            except:
                pass
    return {"status": "ok"}

@app.get("/payment/callback")
async def payment_callback(reference: str, request: Request, db: Session = Depends(get_db)):
    if not PAYSTACK_SECRET:
        return RedirectResponse("/premium?payment=error")
    req = urllib.request.Request(f"https://api.paystack.co/transaction/verify/{reference}",
                                 headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except:
        return RedirectResponse("/premium?payment=error")
    if result.get("status") and result["data"].get("status") == "success":
        # Try metadata first, then fall back to current session user
        user_id = result["data"].get("metadata", {}).get("user_id")
        if not user_id:
            session_user = get_user_from_request(request, db)
            if session_user:
                user_id = session_user.id
        if user_id:
            try:
                user = db.query(models.User).filter(models.User.id == int(user_id)).first()
                if user:
                    user.is_premium = 1
                    db.commit()
                    # Return page that updates localStorage too
                    html = f"""<!DOCTYPE html><html><head><title>Payment Success</title></head><body>
<script>
try {{
    var u = JSON.parse(localStorage.getItem('es_user') || '{{}}');
    u.is_premium = 1; u.plan = 'premium';
    localStorage.setItem('es_user', JSON.stringify(u));
}} catch(e) {{}}
window.location.href = '/premium?upgraded=1';
</script>
</body></html>"""
                    from fastapi.responses import HTMLResponse
                    return HTMLResponse(content=html)
            except:
                pass
        return RedirectResponse("/premium?upgraded=1")
    return RedirectResponse("/premium?payment=failed")

@app.get("/premium")
async def premium_page(request: Request):
    return serve_file("premium.html")

# ============================================
# ADMIN PREVIEW — skip user login when viewing site from admin dashboard
# ============================================
@app.get("/admin-preview")
async def admin_preview(request: Request, db: Session = Depends(get_db)):
    """Admin clicks 'View Site' — sets preview + user_session cookies and sets localStorage via redirect page."""
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED":
        return RedirectResponse(url="/admin")
    # Also set user_session so admin can interact with the site fully
    admin_user = db.query(models.User).filter(
        models.User.role.in_(["superuser", "admin"])
    ).first()
    # Serve a small HTML page that sets localStorage then redirects to /app
    user_id = admin_user.id if admin_user else ""
    username = admin_user.username if admin_user else "Admin"
    role = admin_user.role if admin_user else "admin"
    is_premium = admin_user.is_premium if admin_user else 1
    html = f"""<!DOCTYPE html><html><head><title>Loading...</title></head><body>
<script>
try {{
    localStorage.setItem('es_user', JSON.stringify({{
        loggedIn: true,
        user_id: {user_id if user_id else 1},
        username: "{username}",
        email: "",
        role: "{role}",
        plan: "premium",
        is_premium: 1
    }}));
}} catch(e) {{}}
window.location.href = '/app';
</script>
<p>Redirecting to site...</p>
</body></html>"""
    from fastapi.responses import HTMLResponse
    response = HTMLResponse(content=html)
    response.set_cookie(key="admin_preview", value="1", max_age=3600, path="/")
    if user_id:
        response.set_cookie(key="user_session", value=str(user_id), max_age=3600, path="/")
    return response
