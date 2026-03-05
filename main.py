from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json
from typing import Optional

from database import engine, get_db, Base
import models

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# Mount static folders
try:
    os.makedirs("uploads", exist_ok=True)
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except:
    pass

@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome"}

@app.get("/admin")
def serve_admin():
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/manifest.json")
def serve_manifest():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404, detail="Not found")

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
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
            "hero_image": r.hero_image,
            "gallery_images": r.gallery_images.split(",") if r.gallery_images else [],
            "audio_files": r.audio_files.split(",") if r.audio_files else [],
            "category": r.category,
            "tags": r.tags.split(",") if r.tags else [],
            "source": r.source
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
    source: str = Form(""),
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
        audio_files=audio_files,
        source=source
    )
    db.add(new_region)
    db.commit()
    db.refresh(new_region)
    return {"success": True, "region_id": new_region.id}

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
    db: Session = Depends(get_db)
):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Not found")
    
    if name: region.name = name
    if capital: region.capital = capital
    if population: region.population = population
    if terrain: region.terrain = terrain
    if description: region.description = description
    if category: region.category = category
    if tags: region.tags = tags
    if hero_image: region.hero_image = hero_image
    if gallery_images: region.gallery_images = gallery_images
    if audio_files: region.audio_files = audio_files
    if source: region.source = source
    
    db.commit()
    db.refresh(region)
    return {"success": True}

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(region)
    db.commit()
    return {"success": True}

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
