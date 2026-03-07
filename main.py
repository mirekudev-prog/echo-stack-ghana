# ✅ ADD Response to the imports
from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os, json, re, hashlib, datetime, hmac, urllib.request
from pathlib import Path
from database import engine, get_db, Base
import models

# Create all database tables (safe - won't error if tables exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

# ============================================
# CONFIGURATION
# ============================================
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder: {e}")

# Admin secret answer (case-insensitive)
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "THE ADMIN")

# Paystack & AI tokens (from environment)
PAYSTACK_SECRET = os.environ.get("PAYSTACK_SECRET_KEY", "")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# ============================================
# HELPERS
# ============================================
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def get_user_from_request(request: Request, db: Session):
    """Get current user from session cookie."""
    user_id = request.cookies.get("user_session")
    if not user_id:
        return None
    try:
        return db.query(models.User).filter(models.User.id == int(user_id)).first()
    except:
        return None

def require_admin(request: Request):
    """Check if request has valid admin session."""
    token = request.cookies.get("admin_session")
    if not token or token != "ADMIN_AUTHORIZED":
        raise HTTPException(status_code=403, detail="Not authorized")

# ============================================
# STATIC PAGES
# ============================================
def serve_file(filename: str):
    if os.path.exists(filename):
        return FileResponse(filename)
    raise HTTPException(status_code=404, detail=f"{filename} not found")

@app.get("/")
def homepage(): return serve_file("index.html")

@app.get("/signup")
def signup_page(): return serve_file("signup.html")

@app.get("/user-login")
def user_login_page(): return serve_file("user-login.html")

@app.get("/dashboard")
async def dashboard_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("dashboard.html")

@app.get("/creator")
async def creator_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("creator.html")

@app.get("/post/{post_id}")
async def post_page(post_id: int, request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("post.html")

@app.get("/app")
async def app_page(request: Request):
    if not request.cookies.get("user_session"):
        return RedirectResponse(url="/user-login")
    return serve_file("app.html")

@app.get("/admin")
async def admin_page(request: Request):
    if not request.cookies.get("admin_session") == "ADMIN_AUTHORIZED":
        return serve_file("login.html")
    return serve_file("admin_dashboard.html")

@app.get("/client-login")
def client_login_page(): return serve_file("client_login.html")

@app.get("/client-dashboard")
async def client_dashboard_page(request: Request):
    if not request.cookies.get("client_session"):
        return RedirectResponse(url="/client-login")
    return serve_file("client_dashboard.html")

@app.get("/test")
def test_endpoint(): return {"status": "ok", "backend": "working"}

@app.get("/echostack-logo.png")
def serve_logo(): return serve_file("echostack-logo.png")

@app.get("/sw.js")
def serve_sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript",
                          headers={"Service-Worker-Allowed": "/"})
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            return JSONResponse(content=json.load(f))
    raise HTTPException(status_code=404)

# ============================================
# ADMIN AUTHENTICATION (Secret Answer Login)
# ============================================
@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    """Admin login with secret answer - case insensitive"""
    cleaned = ADMIN_SECRET.lower().replace(" ", "")
    given = answer.strip().lower().replace(" ", "")
    
    if cleaned == given:
        response = JSONResponse(content={"success": True})
        response.set_cookie(
            key="admin_session",
            value="ADMIN_AUTHORIZED",
            max_age=86400,  # 24 hours
            path="/",
            httponly=False
        )
        return response
    
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout(response: Response):
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(key="admin_session", path="/")
    return resp

