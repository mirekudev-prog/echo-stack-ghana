from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json
from datetime import datetime, timedelta
import secrets

from database import engine, get_db, Base
import models

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# SECURITY SETTINGS
# ============================================
SECRET_ANSWER = "university of education, winn"  # Accepts any capitalization
SESSION_SECRET = secrets.token_hex(32)

# Mount static folders
os.makedirs("uploads", exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except:
    pass

@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome"}

@app.get("/admin")
def serve_admin(request: Request):
    # Check for admin session cookie
    session_token = request.cookies.get("admin_session")
    if not session_token:
        return FileResponse("login.html")
    if session_token != SESSION_SECRET:
        return FileResponse("login.html")
    return FileResponse("admin.html")

@app.post("/api/auth/login")
def admin_login(answer: str = Form(...)):
    """Check if answer matches security question"""
    if SECRET_ANSWER.lower() in answer.lower().replace(" ", "").lower():
        return {
            "success": True, 
            "token": SESSION_SECRET,
            "message": "Login successful!"
        }
    raise HTTPException(status_code=403, detail="Incorrect answer to security question")

@app.post("/api/auth/logout")
def admin_logout():
    return {"success": True, "message": "Logged out"}

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
            "source": r.source,
            "created_at": str(r.created_at),
            "updated_at": str(r.updated_at)
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
    if not name:
        raise HTTPException(status_code=400, detail="Region name required")
    
    try:
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
    except Exception as e:
        db.rollback()
        print(f"Error creating region: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=404, detail="Region not found")
    
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

@app.post("/api/upload/image")
async def upload_image(file: bytes = Form(...), filename: str = Form(...)):
    file_ext = os.path.splitext(filename)[1]
    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join("uploads", safe_name)
    with open(file_path, "wb") as buffer:
        buffer.write(file)
    return {"success": True, "url": f"/uploads/{safe_name}", "filename": safe_name}

@app.post("/api/upload/audio")
async def upload_audio(file: bytes = Form(...), filename: str = Form(...)):
    file_ext = os.path.splitext(filename)[1]
    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join("uploads", safe_name)
    with open(file_path, "wb") as buffer:
        buffer.write(file)
    return {"success": True, "url": f"/uploads/{safe_name}", "filename": safe_name}

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
