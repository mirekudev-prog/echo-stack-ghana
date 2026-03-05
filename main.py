from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db, Base
import models

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

@app.get("/")
def read_root():
    return {"message": "Welcome to EchoStack - Ghana's Heritage Archive", "status": "Backend Running!"}

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    # Return data from SQLite database
    regions = db.query(models.Region).all()
    if not regions:
        # Preload sample data on first run
        return [
            {"id": 1, "name": "Ashanti", "overview": "Heart of the Ashanti Kingdom..."},
            {"id": 2, "name": "Eastern", "overview": "Sixth largest region by area..."},
            {"id": 3, "name": "Savannah", "overview": "Ghana's largest region by land..."},
            {"id": 4, "name": "North East", "overview": "Northern Ghana landscapes..."},
        ]
    return regions

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
