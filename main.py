from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import engine, get_db, Base
import models

# Create tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

@app.get("/")
def read_root():
    return {"message": "Welcome to EchoStack - Ghana's Heritage Archive"}

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    return db.query(models.Region).all()

@app.post("/api/regions")
def create_region(name: str, overview: str, source: str, db: Session = Depends(get_db)):
    new_region = models.Region(name=name, overview=overview, source=source)
    db.add(new_region)
    db.commit()
    db.refresh(new_region)
    return new_region
