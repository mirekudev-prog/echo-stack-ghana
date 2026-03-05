from fastapi import FastAPI, Depends, HTTPException, Form, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json

from database import engine, get_db, Base
import models

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# SETUP FOLDERS FOR UPLOADS
# ============================================
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder")

# ============================================
# SECURITY SETTINGS
# ============================================
CORRECT_ANSWER = "THE ADMIN"

# ============================================
# PUBLIC ROUTES
# ============================================
@app.get("/")
def homepage():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "Welcome to EchoStack"}

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "backend": "working"}

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404)

# ============================================
# LOGIN SYSTEM - FIXED REQUEST TYPE
# ============================================
@app.get("/admin")
async def admin_page(request: Request):
    """Serve admin dashboard"""
    token = request.cookies.get("admin_session")
    
    if not token or token != "ADMIN_AUTHORIZED":
        if os.path.exists("login.html"):
            return FileResponse("login.html")
        raise HTTPException(status_code=404)
    
    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")
    raise HTTPException(status_code=404)
    
    # Logged in - show dashboard
    if os.path.exists("admin_dashboard.html"):
        return FileResponse("admin_dashboard.html")
    raise HTTPException(status_code=404, detail="Dashboard not found")

@app.post("/api/auth/login")
async def login(request: Request):
    """Check security answer"""
    # SECURITY ANSWER - TYPE EXACTLY THIS: THE ADMIN
    CORRECT_ANSWER = "THE ADMIN"
    
    form_data = await request.form()
    answer = form_data.get('answer', '').strip().upper()
    
    print(f"Login attempt: Answer = '{answer}'")  # Debug log
    
    if answer == CORRECT_ANSWER:
        response = JSONResponse(content={"success": True, "token": "ADMIN_AUTHORIZED"})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED", max_age=86400, path="/")
        print("✅ Login SUCCESS!")
        return response
    
    print("❌ Login FAILED!")
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
async def logout():
    """Clear session cookie"""
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="admin_session", path="/")
    return response

# ============================================
# REGION CRUD OPERATIONS
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    """GET all regions"""
    try:
        regions = db.query(models.Region).order_by(models.Region.id.desc()).all()
        result = []
        for r in regions:
            result.append({
                "id": r.id,
                "name": r.name or "",
                "capital": r.capital or "",
                "population": r.population or "",
                "terrain": r.terrain or "",
                "description": r.description or "",
                "overview": r.overview or "",
                "category": r.category or "",
                "tags": r.tags.split(",") if r.tags else [],
                "hero_image": r.hero_image or "",
                "gallery_images": r.gallery_images.split(",") if r.gallery_images else [],
                "audio_files": r.audio_files.split(",") if r.audio_files else [],
                "source": r.source or ""
            })
        return result
    except Exception as e:
        print(f"Error fetching regions: {e}")
        return []

@app.post("/api/regions")
async def create_region(request: Request, db: Session = Depends(get_db)):
    """CREATE new region"""
    try:
        form_data = await request.form()
        name = form_data.get('name', '').strip()
        
        if not name:
            raise HTTPException(status_code=400, detail="Region name required")
        
        new_region = models.Region(
            name=name,
            capital=form_data.get('capital', '').strip(),
            population=form_data.get('population', '').strip(),
            terrain=form_data.get('terrain', '').strip(),
            description=form_data.get('description', '').strip(),
            overview=form_data.get('overview', '').strip() or form_data.get('description', '').strip(),
            category=form_data.get('category', '').strip(),
            tags=form_data.get('tags', '').strip(),
            hero_image=form_data.get('hero_image', '').strip(),
            gallery_images=form_data.get('gallery_images', '').strip(),
            audio_files=form_data.get('audio_files', '').strip(),
            source=form_data.get('source', '').strip()
        )
        
        db.add(new_region)
        db.commit()
        db.refresh(new_region)
        
        return {"success": True, "region_id": new_region.id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error creating region: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/regions/{region_id}")
async def update_region(region_id: int, request: Request, db: Session = Depends(get_db)):
    """UPDATE existing region"""
    try:
        region = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Not found")
        
        form_data = await request.form()
        
        if form_data.get('name'): region.name = form_data['name'].strip()
        if form_data.get('capital'): region.capital = form_data['capital'].strip()
        if form_data.get('population'): region.population = form_data['population'].strip()
        if form_data.get('terrain'): region.terrain = form_data['terrain'].strip()
        if form_data.get('description'): region.description = form_data['description'].strip()
        if form_data.get('overview'): region.overview = form_data['overview'].strip()
        if form_data.get('category'): region.category = form_data['category'].strip()
        if form_data.get('tags'): region.tags = form_data['tags'].strip()
        if form_data.get('hero_image'): region.hero_image = form_data['hero_image'].strip()
        if form_data.get('gallery_images'): region.gallery_images = form_data['gallery_images'].strip()
        if form_data.get('audio_files'): region.audio_files = form_data['audio_files'].strip()
        if form_data.get('source'): region.source = form_data['source'].strip()
        
        db.commit()
        db.refresh(region)
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error updating region: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    """DELETE region"""
    try:
        region = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Not found")
        
        db.delete(region)
        db.commit()
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error deleting region: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FILE UPLOAD ROUTES
# ============================================
@app.post("/api/upload/image")
async def upload_image(file: UploadFile = File(...), filename: str = Form(...)):
    """Upload image file"""
    try:
        ext = os.path.splitext(filename)[1] or ".jpg"
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/upload/audio")
async def upload_audio(file: UploadFile = File(...), filename: str = Form(...)):
    """Upload audio file"""
    try:
        ext = os.path.splitext(filename)[1] or ".mp3"
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        return {
            "success": True,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

# ============================================
# STATS & IMPORT/EXPORT
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get statistics"""
    total = db.query(models.Region).count()
    size_mb = round(os.path.getsize("echostack.db") / 1024 / 1024, 2) if os.path.exists("echostack.db") else 0
    
    return {
        "total_regions": total,
        "with_audio": db.query(models.Region).filter(models.Region.audio_files != "").count(),
        "with_images": db.query(models.Region).filter(models.Region.gallery_images != "").count(),
        "database_size_mb": size_mb
    }

@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    """Import regions from JSON"""
    if not isinstance(data, list):
        data = [data]
    
    imported = 0
    for region_data in data:
        try:
            new_region = models.Region(**region_data)
            db.add(new_region)
            imported += 1
        except:
            continue
    
    db.commit()
    return {"success": True, "imported": imported}
