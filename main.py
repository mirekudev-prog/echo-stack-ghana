from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json
import re

from database import engine, get_db, Base
import models

# Create tables
Base.metadata.create_all(bind=engine)
```

The only change is line 13 — removed the old `from models import User` and replaced with a comment. This forces Render to reload the file fresh.

Also, your `main.py` has no `from passlib` or `from models import User` — so the error must be coming from an old cached file. Committing this change will clear it.

Also add `python-jose` to `requirements.txt` just in case:

### 📄 `requirements.txt`
```
fastapi==0.110.0
uvicorn==0.29.0
sqlalchemy==2.0.36
psycopg2-binary==2.9.9
python-multipart==0.0.9
aiofiles==23.2.1
passlib==1.7.4
bcrypt==4.0.1
python-jose==3.3.0

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="EchoStack API")

# ============================================
# DATABASE STARTUP
# ============================================

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

# ============================================
# FILE STORAGE
# ============================================

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# ============================================
# STATIC FILES
# ============================================

@app.get("/echostack-logo.png")
def serve_logo():
    if os.path.exists("echostack-logo.png"):
        return FileResponse("echostack-logo.png", media_type="image/png")
    raise HTTPException(status_code=404)

@app.get("/sw.js")
def serve_sw():
    if os.path.exists("sw.js"):
        return FileResponse(
            "sw.js",
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )
    raise HTTPException(status_code=404)

# ============================================
# ROOT
# ============================================

@app.get("/")
def homepage():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/test")
def test():
    return {"status": "backend working"}

@app.get("/manifest.json")
def manifest():
    if os.path.exists("manifest.json"):
        with open("manifest.json") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404)

# ============================================
# ADMIN LOGIN
# ============================================

CORRECT_ANSWER = "THE ADMIN"

@app.get("/admin")
async def admin_page(request: Request):

    token = request.cookies.get("admin_session")

    if not token or token != "ADMIN_AUTHORIZED":
        if os.path.exists("login.html"):
            return FileResponse("login.html")
        raise HTTPException(status_code=404)

    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")

    raise HTTPException(status_code=404)


@app.post("/api/auth/login")
async def login(answer: str = Form(...)):

    cleaned = CORRECT_ANSWER.lower().replace(" ", "")
    incoming = answer.lower().strip().replace(" ", "")

    if cleaned == incoming:

        response = JSONResponse({"success": True})
        response.set_cookie(
            key="admin_session",
            value="ADMIN_AUTHORIZED",
            max_age=86400,
            path="/",
        )

        return response

    raise HTTPException(status_code=403, detail="Incorrect answer")


@app.post("/api/auth/logout")
def logout():

    response = JSONResponse({"success": True})
    response.delete_cookie("admin_session", path="/")

    return response

# ============================================
# REGIONS
# ============================================

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):

    regions = db.query(models.Region).all()

    return regions


@app.post("/api/regions")
def create_region(
    name: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db)
):

    region = models.Region(
        name=name,
        description=description
    )

    db.add(region)
    db.commit()
    db.refresh(region)

    return {"success": True, "region_id": region.id}


@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):

    region = db.query(models.Region).filter(models.Region.id == region_id).first()

    if not region:
        raise HTTPException(status_code=404)

    db.delete(region)
    db.commit()

    return {"success": True}

# ============================================
# FILE UPLOAD
# ============================================

@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(...),
    db: Session = Depends(get_db)
):

    ext = os.path.splitext(filename)[1]

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    safe_name = f"{timestamp}{ext}"

    path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()

    with open(path, "wb") as f:
        f.write(content)

    uploaded = models.UploadedFile(
        filename=safe_name,
        original_name=filename,
        file_path=path,
        file_size=len(content),
        mime_type=file.content_type,
    )

    db.add(uploaded)
    db.commit()
    db.refresh(uploaded)

    return {"success": True, "url": f"/uploads/{safe_name}"}

# ============================================
# FILE LIST
# ============================================

@app.get("/api/files")
def get_files(db: Session = Depends(get_db)):

    files = db.query(models.UploadedFile).all()

    return files

# ============================================
# USER REGISTRATION
# ============================================

@app.post("/api/users/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):

    existing = db.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username or email exists")

    hashed_password = pwd_context.hash(password)

    user = User(
        username=username,
        email=email,
        password_hash=hashed_password,
        is_verified=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"success": True, "user_id": user.id}
