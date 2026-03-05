from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json

from database import engine, get_db, Base
import models

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# Mount folders
os.makedirs("uploads", exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads: {e}")

@app.get("/")
def read_root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome"}

@app.get("/admin")
def serve_admin():
    if os.path.exists("login.html"):
        return FileResponse("login.html")
    raise HTTPException(status_code=404, detail="Login page not found")

@app.post("/api/auth/login")
def admin_login(answer: str = Form(...)):
    SECRET_ANSWER = "university of education winn"
    if SECRET_ANSWER.lower() in answer.lower().replace(" ", ""):
        return {"success": True, "token": "authenticated_token_here", "message": "Login successful!"}
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    regions = db.query(models.Region).all()
    result = []
    for r in regions:
        result.append({
            "id": r.id,
            "name": r.name,
            "capital": r.capital,
            "description": r.description,
            "category": r.category,
            "tags": r.tags.split(",") if r.tags else [],
            "hero_image": r.hero_image,
            "gallery_images": r.gallery_images.split(",") if r.gallery_images else [],
            "audio_files": r.audio_files.split(",") if r.audio_files else [],
            "population": r.population,
            "terrain": r.terrain,
            "overview": r.overview,
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
def update_region(region_id: int, form_data: dict = Form(...), db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404, detail="Not found")
    
    for key, value in form_data.items():
        if hasattr(region, key):
            setattr(region, key, value)
    
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
    from datetime import datetime
    file_ext = os.path.splitext(filename)[1]
    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join("uploads", safe_name)
    with open(file_path, "wb") as buffer:
        buffer.write(file)
    return {"success": True, "url": f"/uploads/{safe_name}", "filename": safe_name}

@app.post("/api/upload/audio")
async def upload_audio(file: bytes = Form(...), filename: str = Form(...)):
    from datetime import datetime
    file_ext = os.path.splitext(filename)[1]
    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join("uploads", safe_name)
    with open(file_path, "wb") as buffer:
        buffer.write(file)
    return {"success": True, "url": f"/uploads/{safe_name}", "filename": safe_name}

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
