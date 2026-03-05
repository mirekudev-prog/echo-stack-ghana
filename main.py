from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json

from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# Create uploads directory
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
def read_root():
    return FileResponse("index.html") if os.path.exists("index.html") else {"message": "Welcome"}

@app.get("/admin")
def serve_admin():
    return FileResponse("admin.html") if os.path.exists("admin.html") else None

@app.get("/manifest.json")
def serve_manifest():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404)

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    regions = db.query(models.Region).all()
    result = []
    for r in regions:
        result.append({
            "id": r.id, "name": r.name, "capital": r.capital,
            "population": r.population, "terrain": r.terrain,
            "description": r.description, "overview": r.overview,
            "hero_image": r.hero_image, "category": r.category
        })
    return result

@app.post("/api/regions")
def create_region(name: str = Form(...), capital: str = Form(""), 
                population: str = Form(""), terrain: str = Form(""),
                description: str = Form(""), category: str = Form(""),
                db: Session = Depends(get_db)):
    new_region = models.Region(name=name, capital=capital, population=population,
                              terrain=terrain, description=description, overview=description,
                              category=category)
    db.add(new_region)
    db.commit()
    db.refresh(new_region)
    return {"success": True, "region_id": new_region.id}

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    region = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not region: raise HTTPException(status_code=404)
    db.delete(region)
    db.commit()
    return {"success": True}

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
