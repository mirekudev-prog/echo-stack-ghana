from fastapi import FastAPI, Depends, Form, HTTPException, UploadFile, File, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import hashlib
import os
import json
import shutil
import datetime
from pathlib import Path

from database import engine, get_db, Base, init_db
import models

init_db()

app = FastAPI(title="EchoStack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


# ── PAGE ROUTES ───────────────────────────────────────────────────────────────

@app.get("/")
def home(): return FileResponse("index.html")

@app.get("/app")
def app_view(): return FileResponse("app.html")

@app.get("/signup")
def signup_view(): return FileResponse("signup.html")

@app.get("/user-login")
def user_login_view(): return FileResponse("user-login.html")

@app.get("/dashboard")
def dashboard_view(): return FileResponse("dashboard.html")

@app.get("/admin")
def admin_view(): return FileResponse("admin_dashboard.html")

@app.get("/echostack-logo.png")
def logo(): return FileResponse("echostack-logo.png")


# ── USER REGISTRATION ─────────────────────────────────────────────────────────

@app.post("/api/users/register")
async def user_register(
    username:  str = Form(...),
    email:     str = Form(...),
    password:  str = Form(...),
    interests: str = Form("General"),
    db: Session = Depends(get_db)
):
    try:
        username = username.strip()
        email    = email.lower().strip()

        if not username or not email or not password:
            raise HTTPException(status_code=400, detail="All fields are required")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

        user = models.User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            interests=interests or "General",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"success": True, "message": "Account created successfully!"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ REGISTER ERROR: {e}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


# ── USER LOGIN ────────────────────────────────────────────────────────────────

@app.post("/api/users/login")
async def user_login(
    email:    str = Form(default=""),
    username: str = Form(default=""),
    password: str = Form(...),
    response: Response = None,
    db: Session = Depends(get_db)
):
    # Accept email or username field — use whichever was sent
    login_value = (email or username).lower().strip()

    if not login_value:
        raise HTTPException(status_code=400, detail="Email or username is required")

    try:
        # Try email first, then username
        user = db.query(models.User).filter(models.User.email == login_value).first()
        if not user:
            user = db.query(models.User).filter(models.User.username == login_value).first()

        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account is deactivated")

        return {
            "success":  True,
            "username": user.username,
            "email":    user.email,
            "plan":     "free",
            "message":  "Logged in!"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ LOGIN ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/logout")
async def user_logout(response: Response):
    response.delete_cookie("user_session")
    return {"success": True}


# ── ADMIN AUTH ────────────────────────────────────────────────────────────────

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "THE ADMIN")

@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...), response: Response = None):
    if answer.strip().upper() != ADMIN_SECRET.upper():
        raise HTTPException(status_code=401, detail="Wrong answer")
    session = hash_password(f"admin{datetime.datetime.utcnow()}")
    response.set_cookie(key="admin_session", value=session, httponly=True, max_age=86400)
    return {"success": True}

@app.post("/api/auth/logout")
async def admin_logout(response: Response):
    response.delete_cookie("admin_session")
    return {"success": True}


# ── STATS ─────────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        return {
            "total_regions":    db.query(models.Region).count(),
            "with_audio":       db.query(models.Region).filter(models.Region.audio_files.isnot(None), models.Region.audio_files != "").count(),
            "with_images":      db.query(models.Region).filter(models.Region.gallery_images.isnot(None), models.Region.gallery_images != "").count(),
            "user_count":       db.query(models.User).count(),
            "file_count":       db.query(models.UploadedFile).count(),
            "database_size_mb": 0
        }
    except Exception as e:
        print(f"❌ STATS ERROR: {e}")
        return {"total_regions": 0, "with_audio": 0, "with_images": 0, "user_count": 0, "file_count": 0, "database_size_mb": 0}


# ── REGIONS ───────────────────────────────────────────────────────────────────

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        return db.query(models.Region).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/regions/{region_id}")
def get_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    return region

