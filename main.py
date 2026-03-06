from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json
import re
import hashlib

from database import engine, get_db, Base
import models

# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# CONFIGURATION
# ============================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder: {e}")

CORRECT_ANSWER = "THE ADMIN"

# ============================================
# PASSWORD HELPERS
# ============================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

# ============================================
# STATIC PAGES
# ============================================
@app.get("/")
def homepage():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/app")
async def app_page(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/user-login")
    if os.path.exists("app.html"):
        return FileResponse("app.html")
    raise HTTPException(status_code=404)

@app.get("/signup")
def signup_page():
    if os.path.exists("signup.html"):
        return FileResponse("signup.html")
    raise HTTPException(status_code=404)

@app.get("/user-login")
def user_login_page():
    if os.path.exists("user-login.html"):
        return FileResponse("user-login.html")
    raise HTTPException(status_code=404)

@app.get("/login")
def admin_login_page():
    if os.path.exists("login.html"):
        return FileResponse("login.html")
    raise HTTPException(status_code=404)

@app.get("/admin")
async def admin_dashboard_page(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token != "ADMIN_AUTHORIZED":
        if os.path.exists("login.html"):
            return FileResponse("login.html")
        raise HTTPException(status_code=404)
    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")
    raise HTTPException(status_code=404)

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "backend": "working"}

@app.get("/echostack-logo.png")
def serve_logo():
    if os.path.exists("echostack-logo.png"):
        return FileResponse("echostack-logo.png", media_type="image/png")
    raise HTTPException(status_code=404)

@app.get("/sw.js")
def serve_sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404)

# ============================================
# ADMIN AUTHENTICATION
# ============================================
@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    cleaned = CORRECT_ANSWER.lower().replace(" ", "")
    given = answer.strip().lower().replace(" ", "")
    if cleaned == given:
        response = JSONResponse(content={"success": True})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED", max_age=86400, path="/")
        return response
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="admin_session", path="/")
    return response

# ============================================
# USER ACCOUNTS (Public Users)
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
        existing_email = db.query(models.User).filter(models.User.email == email.lower().strip()).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        existing_username = db.query(models.User).filter(models.User.username == username.strip()).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        new_user = models.User(
            username=username.strip(),
            email=email.lower().strip(),
            password_hash=hash_password(password),
            interests=interests
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        response = JSONResponse(content={"success": True, "user_id": new_user.id, "username": new_user.username})
        response.set_cookie(key="user_session", value=str(new_user.id), max_age=86400*7, path="/")
        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/login")
async def user_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.User).filter(
            (models.User.email == username.lower().strip()) |
            (models.User.username == username.strip())
        ).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        response = JSONResponse(content={
            "success": True,
            "user_id": user.id,
            "username": user.username
        })
        response.set_cookie(key="user_session", value=str(user.id), max_age=86400*7, path="/")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/logout")
def user_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="user_session", path="/")
    return response

@app.get("/api/users/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_session")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name or "",
        "bio": user.bio or "",
        "interests": user.interests or "",
        "avatar_url": user.avatar_url or "",
        "created_at": str(user.created_at)
    }

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
            "source": str(r.source) if r.source else ""
        } for r in regions]
    except Exception as e:
        print(f"Error getting regions: {e}")
        return []

