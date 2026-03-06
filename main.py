from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json
import re
import hashlib

from database import engine, get_db, Base
import models

# This line tells the database to create any missing tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# CONFIGURATION
# ============================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder: {e}")

CORRECT_ANSWER = "THE ADMIN"

# ============================================
# PASSWORD HELPERS
# ============================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

# ============================================
# STATIC PAGES (The HTML files)
# ============================================
@app.get("/")
def homepage():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/app")
async def app_page(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/user-login")
    if os.path.exists("app.html"):
        return FileResponse("app.html")
    raise HTTPException(status_code=404)

@app.get("/signup")
def signup_page():
    if os.path.exists("signup.html"):
        return FileResponse("signup.html")
    raise HTTPException(status_code=404)

@app.get("/user-login")
def user_login_page():
    if os.path.exists("user-login.html"):
        return FileResponse("user-login.html")
    raise HTTPException(status_code=404)

@app.get("/login")
def admin_login_page():
    if os.path.exists("login.html"):
        return FileResponse("login.html")
    raise HTTPException(status_code=404)

@app.get("/admin")
async def admin_dashboard_page(request: Request):
    token = request.cookies.get("admin_session")
    if not token or token != "ADMIN_AUTHORIZED":
        if os.path.exists("login.html"):
            return FileResponse("login.html")
        raise HTTPException(status_code=404)
    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")
    raise HTTPException(status_code=404)

@app.get("/echostack-logo.png")
def serve_logo():
    if os.path.exists("echostack-logo.png"):
        return FileResponse("echostack-logo.png", media_type="image/png")
    raise HTTPException(status_code=404)

@app.get("/sw.js")
def serve_sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404)

# ============================================
# ADMIN AUTHENTICATION
# ============================================
@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    cleaned = CORRECT_ANSWER.lower().replace(" ", "")
    given = answer.strip().lower().replace(" ", "")
    if cleaned == given:
        response = JSONResponse(content={"success": True})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED", max_age=86400, path="/")
        return response
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="admin_session", path="/")
    return response

# ============================================
# USER ACCOUNTS (Registration & Login)
# ============================================
@app.post("/api/users/register") 
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    interests: str = Form(""), 
    db: Session = Depends(get_db)
):
    try:
        # Check if email is already used
        existing_email = db.query(models.User).filter(models.User.email == email.lower().strip()).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if username is already taken
        existing_username = db.query(models.User).filter(models.User.username == username.strip()).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
            
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Create the new user object
        new_user = models.User(
            username=username.strip(),
            email=email.lower().strip(),
            password_hash=hash_password(password),
            interests=str(interests).strip() # Ensures interests are saved as text
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Log the user in automatically after signup
        response = JSONResponse(content={"success": True, "user_id": new_user.id, "username": new_user.username})
        response.set_cookie(key="user_session", value=str(new_user.id), max_age=86400*7, path="/")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        # This will show up in your Render Logs if it fails
        print(f"CRITICAL ERROR DURING SIGNUP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.post("/api/users/login")
async def user_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.User).filter(
            (models.User.email == username.lower().strip()) |
            (models.User.username == username.strip())
        ).first()
        
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
            
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
            
        response = JSONResponse(content={"success": True, "user_id": user.id, "username": user.username})
        response.set_cookie(key="user_session", value=str(user.id), max_age=86400*7, path="/")
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.cookies.get("user_session")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "interests": user.interests or ""
    }

# ============================================
# REGIONS DATA
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        regions = db.query(models.Region).all()
        return [{
            "id": r.id, "name": r.name, "capital": r.capital,
            "description": r.description, "category": r.category,
            "hero_image": r.hero_image
        } for r in regions]
    except Exception as e:
        return []

@app.post("/api/regions")
def create_region(
    name: str = Form(...), capital: str = Form(""), description: str = Form(""),
    db: Session = Depends(get_db)
):
    r = models.Region(name=name, capital=capital, description=description)
    db.add(r)
    db.commit()
    return {"success": True}

# ============================================
# FILE UPLOAD SYSTEM
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(...),
    category: str = Form("general"), db: Session = Depends(get_db)
):
    try:
        ext = os.path.splitext(filename)[1].lower()
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        uf = models.UploadedFile(
            filename=safe_name, original_name=filename, 
            file_path=file_path, category=category
        )
        db.add(uf)
        db.commit()
        return {"success": True, "url": f"/uploads/{safe_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SITE STATS
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    return {
        "total_regions": db.query(models.Region).count(),
        "total_users": db.query(models.User).count()
    }
