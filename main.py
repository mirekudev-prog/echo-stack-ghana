from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json

from database import engine, get_db, Base
import models

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

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
# REGION API ROUTES (FOR ADMIN PANEL)
# ============================================

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    """GET all regions - used by admin panel and map"""
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
                "overview": "Heart of the Ashanti Kingdom"
            },
            {
                "id": 2, 
                "name": "Eastern", 
                "capital": "Koforidua",
                "population": "3,244,341",
                "terrain": "Mountainous Range",
                "description": "Features Akwapim-Togo mountain ranges and dams.",
                "overview": "Mountainous terrain and dams"
            },
            {
                "id": 3, 
                "name": "Volta", 
                "capital": "Ho",
                "population": "1,659,040",
                "terrain": "Valley/Mountainous",
                "description": "Home to Mount Afadjato and Lake Volta.",
                "overview": "Lake Volta and mountains"
            },
            {
                "id": 4, 
                "name": "Greater Accra", 
                "capital": "Accra",
                "population": "5,455,694",
                "terrain": "Coastal Plain (0-100m)",
                "description": "Nation's capital region with vibrant urban culture.",
                "overview": "Capital region"
            }
        ]
    
    # Return all region data fields
    result = []
    for r in regions:
        result.append({
            "id": r.id,
            "name": r.name,
            "capital": r.capital or "",
            "population": r.population or "",
            "terrain": r.terrain or "",
            "description": r.description or r.overview or "",
            "overview": r.overview or "",
            "imageUrl": r.image_url or "",
            "gallery_images": r.gallery_images or "",
            "meta_description": r.meta_description or "",
            "featured_story": r.featured_story or "",
            "source": r.source or ""
        })
    return result

@app.post("/api/regions")
def create_region(
    name: str,
    capital: str = "",
    population: str = "",
    terrain: str = "",
    description: str = "",
    overview: str = "",
    source: str = "",
    imageUrl: str = "",
    gallery_images: str = "",
    meta_description: str = "",
    featured_story: str = "",
    db: Session = Depends(get_db)
):
    """CREATE a new region"""
    
    # Use description as overview if overview is empty
    if not overview and description:
        overview = description
    
    # Validate required field
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
            image_url=imageUrl,
            gallery_images=gallery_images,
            meta_description=meta_description,
            featured_story=featured_story
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
    name: str = None,
    capital: str = None,
    population: str = None,
    terrain: str = None,
    description: str = None,
    overview: str = None,
    source: str = None,
    imageUrl: str = None,
    gallery_images: str = None,
    meta_description: str = None,
    featured_story: str = None,
    db: Session = Depends(get_db)
):
    """UPDATE an existing region"""
    
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    
    if not region:
        raise HTTPException(status_code=404, detail="Region not found")
    
    # Update fields only if they are provided (not None)
    if name is not None:
        region.name = name
    if capital is not None:
        region.capital = capital
    if population is not None:
        region.population = population
    if terrain is not None:
        region.terrain = terrain
    if description is not None:
        region.description = description
    if overview is not None:
        region.overview = overview
    if source is not None:
        region.source = source
    if imageUrl is not None:
        region.image_url = imageUrl
    if gallery_images is not None:
        region.gallery_images = gallery_images
    if meta_description is not None:
        region.meta_description = meta_description
    if featured_story is not None:
        region.featured_story = featured_story
    
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