# ============================================
# USER ACCOUNTS (es_users table)
# ============================================
@app.post("/api/users/signup")
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    interests: str = Form("General"),
    db: Session = Depends(get_db)
):
    try:
        username = username.strip()
        email = email.lower().strip()
        
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        
        new_user = models.User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            interests=interests,
            role="user",
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        response = JSONResponse(content={
            "success": True,
            "user_id": new_user.id,
            "username": new_user.username,
            "role": new_user.role
        })
        response.set_cookie(
            key="user_session",
            value=str(new_user.id),
            max_age=86400 * 7,
            path="/"
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/login")
async def user_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        login_val = username.lower().strip()
        
        user = db.query(models.User).filter(
            (models.User.email == login_val) |
            (models.User.username == login_val)
        ).first()
        
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        
        response = JSONResponse(content={
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "role": user.role or "user",
            "is_premium": user.is_premium or 0
        })
        response.set_cookie(
            key="user_session",
            value=str(user.id),
            max_age=86400 * 7,
            path="/"
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/logout")
def user_logout(response: Response):
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie(key="user_session", path="/")
    return resp

@app.get("/api/users/me")
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name or "",
        "bio": user.bio or "",
        "interests": user.interests or "",
        "avatar_url": user.avatar_url or "",
        "role": user.role or "user",
        "is_premium": user.is_premium or 0,
        "created_at": str(user.created_at)
    }

# ============================================
# REGIONS (Ghana Heritage)
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        regions = db.query(models.Region).all()
        return [{
            "id": int(r.id),
            "name": str(r.name) if r.name else "",
            "capital": str(r.capital) if r.capital else "",
            "population": str(r.population) if r.population else "",
            "terrain": str(r.terrain) if r.terrain else "",
            "description": str(r.description) if r.description else "",
            "overview": str(r.overview) if r.overview else "",
            "category": str(r.category) if r.category else "",
            "tags": str(r.tags) if r.tags else "",
            "hero_image": str(r.hero_image) if r.hero_image else "",
            "gallery_images": str(r.gallery_images) if r.gallery_images else "",
            "audio_files": str(r.audio_files) if r.audio_files else "",
            "video_files": str(r.video_files) if hasattr(r, 'video_files') and r.video_files else "",
            "documents": str(r.documents) if hasattr(r, 'documents') and r.documents else "",
            "source": str(r.source) if r.source else ""
        } for r in regions]
    except Exception as e:
        print(f"Error getting regions: {e}")
        return []

@app.get("/api/regions/{region_id}")
def get_region(region_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Region not found")
    
    return {
        "id": r.id,
        "name": r.name,
        "capital": r.capital or "",
        "description": r.description or "",
        "overview": r.overview or "",
        "hero_image": r.hero_image or "",
        "gallery_images": r.gallery_images or "",
        "audio_files": r.audio_files or "",
        "video_files": r.video_files if hasattr(r, 'video_files') else "",
        "documents": r.documents if hasattr(r, 'documents') else "",
        "tags": r.tags or ""
    }

@app.post("/api/regions")
def create_region(
    name: str = Form(...),
    capital: str = Form(""),
    population: str = Form(""),
    terrain: str = Form(""),
    description: str = Form(...),
    category: str = Form(""),
    tags: str = Form(""),
    hero_image: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    video_files: str = Form(""),
    documents: str = Form(""),
    source: str = Form(""),
    overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")
        
        r = models.Region(
            name=name.strip(),
            capital=capital.strip(),
            population=population.strip(),
            terrain=terrain.strip(),
            description=description.strip(),
            overview=overview.strip() or description.strip(),
            category=category.strip(),
            tags=tags.strip(),
            hero_image=hero_image.strip(),
            gallery_images=gallery_images.strip(),
            audio_files=audio_files.strip(),
            video_files=video_files.strip() if video_files else "",
            documents=documents.strip() if documents else "",
            source=source.strip()
        )
        
        db.add(r)
        db.commit()
        db.refresh(r)
        
        return {"success": True, "region_id": r.id}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/regions/{region_id}")
def update_region(
    region_id: int,
    name: str = Form(None),
    capital: str = Form(None),
    population: str = Form(None),
    terrain: str = Form(None),
    description: str = Form(None),
    category: str = Form(None),
    tags: str = Form(None),
    hero_image: str = Form(None),
    gallery_images: str = Form(None),
    audio_files: str = Form(None),
    video_files: str = Form(None),
    documents: str = Form(None),
    source: str = Form(None),
    overview: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        r = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Region not found")
        
        if name is not None and name.strip(): r.name = name.strip()
        if capital is not None: r.capital = capital.strip()
        if population is not None: r.population = population.strip()
        if terrain is not None: r.terrain = terrain.strip()
        if description is not None: r.description = description.strip()
        if overview is not None and overview.strip(): r.overview = overview.strip()
        if category is not None: r.category = category.strip()
        if tags is not None: r.tags = tags.strip()
        if hero_image is not None: r.hero_image = hero_image.strip()
        if gallery_images is not None: r.gallery_images = gallery_images.strip()
        if audio_files is not None: r.audio_files = audio_files.strip()
        if video_files is not None: r.video_files = video_files.strip()
        if documents is not None: r.documents = documents.strip()
        if source is not None: r.source = source.strip()
        
        db.commit()
        db.refresh(r)
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    try:
        r = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Region not found")
        
        db.delete(r)
        db.commit()
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FILE UPLOADS (Any Type - Images, Video, Audio, Docs)
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    filename: str = Form(...),
    category: str = Form("general"),
    description: str = Form(""),
    region_id: str = Form(""),
    is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        ext = Path(filename).suffix.lower()
        safe_name = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{filename.replace(' ', '_')}"
        file_path = UPLOAD_DIR / safe_name
        
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        uf = models.UploadedFile(
            filename=safe_name,
            original_name=filename,
            file_path=str(file_path),
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            category=category,
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            description=description,
            uploaded_by="admin",
            is_public=int(is_public) if is_public else 1
        )
        
        db.add(uf)
        db.commit()
        db.refresh(uf)
        
        return {
            "success": True,
            "file_id": uf.id,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name,
            "original_name": filename,
            "category": category,
            "size_bytes": len(content),
            "file_size_mb": round(len(content) / (1024 * 1024), 2),
            "mime_type": file.content_type
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files(category: str = "", region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category:
            q = q.filter(models.UploadedFile.category == category)
        if region_id:
            q = q.filter(models.UploadedFile.region_id == int(region_id))
        
        return [{
            "id": f.id,
            "filename": f.filename,
            "original_name": f.original_name,
            "file_url": f"/uploads/{f.filename}",
            "file_size": f.file_size,
            "file_size_mb": round(f.file_size / (1024 * 1024), 2),
            "mime_type": f.mime_type,
            "category": f.category,
            "region_id": f.region_id,
            "description": f.description,
            "created_at": str(f.created_at)
        } for f in q.order_by(models.UploadedFile.created_at.desc()).all()]
    except Exception as e:
        print(f"Error getting files: {e}")
        return []

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    try:
        f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
        if not f:
            raise HTTPException(status_code=404, detail="File not found")
        
        if os.path.exists(f.file_path):
            os.remove(f.file_path)
        
        db.delete(f)
        db.commit()
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# POSTS & CONTENT
# ============================================
@app.get("/api/posts")
def get_posts(
    status: str = "published",
    content_type: str = "",
    limit: int = 20,
    db: Session = Depends(get_db)
):
    try:
        q = db.query(models.Post).filter(models.Post.status == status)
        if content_type:
            q = q.filter(models.Post.content_type == content_type)
        
        posts = q.order_by(models.Post.created_at.desc()).limit(limit).all()
        
        return [{
            "id": p.id,
            "title": p.title,
            "excerpt": p.excerpt or "",
            "cover_image": p.cover_image or "",
            "content_type": p.content_type or "article",
            "author_username": p.author_username or "",
            "author_id": p.author_id,
            "status": p.status,
            "views": p.views or 0,
            "likes": p.likes or 0,
            "is_premium": p.is_premium or 0,
            "region_id": p.region_id,
            "created_at": str(p.created_at)
        } for p in posts]
    except Exception as e:
        print(f"Error getting posts: {e}")
        return []

@app.post("/api/posts")
async def create_post(
    title: str = Form(...),
    excerpt: str = Form(""),
    content: str = Form(""),
    cover_image: str = Form(""),
    content_type: str = Form("article"),
    region_id: str = Form(""),
    status: str = Form("draft"),
    is_premium: str = Form("0"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in")
    
    if user.role not in ["creator", "superuser", "admin"]:
        raise HTTPException(status_code=403, detail="Creator account required")
    
    post = models.Post(
        author_id=user.id,
        author_username=user.username,
        title=title.strip(),
        excerpt=excerpt.strip(),
        content=content.strip(),
        cover_image=cover_image.strip(),
        content_type=content_type,
        region_id=int(region_id) if region_id and region_id.isdigit() else None,
        status=status,
        is_premium=int(is_premium)
    )
    
    db.add(post)
    db.commit()
    db.refresh(post)
    
    return {"success": True, "post_id": post.id, "status": post.status}

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    db.delete(post)
    db.commit()
    return {"success": True}

# ============================================
# STATS (Safe - handles missing tables)
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get platform stats - safe for fresh databases"""
    try:
        return {
            "total_regions": db.query(models.Region).count(),
            "total_users": db.query(models.User).count(),
            "with_audio": db.query(models.UploadedFile).filter(
                models.UploadedFile.category == "audio").count(),
            "with_images": db.query(models.UploadedFile).filter(
                models.UploadedFile.category == "image").count(),
            "database_size_mb": 0
        }
    except Exception as e:
        print(f"Stats error (fresh DB): {e}")
        return {
            "total_regions": 0,
            "total_users": 0,
            "with_audio": 0,
            "with_images": 0,
            "database_size_mb": 0
        }

# ============================================
# ECHOBOT AI (Hugging Face)
# ============================================
@app.post("/api/ai/chat")
async def ai_chat(
    message: str = Form(...),
    region_context: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """AI chat for heritage questions - premium feature"""
    try:
        user = get_user_from_request(request, db)
        
        # Free users get locked message
        if not user or (not user.is_premium and user.role not in ["superuser", "admin", "creator"]):
            return {
                "reply": "EchoBot is a premium feature 🔒 Subscribe for GH₵150/month to unlock unlimited AI heritage assistance!",
                "success": False,
                "locked": True
            }
        
        if not HF_TOKEN:
            return {
                "reply": "EchoBot is not configured. Add HF_TOKEN to Render environment.",
                "success": False
            }
        
        # Build prompt
        system_prompt = """You are EchoBot, a friendly and knowledgeable AI heritage guide for Ghana.
You specialise in Ghana's 16 regions, culture, history, traditions, food, music, festivals, and people.
Keep answers concise (3-5 sentences), warm, and educational.
If asked about something unrelated to Ghana or heritage, politely redirect to Ghana topics.
Always respond in English."""
        
        if region_context:
            system_prompt += f"\nThe user is currently viewing the {region_context} region."
        
        full_prompt = f"<s>[INST] {system_prompt}\nUser question: {message} [/INST]"
        
        # Call Hugging Face API
        payload = json.dumps({
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 300,
                "temperature": 0.7,
                "do_sample": True,
                "return_full_text": False
            }
        }).encode("utf-8")
        
        req = urllib.request.Request(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
            data=payload,
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
        
        if isinstance(result, list) and len(result) > 0:
            reply = result[0].get("generated_text", "").strip()
        else:
            reply = "I'm having trouble responding right now. Please try again!"
        
        return {"reply": reply, "success": True, "locked": False}
        
    except Exception as e:
        print(f"AI error: {e}")
        return {
            "reply": "EchoBot is warming up! Please try again in a moment.",
            "success": False
        }

# ============================================
# PAYSTACK PAYMENTS (Premium Subscriptions)
# ============================================
@app.post("/api/payments/initialize")
async def initialize_payment(request: Request, db: Session = Depends(get_db)):
    """Initialize Paystack payment for premium subscription"""
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first")
    
    if not PAYSTACK_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Paystack not configured. Add PAYSTACK_SECRET_KEY to Render environment variables."
        )
    
    payload = json.dumps({
        "email": user.email,
        "amount": 15000,  # GH₵150 = 15000 pesewas
        "currency": "GHS",
        "callback_url": "https://echostackgh.onrender.com/payment/callback",
        "metadata": {"user_id": user.id, "plan": "premium"}
    }).encode("utf-8")
    
    req = urllib.request.Request(
        "https://api.paystack.co/transaction/initialize",
        data=payload,
        headers={
            "Authorization": f"Bearer {PAYSTACK_SECRET}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Paystack connection error: {str(e)}")
    
    if not result.get("status"):
        raise HTTPException(status_code=400, detail="Payment initialization failed")
    
    ref = result["data"]["reference"]
    
    # Save payment record if Payment model exists
    try:
        payment = models.Payment(
            user_id=user.id,
            email=user.email,
            amount=15000,
            reference=ref,
            status="pending",
            plan="premium"
        )
        db.add(payment)
        db.commit()
    except:
        pass  # Payment table may not exist yet
    
    return {
        "success": True,
        "authorization_url": result["data"]["authorization_url"],
        "reference": ref
    }

@app.post("/api/payments/webhook")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Paystack webhook - called automatically after payment"""
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")
    
    # Verify webhook signature
    if PAYSTACK_SECRET and signature:
        expected = hmac.new(
            PAYSTACK_SECRET.encode(),
            body,
            hashlib.sha512
        ).hexdigest()
        if signature != expected:
            raise HTTPException(status_code=400, detail="Invalid signature")
    
    try:
        data = json.loads(body.decode("utf-8"))
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if data.get("event") == "charge.success":
        ref = data["data"]["reference"]
        user_id = data["data"].get("metadata", {}).get("user_id")
        
        # Mark payment as successful
        try:
            payment = db.query(models.Payment).filter(
                models.Payment.reference == ref
            ).first()
            if payment:
                payment.status = "success"
        except:
            pass
        
        # Upgrade user to premium
        if user_id:
            try:
                user = db.query(models.User).filter(
                    models.User.id == int(user_id)
                ).first()
                if user:
                    user.is_premium = 1
                    db.commit()
            except:
                pass
        
        return {"status": "ok"}
    
    return {"status": "ignored"}

@app.get("/payment/callback")
async def payment_callback(reference: str, db: Session = Depends(get_db)):
    """User redirect after Paystack checkout"""
    if not PAYSTACK_SECRET:
        return RedirectResponse("/dashboard?payment=error")
    
    req = urllib.request.Request(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers={"Authorization": f"Bearer {PAYSTACK_SECRET}"},
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except:
        return RedirectResponse("/dashboard?payment=error")
    
    if result.get("status") and result["data"].get("status") == "success":
        user_id = result["data"].get("metadata", {}).get("user_id")
        
        if user_id:
            try:
                user = db.query(models.User).filter(
                    models.User.id == int(user_id)
                ).first()
                if user:
                    user.is_premium = 1
                    
                    # Update payment record
                    try:
                        payment = db.query(models.Payment).filter(
                            models.Payment.reference == reference
                        ).first()
                        if payment:
                            payment.status = "success"
                    except:
                        pass
                    
                    db.commit()
            except:
                pass
        
        return RedirectResponse("/dashboard?upgraded=1")
    
    return RedirectResponse("/dashboard?payment=failed")

# ============================================
# THEME & CONFIG (Site Builder)
# ============================================
@app.get("/api/theme")
def get_theme():
    try:
        if os.path.exists("theme.json"):
            with open("theme.json", "r") as f:
                return json.load(f)
        return {}
    except:
        return {}

@app.post("/api/theme")
async def save_theme(request: Request):
    try:
        body = await request.json()
        with open("theme.json", "w") as f:
            json.dump(body, f)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/site-config")
async def get_site_config(request: Request):
    """Get site configuration for Site Builder"""
    require_admin(request)
    try:
        if os.path.exists("site_config.json"):
            with open("site_config.json", "r") as f:
                return json.load(f)
        return {}
    except:
        return {}

@app.post("/api/site-config")
async def save_site_config(request: Request):
    """Save site configuration from Site Builder"""
    require_admin(request)
    try:
        config = await request.json()
        with open("site_config.json", "w") as f:
            json.dump(config, f, indent=2)
        return {"success": True, "message": "Site config saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SECTIONS & MISC
# ============================================
@app.get("/api/sections")
def get_sections(active_only: int = 1, db: Session = Depends(get_db)):
    try:
        q = db.query(models.Section)
        if active_only:
            q = q.filter(models.Section.is_active == 1).order_by(models.Section.display_order)
        return [{"id": s.id, "name": s.name, "slug": s.slug, "description": s.description} 
                for s in q.all()]
    except:
        return []

@app.post("/api/sections")
def create_section(
    name: str = Form(...),
    description: str = Form(""),
    display_order: int = Form(0),
    db: Session = Depends(get_db)
):
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        if db.query(models.Section).filter(models.Section.slug == slug).first():
            raise HTTPException(status_code=400, detail="Already exists")
        
        s = models.Section(
            name=name,
            slug=slug,
            description=description,
            display_order=display_order
        )
        db.add(s)
        db.commit()
        db.refresh(s)
        return {"success": True, "section_id": s.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    try:
        s = db.query(models.Section).filter(models.Section.id == section_id).first()
        if not s:
            raise HTTPException(status_code=404)
        s.is_active = 0
        db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    try:
        if not isinstance(data, list):
            data = [data]
        imported = 0
        for rd in data:
            try:
                db.add(models.Region(**rd))
                imported += 1
            except:
                continue
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# EVENTS, NEWSLETTER, CHAT (Basic Endpoints)
# ============================================
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    try:
        events = db.query(models.Event).filter(models.Event.is_active == 1).all()
        return [{
            "id": e.id,
            "title": e.title,
            "description": e.description,
            "event_date": e.event_date,
            "location": e.location,
            "image_url": e.image_url
        } for e in events]
    except:
        return []

@app.post("/api/events")
async def create_event(
    title: str = Form(...),
    description: str = Form(""),
    event_date: str = Form(""),
    location: str = Form(""),
    image_url: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    require_admin(request)
    
    event = models.Event(
        title=title,
        description=description,
        event_date=event_date,
        location=location,
        image_url=image_url
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return {"success": True, "event_id": event.id}

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404)
    
    event.is_active = 0
    db.commit()
    return {"success": True}

@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(
    email: str = Form(...),
    full_name: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(models.NewsletterSubscriber).filter(
        models.NewsletterSubscriber.email == email.lower()
    ).first()
    
    if existing:
        return {"success": True, "message": "Already subscribed!"}
    
    sub = models.NewsletterSubscriber(
        email=email.lower(),
        full_name=full_name
    )
    db.add(sub)
    db.commit()
    return {"success": True, "message": "Subscribed successfully!"}

@app.get("/api/chat")
def get_messages(region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.is_approved == 1)
        if region_id:
            q = q.filter(models.ChatMessage.region_id == int(region_id))
        
        msgs = q.order_by(models.ChatMessage.created_at.desc()).limit(50).all()
        return [{
            "id": m.id,
            "username": m.username,
            "message": m.message,
            "region_id": m.region_id,
            "created_at": str(m.created_at)
        } for m in msgs]
    except:
        return []

@app.post("/api/chat")
async def post_message(
    message: str = Form(...),
    region_id: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to chat")
    
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    msg = models.ChatMessage(
        user_id=user.id,
        username=user.username,
        message=message.strip()[:500],
        region_id=int(region_id) if region_id and region_id.isdigit() else None
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    
    return {
        "success": True,
        "id": msg.id,
        "username": msg.username,
        "message": msg.message
    }