@app.post("/api/regions")
def create_region(
    name: str = Form(...), capital: str = Form(""), population: str = Form(""),
    terrain: str = Form(""), description: str = Form(""), category: str = Form(""),
    tags: str = Form(""), hero_image: str = Form(""), gallery_images: str = Form(""),
    audio_files: str = Form(""), source: str = Form(""), overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")
        r = models.Region(
            name=name.strip(), capital=capital.strip(), population=population.strip(),
            terrain=terrain.strip(), description=description.strip(),
            overview=overview.strip() or description.strip(),
            category=category.strip(), tags=tags.strip(), hero_image=hero_image.strip(),
            gallery_images=gallery_images.strip(), audio_files=audio_files.strip(),
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
def update_region(
    region_id: int, name: str = Form(None), capital: str = Form(None),
    population: str = Form(None), terrain: str = Form(None), description: str = Form(None),
    category: str = Form(None), tags: str = Form(None), hero_image: str = Form(None),
    gallery_images: str = Form(None), audio_files: str = Form(None),
    source: str = Form(None), overview: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        r = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Not found")
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
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(r)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FILE UPLOADS
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(...),
    category: str = Form("general"), description: str = Form(""),
    region_id: str = Form(""), is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        ext = os.path.splitext(filename)[1].lower()
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext or '.bin'}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        uf = models.UploadedFile(
            filename=safe_name, original_name=filename, file_path=file_path,
            file_size=len(content), mime_type=file.content_type or "application/octet-stream",
            category=category, region_id=int(region_id) if region_id and region_id.isdigit() else None,
            description=description, uploaded_by="admin",
            is_public=int(is_public) if is_public else 1
        )
        db.add(uf)
        db.commit()
        db.refresh(uf)
        return {"success": True, "file_id": uf.id, "url": f"/uploads/{safe_name}",
                "filename": safe_name, "original_name": filename, "category": category,
                "size_bytes": len(content), "file_size_mb": round(len(content)/(1024*1024), 2),
                "mime_type": file.content_type}
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files(category: str = "", region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category: q = q.filter(models.UploadedFile.category == category)
        if region_id: q = q.filter(models.UploadedFile.region_id == int(region_id))
        return [{"id": f.id, "filename": f.filename, "original_name": f.original_name,
                 "file_url": f"/uploads/{f.filename}", "file_size": f.file_size,
                 "file_size_mb": round(f.file_size/(1024*1024), 2), "mime_type": f.mime_type,
                 "category": f.category, "region_id": f.region_id, "description": f.description,
                 "created_at": str(f.created_at)} for f in q.order_by(models.UploadedFile.created_at.desc()).all()]
    except Exception as e:
        print(f"Error getting files: {e}")
        return []

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    try:
        f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
        if not f: raise HTTPException(status_code=404)
        if os.path.exists(f.file_path): os.remove(f.file_path)
        db.delete(f)
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SECTIONS
# ============================================
@app.post("/api/sections")
def create_section(name: str = Form(...), description: str = Form(""), display_order: int = Form(0), db: Session = Depends(get_db)):
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

@app.get("/api/sections")
def get_sections(active_only: int = 1, db: Session = Depends(get_db)):
    try:
        q = db.query(models.Section)
        if active_only: q = q.filter(models.Section.is_active == 1).order_by(models.Section.display_order)
        return [{"id": s.id, "name": s.name, "slug": s.slug, "description": s.description} for s in q.all()]
    except Exception as e:
        print(f"Error getting sections: {e}")
        return []

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    try:
        s = db.query(models.Section).filter(models.Section.id == section_id).first()
        if not s: raise HTTPException(status_code=404)
        s.is_active = 0
        db.commit()
        return {"success": True}
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
            "total_users": db.query(models.User).count() if hasattr(models, 'User') else 0,
            "with_audio": db.query(models.UploadedFile).filter(models.UploadedFile.category == "audio").count(),
            "with_images": db.query(models.UploadedFile).filter(models.UploadedFile.category == "image").count(),
            "database_size_mb": 0
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {"total_regions": 0, "database_size_mb": 0}

@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    try:
        if not isinstance(data, list): data = [data]
        imported = 0
        for rd in data:
            try:
                db.add(models.Region(**rd))
                imported += 1
            except: continue
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# THEME
# ============================================
@app.post("/api/theme")
async def save_theme(theme: str = Form(...)):
    try:
        with open("theme.json", "w") as f: f.write(theme)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/theme")
def get_theme():
    try:
        if os.path.exists("theme.json"):
            with open("theme.json", "r") as f: return json.load(f)
        return {}
    except:
        return {}
