from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import hashlib
from database import engine, get_db, Base
import models

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack Full API")

# --- Helpers ---
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- Static Pages (Your Frontend) ---
@app.get("/")
def home(): return FileResponse("index.html")

@app.get("/app")
def app_page(): return FileResponse("app.html")

@app.get("/signup")
def signup(): return FileResponse("signup.html")

@app.get("/admin")
def admin(): return FileResponse("admin_dashboard.html")

# --- Authentication & User API ---
@app.post("/api/users/register") 
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    interests: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.email == email.lower().strip()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        username=username.strip(),
        email=email.lower().strip(),
        password_hash=hash_password(password),
        interests=interests
    )
    db.add(new_user)
    db.commit()
    return {"success": True}

# --- Admin & Site Builder API ---
@app.post("/api/admin/login")
async def admin_login(answer: str = Form(...)):
    # Your secret answer logic
    if answer.lower().strip() == "the admin":
        return {"success": True}
    raise HTTPException(status_code=403, detail="Invalid Access")

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    return db.query(models.Region).all()

@app.post("/api/upload/file")
async def upload_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Standard file upload logic
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"success": True, "path": file_path}

@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "users": db.query(models.User).count(),
        "regions": db.query(models.Region).count()
    }
