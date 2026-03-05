from fastapi import FastAPI, Depends, HTTPException, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os

from database import engine, get_db, Base
import models

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Create upload folder
os.makedirs("uploads", exist_ok=True)
try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except:
    pass

# SECURITY ANSWER
CORRECT_ANSWER = "THE ADMIN"

@app.get("/")
def root():
    return FileResponse("index.html")

@app.get("/admin")
def serve_admin(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token != "ADMIN_AUTHORIZED":
        return FileResponse("login.html")
    if os.path.exists("admin.html"):
        return FileResponse("admin.html")
    raise HTTPException(status_code=404)

@app.post("/api/auth/login")
def login(answer: str = Form(...)):
    if answer.strip().upper() == CORRECT_ANSWER:
        return {"success": True, "token": "ADMIN_AUTHORIZED"}
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.get("/api/regions")
def regions(db: Session = Depends(get_db)):
    data = []
    for r in db.query(models.Region).all():
        data.append({
            "id": r.id, 
            "name": r.name, 
            "capital": r.capital,
            "description": r.description, 
            "category": r.category,
            "population": r.population, 
            "terrain": r.terrain,
            "hero_image": r.hero_image, 
            "gallery_images": r.gallery_images.split(",") if r.gallery_images else [],
            "audio_files": r.audio_files.split(",") if r.audio_files else [],
            "tags": r.tags.split(",") if r.tags else [],
            "source": r.source, 
            "overview": r.overview
        })
    return data

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
        raise HTTPException(status_code=404)
    
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
    return {"success": True}

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region:
        raise HTTPException(status_code=404)
    db.delete(region)
    db.commit()
    return {"success": True}

@app.post("/api/upload/image")
async def upload_image(file: bytes = Form(...), filename: str = Form(...)):
    from datetime import datetime
    ext = os.path.splitext(filename)[1]
    safe = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    with open(f"uploads/{safe}", "wb") as f:
        f.write(file)
    return {"success": True, "url": f"/uploads/{safe}"}

@app.post("/api/upload/audio")
async def upload_audio(file: bytes = Form(...), filename: str = Form(...)):
    from datetime import datetime
    ext = os.path.splitext(filename)[1]
    safe = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    with open(f"uploads/{safe}", "wb") as f:
        f.write(file)
    return {"success": True, "url": f"/uploads/{safe}"}

@app.get("/test")
def test():
    return {"status": "ok"}
