from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
import json

from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

@app.get("/")
def read_root():
    return FileResponse("index.html")

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
        return [
            {"id": 1, "name": "Ashanti", "overview": "Heart of the Ashanti Kingdom"},
            {"id": 2, "name": "Eastern", "overview": "Mountainous terrain and dams"},
            {"id": 3, "name": "Volta", "overview": "Lake Volta and mountains"},
            {"id": 4, "name": "Greater Accra", "overview": "Capital region"},
        ]
    return [{"id": r.id, "name": r.name, "overview": r.overview} for r in regions]

@app.post("/api/regions")
def create_region(name: str, overview: str, source: str = "", db: Session = Depends(get_db)):
    new_region = models.Region(name=name, overview=overview, source=source)
    db.add(new_region)
    db.commit()
    db.refresh(new_region)
    return new_region

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
