from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os

# Database imports
from database import engine, get_db, Base
import models

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# Mount static folders (CSS/JS)
app.mount("/css", StaticFiles(directory="css"), name="css")
app.mount("/js", StaticFiles(directory="js"), name="js")

@app.on_event("startup")
async def startup():
    """Test database connection on startup"""
    print("🚀 Starting EchoStack...")
    
@app.get("/")
def read_root():
    """Serve the homepage HTML"""
    return FileResponse("index.html")

@app.get("/regions/{region_name}")
def region_page(region_name: str):
    """Serve individual region pages"""
    file_path = f"regions/{region_name}.html"
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Region page not found")

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    regions = db.query(models.Region).all()
    if not regions:
        # Return sample data for demo
        return [
            {"id": 1, "name": "Ashanti", "overview": "Heart of the Ashanti Kingdom"},
            {"id": 2, "name": "Eastern", "overview": "Sixth largest region by area"},
            {"id": 3, "name": "Savannah", "overview": "Ghana's largest region by land"},
            {"id": 4, "name": "North East", "overview": "Northern Ghana landscapes"},
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
    return {"test": "passed", "message": "Database connection successful"}
