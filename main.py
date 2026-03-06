from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
import hashlib
from database import engine, get_db, Base
import models

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# --- Password Helpers ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- Static Routes ---
@app.get("/")
def homepage():
    return FileResponse("index.html")

@app.get("/signup")
def signup_page():
    return FileResponse("signup.html")

# --- Signup Endpoint (Fixed to match your frontend) ---
@app.post("/api/users/register") 
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    interests: str = Form(""),
    db: Session = Depends(get_db)
):
    # Check if user already exists
    existing_user = db.query(models.User).filter(models.User.email == email.lower().strip()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    new_user = models.User(
        username=username.strip(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        interests=interests
    )
    db.add(new_user)
    db.commit()
    return {"success": True, "message": "User created successfully"}

# --- Other Essential Routes ---
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "total_users": db.query(models.User).count(),
        "total_regions": db.query(models.Region).count()
    }
