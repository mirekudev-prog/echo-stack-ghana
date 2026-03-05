from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime

from database import engine, get_db, Base
import models

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# Mount uploads folder
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except:
    pass

@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/admin")
def serve_admin():
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    raise HTTPException(status_code=404, detail="Admin panel not found")

@app.get("/manifest.json")
def serve_manifest():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404, detail="Manifest not found")

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    regions = db.query(models.Region).all()
    
    if not regions:
        return [{"id": 1, "name": "Ashanti", "capital": "Kumasi", "description": "Cultural heart of Ghana"}]
    
    result = []
    for r in regions:
        result.append({
            "id": r.id,
            "name": r.name,
            "capital": r.capital or "",
            "population": r.population or "",
            "terrain": r.terrain or "",
            "description": r.description or "",
            "overview": r.overview or "",
            "hero_image": r.hero_image or "",
            "gallery_images": r.gallery_images.split(',') if r.gallery_images else [],
            "audio_files": r.audio_files.split(',') if r.audio_files else [],
            "category": r.category or "",
            "tags": r.tags.split(',') if r.tags else [],
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
    category: str = Form(""),
    tags: str = Form(""),
    hero_image: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    db: Session = Depends(get_db)
):
    new_region = models.Region(
        name=name,
        capital=capital,
        population=population,
        terrain=terrain,
        description=description,
        overview=description,
        category=category,
        tags=tags,
        hero_image=hero_image,
        gallery_images=gallery_images,
        audio_files=audio_files
    )
    db.add(new_region)
    db.commit()
    db.refresh(new_region)
    return {"success": True, "region_id": new_region.id}

@app.put("/api/regions/{region_id}")
def update_region(region_id: int, **kwargs, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    for key, value in kwargs.items():
        if hasattr(region, key):
            setattr(region, key, value)
    
    db.commit()
    db.refresh(region)
    return {"success": True}

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    db.delete(region)
    db.commit()
    return {"success": True}

@app.post("/api/upload/image")
async def upload_image(file: bytes = Form(...)):
    # Simplified upload - just return placeholder URL
    return {"success": True, "url": "/uploads/sample.jpg"}

@app.post("/api/upload/audio")
async def upload_audio(file: bytes = Form(...)):
    return {"success": True, "url": "/uploads/sample.mp3"}

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