@app.post("/api/regions")
async def create_region(
    name: str = Form(...), capital: str = Form(""), population: str = Form(""),
    terrain: str = Form(""), description: str = Form(""), category: str = Form(""),
    tags: str = Form(""), hero_image: str = Form(""), gallery_images: str = Form(""),
    audio_files: str = Form(""), source: str = Form(""), overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        region = models.Region(
            name=name.strip(), capital=capital.strip(), population=population,
            terrain=terrain, description=description, category=category,
            tags=tags, hero_image=hero_image, gallery_images=gallery_images,
            audio_files=audio_files, source=source, overview=overview
        )
        db.add(region); db.commit(); db.refresh(region)
        return {"success": True, "id": region.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/regions/{region_id}")
async def update_region(
    region_id: int, name: str = Form(...), capital: str = Form(""),
    population: str = Form(""), terrain: str = Form(""), description: str = Form(""),
    category: str = Form(""), tags: str = Form(""), hero_image: str = Form(""),
    gallery_images: str = Form(""), audio_files: str = Form(""),
    source: str = Form(""), overview: str = Form(""), db: Session = Depends(get_db)
):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region: raise HTTPException(status_code=404, detail="Region not found")
    try:
        region.name=name.strip(); region.capital=capital.strip(); region.population=population
        region.terrain=terrain; region.description=description; region.category=category
        region.tags=tags; region.hero_image=hero_image; region.gallery_images=gallery_images
        region.audio_files=audio_files; region.source=source; region.overview=overview
        region.updated_at=datetime.datetime.utcnow()
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region: raise HTTPException(status_code=404, detail="Region not found")
    try:
        db.delete(region); db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── FILE UPLOADS ──────────────────────────────────────────────────────────────

def save_upload(file: UploadFile, subfolder: str = "") -> dict:
    dest_dir = UPLOAD_DIR / subfolder if subfolder else UPLOAD_DIR
    dest_dir.mkdir(exist_ok=True)
    safe_name = "".join(c for c in file.filename if c.isalnum() or c in "._- ").strip()
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S_")
    final_name = timestamp + safe_name
    dest_path = dest_dir / final_name
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    size_mb = round(dest_path.stat().st_size / (1024 * 1024), 2)
    url = f"/uploads/{subfolder + '/' if subfolder else ''}{final_name}"
    return {"path": str(dest_path), "url": url, "filename": final_name, "original": file.filename, "size_mb": size_mb}

@app.post("/api/upload/file")
async def upload_any_file(
    file: UploadFile = File(...), filename: str = Form(""),
    category: str = Form("general"), description: str = Form(""),
    is_public: str = Form("1"), region_id: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        saved = save_upload(file, category)
        record = models.UploadedFile(
            filename=saved["filename"], original_name=saved["original"],
            file_path=saved["path"], file_url=saved["url"], category=category,
            description=description, file_size_mb=saved["size_mb"],
            is_public=(is_public == "1"),
            region_id=int(region_id) if region_id.isdigit() else None
        )
        db.add(record); db.commit(); db.refresh(record)
        return {"success": True, "url": saved["url"], "original_name": saved["original"], "file_size_mb": saved["size_mb"], "category": category}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        saved = save_upload(file, "image")
        db.add(models.UploadedFile(filename=saved["filename"], original_name=saved["original"], file_path=saved["path"], file_url=saved["url"], category="image", file_size_mb=saved["size_mb"], is_public=True))
        db.commit()
        return {"success": True, "url": saved["url"]}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        saved = save_upload(file, "audio")
        db.add(models.UploadedFile(filename=saved["filename"], original_name=saved["original"], file_path=saved["path"], file_url=saved["url"], category="audio", file_size_mb=saved["size_mb"], is_public=True))
        db.commit()
        return {"success": True, "url": saved["url"]}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files(db: Session = Depends(get_db)):
    try:
        return db.query(models.UploadedFile).order_by(models.UploadedFile.uploaded_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not f: raise HTTPException(status_code=404, detail="File not found")
    try:
        if f.file_path and Path(f.file_path).exists(): Path(f.file_path).unlink()
        db.delete(f); db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── SECTIONS ──────────────────────────────────────────────────────────────────

@app.get("/api/sections")
def get_sections(db: Session = Depends(get_db)):
    try:
        return db.query(models.Section).order_by(models.Section.display_order).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sections")
async def create_section(name: str = Form(...), db: Session = Depends(get_db)):
    try:
        slug = name.lower().strip().replace(" ", "-")
        if db.query(models.Section).filter(models.Section.slug == slug).first():
            raise HTTPException(status_code=400, detail="Section already exists")
        section = models.Section(name=name.strip(), slug=slug)
        db.add(section); db.commit(); db.refresh(section)
        return {"success": True, "id": section.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if not section: raise HTTPException(status_code=404, detail="Section not found")
    try:
        db.delete(section); db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── SITE BUILDER ──────────────────────────────────────────────────────────────

@app.get("/api/site-pages")
def get_site_pages(db: Session = Depends(get_db)):
    try:
        return db.query(models.SitePage).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/site-pages/{slug}")
def get_site_page(slug: str, db: Session = Depends(get_db)):
    page = db.query(models.SitePage).filter(models.SitePage.slug == slug).first()
    if not page: raise HTTPException(status_code=404, detail="Page not found")
    try: widgets = json.loads(page.widgets or "[]")
    except: widgets = []
    return {"id": page.id, "title": page.title, "slug": page.slug, "content": page.content, "widgets": widgets, "is_published": page.is_published, "is_home": page.is_home}

@app.get("/api/theme")
def get_theme(db: Session = Depends(get_db)):
    try:
        theme = db.query(models.SiteTheme).filter(models.SiteTheme.is_active == True).first()
        return {"name": theme.name if theme else "default"}
    except:
        return {"name": "default"}

@app.post("/api/theme")
async def set_theme(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        name = body.get("name", "default")
        db.query(models.SiteTheme).update({"is_active": False})
        theme = db.query(models.SiteTheme).filter(models.SiteTheme.name == name).first()
        if theme: theme.is_active = True
        else: db.add(models.SiteTheme(name=name, is_active=True))
        db.commit()
        return {"success": True, "name": name}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── NEWSLETTER ────────────────────────────────────────────────────────────────

@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(email: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)):
    try:
        if db.query(models.NewsletterSubscriber).filter(models.NewsletterSubscriber.email == email.lower().strip()).first():
            raise HTTPException(status_code=400, detail="Already subscribed")
        db.add(models.NewsletterSubscriber(email=email.lower().strip(), full_name=full_name))
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/newsletter/subscribers")
def get_subscribers(db: Session = Depends(get_db)):
    return db.query(models.NewsletterSubscriber).filter(models.NewsletterSubscriber.is_active == True).all()


# ── CHAT ──────────────────────────────────────────────────────────────────────

@app.get("/api/chat")
def get_chat(region_id: int = None, db: Session = Depends(get_db)):
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.is_approved == True)
        if region_id: q = q.filter(models.ChatMessage.region_id == region_id)
        return q.order_by(models.ChatMessage.created_at.desc()).limit(100).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def post_chat(message: str = Form(...), username: str = Form("Anonymous"), region_id: str = Form(""), db: Session = Depends(get_db)):
    try:
        msg = models.ChatMessage(username=username, message=message, region_id=int(region_id) if region_id.isdigit() else None)
        db.add(msg); db.commit(); db.refresh(msg)
        return {"success": True, "id": msg.id}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── STORIES ───────────────────────────────────────────────────────────────────

@app.get("/api/stories")
def get_stories(db: Session = Depends(get_db)):
    return db.query(models.StorySubmission).filter(models.StorySubmission.status == "approved").all()

@app.post("/api/stories")
async def submit_story(title: str = Form(...), content: str = Form(...), db: Session = Depends(get_db)):
    try:
        story = models.StorySubmission(title=title, content=content)
        db.add(story); db.commit(); db.refresh(story)
        return {"success": True, "id": story.id}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── EVENTS ────────────────────────────────────────────────────────────────────

@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    return db.query(models.Event).filter(models.Event.is_active == True).all()

@app.post("/api/events")
async def create_event(title: str = Form(...), description: str = Form(""), location: str = Form(""), image_url: str = Form(""), db: Session = Depends(get_db)):
    try:
        event = models.Event(title=title, description=description, location=location, image_url=image_url)
        db.add(event); db.commit(); db.refresh(event)
        return {"success": True, "id": event.id}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ── IMPORT ────────────────────────────────────────────────────────────────────

@app.post("/api/import/json")
async def import_json(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        regions = data if isinstance(data, list) else data.get("regions", [])
        count = 0
        for r in regions:
            db.add(models.Region(
                name=r.get("name","Unknown"), capital=r.get("capital",""),
                population=r.get("population",""), terrain=r.get("terrain",""),
                description=r.get("description",""), category=r.get("category",""),
                tags=r.get("tags",""), hero_image=r.get("hero_image",""),
                gallery_images=r.get("gallery_images",""), audio_files=r.get("audio_files",""),
                source=r.get("source",""), overview=r.get("overview","")
            ))
            count += 1
        db.commit()
        return {"success": True, "imported": count}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))
