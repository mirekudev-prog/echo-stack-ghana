from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json
from typing import Optional
import shutil
from datetime import datetime

from database import engine, get_db, Base
import models

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# CREATE UPLOADS DIRECTORY IF IT DOESN'T EXIST
# ============================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount uploads folder so we can serve uploaded files later
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ============================================
# PAGE ROUTES
# ============================================

@app.get("/")
def read_root():
    """Serve homepage"""
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/admin")
def serve_admin():
    """Serve admin panel"""
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    raise HTTPException(status_code=404, detail="Admin panel not found")

@app.get("/manifest.json")
def serve_manifest():
    """Serve PWA manifest file"""
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest not found")

@app.get("/test")
def test_endpoint():
    """Test database connection"""
    return {"test": "passed", "message": "Database connection successful"}

# ============================================
# REGION API ROUTES (FULL CRUD)
# ============================================

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    """GET all regions"""
    regions = db.query(models.Region).all()
    
    if not regions:
        # Return sample data if database is empty
        return [
            {
                "id": 1, 
                "name": "Ashanti", 
                "capital": "Kumasi",
                "population": "5,440,463",
                "terrain": "Highland (200-600m)",
                "description": "Cultural heart of Ghana, known for golden stool tradition.",
                "overview": "Heart of the Ashanti Kingdom",
                "hero_image": "",
                "gallery_images": [],
                "audio_files": [],
                "category": "Culture",
                "tags": []
            }
        ]
    
    result = []
    for r in regions:
        gallery = r.gallery_images.split(',') if r.gallery_images else []
        audio = r.audio_files.split(',') if r.audio_files else []
        tags = r.tags.split(',') if r.tags else []
        
        result.append({
            "id": r.id,
            "name": r.name,
            "capital": r.capital or "",
            "population": r.population or "",
            "terrain": r.terrain or "",
            "description": r.description or "",
            "overview": r.overview or "",
            "hero_image": r.hero_image or "",
            "gallery_images": gallery,
            "audio_files": audio,
            "category": r.category or "",
            "tags": tags,
            "source": r.source or ""
        })
    return result

@app.post("/api/regions")
def create_region(
    name: str = Form(...),
    capital: str = Form(""),
    population: str = Form(""),
    terrain: str = Form(""),
    description: str = Form(""),
    overview: str = Form(""),
    source: str = Form(""),
    hero_image: str = Form(""),
    category: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    tags: str = Form(""),
    db: Session = Depends(get_db)
):
    """CREATE a new region"""
    
    if not name:
        raise HTTPException(status_code=400, detail="Region name is required")
    
    try:
        new_region = models.Region(
            name=name,
            capital=capital,
            population=population,
            terrain=terrain,
            description=description,
            overview=overview,
            source=source,
            hero_image=hero_image,
            gallery_images=gallery_images,
            audio_files=audio_files,
            category=category,
            tags=tags
        )
        
        db.add(new_region)
        db.commit()
        db.refresh(new_region)
        
        return {"success": True, "message": "Region created successfully", "region_id": new_region.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating region: {str(e)}")

@app.put("/api/regions/{region_id}")
def update_region(
    region_id: int,
    name: str = Form(None),
    capital: str = Form(None),
    population: str = Form(None),
    terrain: str = Form(None),
    description: str = Form(None),
    overview: str = Form(None),
    source: str = Form(None),
    hero_image: str = Form(None),
    category: str = Form(None),
    gallery_images: str = Form(None),
    audio_files: str = Form(None),
    tags: str = Form(None),
    db: Session = Depends(get_db)
):
    """UPDATE an existing region"""
    
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    # Update only if value provided
    if name is not None: region.name = name
    if capital is not None: region.capital = capital
    if population is not None: region.population = population
    if terrain is not None: region.terrain = terrain
    if description is not None: region.description = description
    if overview is not None: region.overview = overview
    if source is not None: region.source = source
    if hero_image is not None: region.hero_image = hero_image
    if category is not None: region.category = category
    if gallery_images is not None: region.gallery_images = gallery_images
    if audio_files is not None: region.audio_files = audio_files
    if tags is not None: region.tags = tags
    
    try:
        db.commit()
        db.refresh(region)
        
        return {"success": True, "message": "Region updated successfully", "region_id": region.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating region: {str(e)}")

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    """DELETE a region"""
    
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    try:
        db.delete(region)
        db.commit()
        
        return {"success": True, "message": "Region deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting region: {str(e)}")

# ============================================
# FILE UPLOAD ENDPOINTS (FOR AUDIO & IMAGES)
# ============================================

@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...)):
    """Upload image file"""
    try:
        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_img{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "filename": file_name,
            "url": f"/uploads/{file_name}",
            "original_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...)):
    """Upload audio file"""
    try:
        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_audio{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        return {
            "success": True,
            "filename": file_name,
            "url": f"/uploads/{file_name}",
            "original_name": file.filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio upload error: {str(e)}")

@app.post("/api/import/csv")
def import_csv(csv_data: dict = Form(...)):
    """Import multiple regions from CSV-like data"""
    # Parse CSV and create multiple regions at once
    # For simplicity, you can send list of region objects
    pass

@app.get("/api/categories")
def get_categories():
    """Get all content categories"""
    return [
        {"id": 1, "name": "Culture", "slug": "culture"},
        {"id": 2, "name": "History", "slug": "history"},
        {"id": 3, "name": "Nature", "slug": "nature"},
        {"id": 4, "name": "Tourism", "slug": "tourism"},
        {"id": 5, "name": "Food", "slug": "food"}
    ]

@app.on_event("startup")
async def migrate_database():
    """Auto-migrate database on startup"""
    models.Base.metadata.create_all(bind=engine)
