from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime

from database import engine, get_db, Base
import models

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# MOUNT STATIC FOLDERS (Images & Files)
# ============================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder: {e}")

# ============================================
# SECURITY SETTINGS (Who Can Access Admin?)
# ============================================
SECRET_ANSWER = "THE ADMIN"

# ============================================
# PUBLIC ROUTES (Everyone Can Visit)
# ============================================
@app.get("/")
def homepage():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "message": "Backend is working!"}

# ============================================
# LOGIN ROUTES (Security Check)
# ============================================
@app.get("/admin")
def admin_login_page(request: Request):
    """Show login page if not authenticated"""
    session_token = request.cookies.get("admin_session")
    if not session_token or session_token != "ADMIN_AUTHORIZED":
        return FileResponse("login.html")
    # If logged in, show actual admin dashboard
    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")
    raise HTTPException(status_code=404, detail="Admin dashboard not found")

@app.post("/api/auth/login")
def login(answer: str = Form(...)):
    """Check if secret answer is correct"""
    if SECRET_ANSWER.lower() in answer.lower().replace(" ", ""):
        return {"success": True, "token": "ADMIN_AUTHORIZED", "message": "Login successful!"}
    raise HTTPException(status_code=403, detail="Incorrect answer to security question")

@app.post("/api/auth/logout")
def logout():
    return {"success": True, "message": "Logged out successfully"}

# ============================================
# REGION MANAGEMENT (Full CRUD Operations)
# ============================================
@app.get("/api/regions")
def get_all_regions(db: Session = Depends(get_db)):
    """GET all regions from database"""
    regions = db.query(models.Region).all()
    result = []
    for r in regions:
        result.append({
            "id": r.id,
            "name": r.name,
            "capital": r.capital,
            "population": r.population,
            "terrain": r.terrain,
            "description": r.description,
            "overview": r.overview,
            "category": r.category,
            "tags": r.tags.split(",") if r.tags else [],
            "hero_image": r.hero_image,
            "gallery_images": r.gallery_images.split(",") if r.gallery_images else [],
            "audio_files": r.audio_files.split(",") if r.audio_files else [],
            "source": r.source,
            "created_at": str(r.created_at),
            "updated_at": str(r.updated_at)
        })
    return result

@app.post("/api/regions")
def create_new_region(
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
    if not name:
        raise HTTPException(status_code=400, detail="Region name is required")
    
    try:
        new_region = models.Region(
            name=name,
            capital=capital,
            population=population,
            terrain=terrain,
            description=description,
            overview=overview if overview else description,
            category=category,
            tags=tags,
            hero_image=hero_image,
            gallery_images=gallery_images,
            audio_files=audio_files,
            source=source
        )
        db.add(new_region)
        db.commit()
        db.refresh(new_region)
        return {"success": True, "region_id": new_region.id, "message": "Region created successfully!"}
    except Exception as e:
        db.rollback()
        print(f"Error creating region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.put("/api/regions/{region_id}")
def update_existing_region(
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
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    # Only update fields that were provided
    if name: region.name = name
    if capital: region.capital = capital
    if population: region.population = population
    if terrain: region.terrain = terrain
    if description: region.description = description
    if overview: region.overview = overview
    if category: region.category = category
    if tags: region.tags = tags
    if hero_image: region.hero_image = hero_image
    if gallery_images: region.gallery_images = gallery_images
    if audio_files: region.audio_files = audio_files
    if source: region.source = source
    
    try:
        db.commit()
        db.refresh(region)
        return {"success": True, "message": "Region updated successfully!"}
    except Exception as e:
        db.rollback()
        print(f"Error updating region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    """DELETE region completely"""
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    try:
        db.delete(region)
        db.commit()
        return {"success": True, "message": "Region deleted successfully!"}
    except Exception as e:
        db.rollback()
        print(f"Error deleting region: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ============================================
# FILE UPLOAD ROUTES (Images & Audio)
# ============================================
@app.post("/api/upload/image")
async def upload_image_file(file: UploadFile = File(...)):
    """Upload image file"""
    try:
        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "success": True, 
            "url": f"/uploads/{safe_filename}", 
            "filename": safe_filename,
            "original_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@app.post("/api/upload/audio")
async def upload_audio_file(file: UploadFile = File(...)):
    """Upload audio file (MP3, WAV, etc.)"""
    try:
        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_filename}",
            "filename": safe_filename,
            "original_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio upload error: {str(e)}")

@app.post("/api/upload/file")
async def upload_generic_file(file: UploadFile = File(...)):
    """Upload any type of file"""
    try:
        file_ext = os.path.splitext(file.filename)[1]
        safe_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_filename}",
            "filename": safe_filename,
            "type": file.content_type or "application/octet-stream"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload error: {str(e)}")

# ============================================
# DATA IMPORT/EXPORT (Backup & Restore)
# ============================================
@app.post("/api/export/json")
def export_data_as_json(db: Session = Depends(get_db)):
    """Export all regions as JSON file"""
    regions = db.query(models.Region).all()
    data = []
    for r in regions:
        data.append({
            "name": r.name,
            "capital": r.capital,
            "population": r.population,
            "terrain": r.terrain,
            "description": r.description,
            "category": r.category,
            "tags": r.tags,
            "hero_image": r.hero_image,
            "gallery_images": r.gallery_images,
            "audio_files": r.audio_files,
            "source": r.source
        })
    return JSONResponse(content=data)

@app.post("/api/import/json")
def import_data_from_json(data: dict, db: Session = Depends(get_db)):
    """Import regions from JSON data"""
    if not isinstance(data, list):
        raise HTTPException(status_code=400, detail="Data must be an array of regions")
    
    imported_count = 0
    for region_data in data:
        try:
            new_region = models.Region(**region_data)
            db.add(new_region)
            imported_count += 1
        except Exception as e:
            print(f"Failed to import region: {str(e)}")
            continue
    
    db.commit()
    return {"success": True, "imported": imported_count, "message": f"Successfully imported {imported_count} regions"}

# ============================================
# CATEGORY MANAGEMENT
# ============================================
@app.get("/api/categories")
def get_categories():
    """Return available content categories"""
    return [
        {"id": 1, "name": "Culture", "slug": "culture"},
        {"id": 2, "name": "History", "slug": "history"},
        {"id": 3, "name": "Nature", "slug": "nature"},
        {"id": 4, "name": "Tourism", "slug": "tourism"},
        {"id": 5, "name": "Food", "slug": "food"},
        {"id": 6, "name": "Music", "slug": "music"},
        {"id": 7, "name": "Art", "slug": "art"},
        {"id": 8, "name": "Religion", "slug": "religion"}
    ]

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get archive statistics"""
    total_regions = db.query(models.Region).count()
    regions_with_audio = db.query(models.Region).filter(models.Region.audio_files != "").count()
    regions_with_images = db.query(models.Region).filter(models.Region.gallery_images != "").count()
    
    return {
        "total_regions": total_regions,
        "with_audio": regions_with_audio,
        "with_images": regions_with_images,
        "database_size_mb": round(os.path.getsize("echostack.db") / 1024 / 1024, 2) if os.path.exists("echostack.db") else 0
    }
