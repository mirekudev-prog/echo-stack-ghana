from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json

from database import engine, get_db, Base
import models

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# SETUP FOLDERS FOR UPLOADS
# ============================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder")

# ============================================
# SECURITY SETTINGS
# ============================================
CORRECT_ANSWER = "THE ADMIN"

# ============================================
# PUBLIC ROUTES
# ============================================
@app.get("/")
def homepage():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "backend": "working"}

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404)

# ============================================
# LOGIN SYSTEM
# ============================================
@app.get("/admin")
async def admin_page(request: Request):
    """Serve admin dashboard"""
    token = request.cookies.get("admin_session")
    
    if not token or token != "ADMIN_AUTHORIZED":
        if os.path.exists("login.html"):
            return FileResponse("login.html")
        raise HTTPException(status_code=404)
    
    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")
    raise HTTPException(status_code=404)

@app.post("/api/auth/login")
async def login(answer: str = Form(...)):
    """Check security answer"""
    if CORRECT_ANSWER.lower() in answer.lower().replace(" ", ""):
        response = JSONResponse(content={"success": True, "token": "ADMIN_AUTHORIZED"})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED", max_age=86400, path="/")
        return response
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="admin_session", path="/")
    return response

# ============================================
# REGION CRUD OPERATIONS
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    """GET all regions"""
    try:
        regions = db.query(models.Region).all()
        
        result = []
        for r in regions:
            item = {
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
            }
            result.append(item)
        
        print(f"✅ Returning {len(result)} regions")
        return result
        
    except Exception as e:
        print(f"❌ Error in get_regions: {e}")
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
    db: Session = Depends(get_db)
):
    """CREATE new region"""
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")
        
        new_region = models.Region(
            name=name.strip(),
            capital=capital.strip(),
            population=population.strip(),
            terrain=terrain.strip(),
            description=description.strip(),
            overview=overview.strip() or description.strip(),
            category=category.strip(),
            tags=tags.strip(),
            hero_image=hero_image.strip(),
            gallery_images=gallery_images.strip(),
            audio_files=audio_files.strip(),
            source=source.strip()
        )
        
        db.add(new_region)
        db.commit()
        db.refresh(new_region)
        
        print(f"✅ Created region ID: {new_region.id} - {new_region.name}")
        return {"success": True, "region_id": new_region.id, "message": "Created successfully!"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/regions/{region_id}")
def update_region(
    region_id: int,
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
    db: Session = Depends(get_db)
):
    """UPDATE existing region"""
    try:
        region = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Not found")
        
        if name is not None and name.strip():
            region.name = name.strip()
        if capital is not None:
            region.capital = capital.strip()
        if population is not None:
            region.population = population.strip()
        if terrain is not None:
            region.terrain = terrain.strip()
        if description is not None:
            region.description = description.strip()
        if overview is not None and overview.strip():
            region.overview = overview.strip()
        if category is not None:
            region.category = category.strip()
        if tags is not None:
            region.tags = tags.strip()
        if hero_image is not None:
            region.hero_image = hero_image.strip()
        if gallery_images is not None:
            region.gallery_images = gallery_images.strip()
        if audio_files is not None:
            region.audio_files = audio_files.strip()
        if source is not None:
            region.source = source.strip()
        
        db.commit()
        db.refresh(region)
        
        print(f"✅ Updated region: {region.id} - {region.name}")
        return {"success": True, "message": "Updated successfully!"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error updating region: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    """DELETE region"""
    try:
        region = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Not found")
        
        db.delete(region)
        db.commit()
        
        print(f"🗑️ Deleted region: {region_id}")
        return {"success": True, "message": "Deleted successfully!"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting region: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FILE UPLOAD ROUTES
# ============================================
@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), filename: str = Form(...)):
    """Upload image file"""
    try:
        ext = os.path.splitext(filename)[1] or ".jpg"
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), filename: str = Form(...)):
    """Upload audio file"""
    try:
        ext = os.path.splitext(filename)[1] or ".mp3"
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============================================
# STATS & IMPORT/EXPORT
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get statistics"""
    try:
        total = db.query(models.Region).count()
        
        db_path = "echostack.db"
        size_mb = round(os.path.getsize(db_path) / 1024 / 1024, 2) if os.path.exists(db_path) else 0
        
        return {
            "total_regions": total,
            "with_audio": db.query(models.Region).filter(models.Region.audio_files != "").count(),
            "with_images": db.query(models.Region).filter(models.Region.gallery_images != "").count(),
            "database_size_mb": size_mb
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {"total_regions": 0, "database_size_mb": 0}

# ⚠️⚠️⚠️ THIS IS THE BROKEN FUNCTION - NOW FIXED! ⚠️⚠️⚠️
@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    """Import regions from JSON"""
    try:
        # If single object, make it a list
        if not isinstance(data, list):
            data = [data]
        
        imported = 0
        for region_data in data:  # ⚠️ FIXED: was missing 'data:'
            try:
                new_region = models.Region(**region_data)
                db.add(new_region)
                imported += 1
            except Exception as e:
                print(f"Failed to import region: {e}")
                continue
        
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# UNIVERSAL FILE UPLOAD (Any File Type!)
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(...),
    category: str = Form("general"),  # video, audio, image, document, other
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    """Upload ANY file type (MP4, PDF, DOCX, JPG, MP3, etc.)"""
    try:
        ext = os.path.splitext(filename)[1] or ".bin"
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name,
            "category": category,
            "size_bytes": len(content),
            "mime_type": file.content_type or "application/octet-stream",
            "description": description
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============================================
# DYNAMIC SECTIONS/CATEGORIES MANAGER
# ============================================
class Section(Base):
    __tablename__ = "sections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

@app.post("/api/sections")
def create_section(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    import re
    slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
    
    new_section = Section(name=name, slug=slug, description=description)
    db.add(new_section)
    db.commit()
    db.refresh(new_section)
    return {"success": True, "section_id": new_section.id}

@app.get("/api/sections")
def get_sections(db: Session = Depends(get_db)):
    sections = db.query(Section).all()
    return [{"id": s.id, "name": s.name, "slug": s.slug, "description": s.description} for s in sections]

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    section = db.query(Section).filter(Section.id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(section)
    db.commit()
    return {"success": True}
