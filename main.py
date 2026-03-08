from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json
import re
import hashlib
import secrets

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

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user(request: Request, db: Session) -> models.User | None:
    token = request.cookies.get("user_session")
    if not token:
        return None
    return db.query(models.User).filter(models.User.session_token == token).first()

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

@app.get("/dashboard")
def dashboard_page():
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    raise HTTPException(status_code=404)

@app.get("/app")
def app_page():
    if os.path.exists("app.html"):
        return FileResponse("app.html")
    raise HTTPException(status_code=404)

@app.get("/creator")
def creator_page():
    if os.path.exists("creator.html"):
        return FileResponse("creator.html")
    raise HTTPException(status_code=404)

@app.get("/post/{post_id}")
def post_page(post_id: int):
    if os.path.exists("post.html"):
        return FileResponse("post.html")
    raise HTTPException(status_code=404)

@app.get("/user-login")
def user_login_page():
    if os.path.exists("user-login.html"):
        return FileResponse("user-login.html")
    raise HTTPException(status_code=404)

@app.get("/user-profile")
def user_profile_page():
    if os.path.exists("user-profile.html"):
        return FileResponse("user-profile.html")
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest_route():
    if os.path.exists("manifest.json"):
        with open("manifest.json", "r") as f:
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404)

# ============================================
# ADMIN LOGIN SYSTEM
# ============================================
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
    cleaned_answer = CORRECT_ANSWER.lower().replace(" ", "")
    input_answer = answer.strip().lower().replace(" ", "")
    if cleaned_answer == input_answer:
        response = JSONResponse(content={"success": True, "token": "ADMIN_AUTHORIZED"})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED", max_age=86400, path="/")
        return response
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="admin_session", path="/")
    return response

# ============================================
# USER AUTH SYSTEM
# ============================================
@app.post("/api/users/register")
async def register_user(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        existing = db.query(models.User).filter(
            (models.User.username == username) | (models.User.email == email)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Username or email already exists")

        user = models.User(
            username=username.strip(),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role="user",
            plan="free"
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        token = secrets.token_urlsafe(32)
        user.session_token = token
        db.commit()

        response = JSONResponse(content={
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "plan": user.plan,
                "loggedIn": True
            }
        })
        response.set_cookie(key="user_session", value=token, max_age=86400 * 30, path="/", httponly=False)
        return response
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/login")
async def user_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.User).filter(models.User.email == email.strip().lower()).first()
        if not user or user.password_hash != hash_password(password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account disabled")

        token = secrets.token_urlsafe(32)
        user.session_token = token
        db.commit()

        response = JSONResponse(content={
            "success": True,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "plan": user.plan,
                "avatar_url": user.avatar_url or "",
                "channel_name": user.channel_name or "",
                "loggedIn": True
            }
        })
        response.set_cookie(key="user_session", value=token, max_age=86400 * 30, path="/", httponly=False)
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/logout")
async def user_logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("user_session")
    if token:
        user = db.query(models.User).filter(models.User.session_token == token).first()
        if user:
            user.session_token = ""
            db.commit()
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="user_session", path="/")
    return response

@app.get("/api/users/me")
async def get_me(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "plan": user.plan,
        "avatar_url": user.avatar_url or "",
        "channel_name": user.channel_name or user.username,
        "channel_desc": user.channel_desc or "",
        "follower_count": user.follower_count or 0
    }

@app.post("/api/users/become-creator")
async def become_creator(
    request: Request,
    channel_name: str = Form(...),
    channel_desc: str = Form(""),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    user.channel_name = channel_name.strip()
    user.channel_desc = channel_desc.strip()
    user.role = "creator"
    user.plan = "premium"
    db.commit()
    return {"success": True, "message": "You are now a creator!"}

@app.put("/api/users/me")
async def update_profile(
    request: Request,
    channel_name: str = Form(None),
    channel_desc: str = Form(None),
    avatar_url: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    if channel_name is not None:
        user.channel_name = channel_name.strip()
    if channel_desc is not None:
        user.channel_desc = channel_desc.strip()
    if avatar_url is not None:
        user.avatar_url = avatar_url.strip()
    db.commit()
    return {"success": True, "message": "Profile updated"}

# ============================================
# PROFILE PICTURE UPLOAD
# ============================================
@app.post("/api/users/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            raise HTTPException(status_code=400, detail="Only image files allowed for avatar")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"avatar_{user.id}_{timestamp}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        url = f"/uploads/{safe_name}"
        user.avatar_url = url
        db.commit()
        return {"success": True, "url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# POSTS
# ============================================
@app.get("/api/posts")
def get_posts(
    request: Request,
    status: str = "published",
    content_type: str = "",
    author_id: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    try:
        query = db.query(models.Post)

        if status == "all":
            pass  # no status filter — used by creator to see their own posts
        elif status == "published":
            query = query.filter(models.Post.status == "published")
        else:
            query = query.filter(models.Post.status == status)

        if content_type:
            query = query.filter(models.Post.content_type == content_type)

        if author_id:
            query = query.filter(models.Post.author_id == author_id)

        posts = query.order_by(models.Post.created_at.desc()).limit(limit).all()

        result = []
        for p in posts:
            author = db.query(models.User).filter(models.User.id == p.author_id).first()
            result.append({
                "id": p.id,
                "title": p.title,
                "excerpt": p.excerpt or "",
                "content": p.content or "",
                "content_type": p.content_type,
                "cover_image": p.cover_image or "",
                "audio_url": p.audio_url or "",
                "video_url": p.video_url or "",
                "gallery": p.gallery or "",
                "tags": p.tags or "",
                "status": p.status,
                "is_premium": bool(p.is_premium),
                "view_count": p.view_count or 0,
                "like_count": p.like_count or 0,
                "comment_count": p.comment_count or 0,
                "author_id": p.author_id,
                "author_username": author.username if author else "Unknown",
                "author_channel": author.channel_name if author else "",
                "author_avatar": author.avatar_url if author else "",
                "region_id": p.region_id,
                "published_at": str(p.published_at) if p.published_at else "",
                "created_at": str(p.created_at)
            })
        return result
    except Exception as e:
        print(f"❌ get_posts error: {e}")
        return []

@app.get("/api/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    # Increment view count
    post.view_count = (post.view_count or 0) + 1
    db.commit()
    author = db.query(models.User).filter(models.User.id == post.author_id).first()
    return {
        "id": post.id,
        "title": post.title,
        "excerpt": post.excerpt or "",
        "content": post.content or "",
        "content_type": post.content_type,
        "cover_image": post.cover_image or "",
        "audio_url": post.audio_url or "",
        "video_url": post.video_url or "",
        "gallery": post.gallery or "",
        "tags": post.tags or "",
        "status": post.status,
        "is_premium": bool(post.is_premium),
        "is_locked": bool(post.is_premium),
        "view_count": post.view_count or 0,
        "like_count": post.like_count or 0,
        "comment_count": post.comment_count or 0,
        "author_id": post.author_id,
        "author_username": author.username if author else "Unknown",
        "author_channel": author.channel_name if author else "",
        "author_avatar": author.avatar_url if author else "",
        "region_id": post.region_id,
        "published_at": str(post.published_at) if post.published_at else "",
        "created_at": str(post.created_at)
    }

@app.post("/api/posts")
async def create_post(
    request: Request,
    title: str = Form(...),
    content: str = Form(""),
    excerpt: str = Form(""),
    cover_image: str = Form(""),
    content_type: str = Form("article"),
    audio_url: str = Form(""),
    video_url: str = Form(""),
    gallery: str = Form(""),
    tags: str = Form(""),
    region_id: str = Form(""),
    is_premium: str = Form("0"),
    status: str = Form("draft"),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    if user.role not in ["creator", "admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Only creators can post")
    try:
        published_at = datetime.utcnow() if status == "published" else None
        post = models.Post(
            author_id=user.id,
            title=title.strip(),
            excerpt=excerpt.strip(),
            content=content.strip(),
            content_type=content_type,
            cover_image=cover_image.strip(),
            audio_url=audio_url.strip(),
            video_url=video_url.strip(),
            gallery=gallery.strip(),
            tags=tags.strip(),
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            is_premium=int(is_premium) if is_premium else 0,
            status=status,
            published_at=published_at
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        print(f"✅ Post created: ID={post.id} status={status} by user={user.username}")
        return {"success": True, "post_id": post.id, "status": status}
    except Exception as e:
        db.rollback()
        print(f"❌ create_post error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int,
    request: Request,
    title: str = Form(None),
    content: str = Form(None),
    excerpt: str = Form(None),
    cover_image: str = Form(None),
    content_type: str = Form(None),
    audio_url: str = Form(None),
    video_url: str = Form(None),
    gallery: str = Form(None),
    tags: str = Form(None),
    region_id: str = Form(None),
    is_premium: str = Form(None),
    status: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != user.id and user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not your post")
    try:
        if title is not None: post.title = title.strip()
        if content is not None: post.content = content.strip()
        if excerpt is not None: post.excerpt = excerpt.strip()
        if cover_image is not None: post.cover_image = cover_image.strip()
        if content_type is not None: post.content_type = content_type
        if audio_url is not None: post.audio_url = audio_url.strip()
        if video_url is not None: post.video_url = video_url.strip()
        if gallery is not None: post.gallery = gallery.strip()
        if tags is not None: post.tags = tags.strip()
        if region_id is not None:
            post.region_id = int(region_id) if region_id.isdigit() else None
        if is_premium is not None: post.is_premium = int(is_premium)
        if status is not None:
            post.status = status
            if status == "published" and not post.published_at:
                post.published_at = datetime.utcnow()
        db.commit()
        return {"success": True, "message": "Post updated"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != user.id and user.role not in ["admin", "superuser"]:
        raise HTTPException(status_code=403, detail="Not your post")
    db.delete(post)
    db.commit()
    return {"success": True}

# ============================================
# COVER IMAGE UPLOAD FOR POSTS
# ============================================
@app.post("/api/upload/cover")
async def upload_cover_image(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    try:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.mov', '.webm']:
            raise HTTPException(status_code=400, detail="Unsupported file type for cover")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"cover_{user.id}_{timestamp}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        return {"success": True, "url": f"/uploads/{safe_name}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# COMMENTS
# ============================================
@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(models.Comment).filter(models.Comment.post_id == post_id).order_by(models.Comment.created_at).all()
    result = []
    for c in comments:
        author = db.query(models.User).filter(models.User.id == c.author_id).first()
        result.append({
            "id": c.id,
            "content": c.content,
            "author_username": author.username if author else "Unknown",
            "author_avatar": author.avatar_url if author else "",
            "created_at": str(c.created_at)
        })
    return result

@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    request: Request,
    content: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to comment")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    comment = models.Comment(post_id=post_id, author_id=user.id, content=content.strip())
    db.add(comment)
    post.comment_count = (post.comment_count or 0) + 1
    db.commit()
    return {"success": True, "comment_id": comment.id}

# ============================================
# LIKES
# ============================================
@app.post("/api/posts/{post_id}/like")
async def toggle_like(post_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to like")
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    existing = db.query(models.Like).filter(
        models.Like.post_id == post_id,
        models.Like.user_id == user.id
    ).first()
    if existing:
        db.delete(existing)
        post.like_count = max(0, (post.like_count or 0) - 1)
        db.commit()
        return {"liked": False, "likes": post.like_count}
    else:
        like = models.Like(post_id=post_id, user_id=user.id)
        db.add(like)
        post.like_count = (post.like_count or 0) + 1
        db.commit()
        return {"liked": True, "likes": post.like_count}

# ============================================
# FOLLOW / CREATORS
# ============================================
@app.get("/api/creators")
def get_creators(db: Session = Depends(get_db)):
    creators = db.query(models.User).filter(
        models.User.role.in_(["creator", "superuser"])
    ).all()
    return [{
        "id": c.id,
        "username": c.username,
        "channel_name": c.channel_name or c.username,
        "channel_desc": c.channel_desc or "",
        "avatar_url": c.avatar_url or "",
        "follower_count": c.follower_count or 0
    } for c in creators]

@app.post("/api/follow/{creator_id}")
async def toggle_follow(creator_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to follow")
    creator = db.query(models.User).filter(models.User.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == user.id,
        models.Follow.creator_id == creator_id
    ).first()
    if existing:
        db.delete(existing)
        creator.follower_count = max(0, (creator.follower_count or 0) - 1)
        db.commit()
        return {"following": False}
    else:
        follow = models.Follow(follower_id=user.id, creator_id=creator_id)
        db.add(follow)
        creator.follower_count = (creator.follower_count or 0) + 1
        db.commit()
        return {"following": True}

@app.get("/api/follow/{creator_id}/status")
async def follow_status(creator_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return {"following": False}
    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == user.id,
        models.Follow.creator_id == creator_id
    ).first()
    return {"following": bool(existing)}

# ============================================
# REGION CRUD OPERATIONS
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        regions = db.query(models.Region).all()
        result = []
        for r in regions:
            item = {
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
                "source": str(r.source) if r.source else ""
            }
            result.append(item)
        print(f"✅ Returning {len(result)} regions")
        return result
    except Exception as e:
        print(f"❌ Error in get_regions: {e}")
        return []

@app.post("/api/regions")
def create_region(
    name: str = Form(...),
    capital: str = Form(""),
    population: str = Form(""),
    terrain: str = Form(""),
    description: str = Form(""),
    category: str = Form(""),
    tags: str = Form(""),
    hero_image: str = Form(""),
    gallery_images: str = Form(""),
    audio_files: str = Form(""),
    source: str = Form(""),
    overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")
        new_region = models.Region(
            name=name.strip(), capital=capital.strip(), population=population.strip(),
            terrain=terrain.strip(), description=description.strip(),
            overview=overview.strip() or description.strip(),
            category=category.strip(), tags=tags.strip(), hero_image=hero_image.strip(),
            gallery_images=gallery_images.strip(), audio_files=audio_files.strip(),
            source=source.strip()
        )
        db.add(new_region)
        db.commit()
        db.refresh(new_region)
        return {"success": True, "region_id": new_region.id, "message": "Created successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/regions/{region_id}")
def update_region(
    region_id: int,
    name: str = Form(None), capital: str = Form(None), population: str = Form(None),
    terrain: str = Form(None), description: str = Form(None), category: str = Form(None),
    tags: str = Form(None), hero_image: str = Form(None), gallery_images: str = Form(None),
    audio_files: str = Form(None), source: str = Form(None), overview: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        region = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Not found")
        if name is not None and name.strip(): region.name = name.strip()
        if capital is not None: region.capital = capital.strip()
        if population is not None: region.population = population.strip()
        if terrain is not None: region.terrain = terrain.strip()
        if description is not None: region.description = description.strip()
        if overview is not None and overview.strip(): region.overview = overview.strip()
        if category is not None: region.category = category.strip()
        if tags is not None: region.tags = tags.strip()
        if hero_image is not None: region.hero_image = hero_image.strip()
        if gallery_images is not None: region.gallery_images = gallery_images.strip()
        if audio_files is not None: region.audio_files = audio_files.strip()
        if source is not None: region.source = source.strip()
        db.commit()
        db.refresh(region)
        return {"success": True, "message": "Updated successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    try:
        region = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not region:
            raise HTTPException(status_code=404, detail="Not found")
        db.delete(region)
        db.commit()
        return {"success": True, "message": "Deleted successfully!"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# UNIVERSAL FILE UPLOAD
# ============================================
@app.post("/api/upload/file")
async def upload_generic_file(
    request: Request,
    file: UploadFile = File(...),
    filename: str = Form(...),
    category: str = Form("general"),
    description: str = Form(""),
    region_id: str = Form(""),
    is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        ext = os.path.splitext(filename)[1].lower()
        safe_ext = ext if ext else ".bin"
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{timestamp}{safe_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        file_size = len(content)
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        uploaded_file = models.UploadedFile(
            filename=safe_name, original_name=filename, file_path=file_path,
            file_size=file_size, mime_type=file.content_type or "application/octet-stream",
            category=category,
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            description=description, uploaded_by="admin",
            is_public=int(is_public) if is_public else 1
        )
        db.add(uploaded_file)
        db.commit()
        db.refresh(uploaded_file)
        return {
            "success": True, "file_id": uploaded_file.id,
            "url": f"/uploads/{safe_name}", "filename": safe_name,
            "original_name": filename, "category": category,
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "mime_type": file.content_type or "application/octet-stream",
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "file_url": f"/uploads/{safe_name}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/files")
def get_files(category: str = "", region_id: str = "", db: Session = Depends(get_db)):
    try:
        query = db.query(models.UploadedFile)
        if category:
            query = query.filter(models.UploadedFile.category == category)
        if region_id:
            query = query.filter(models.UploadedFile.region_id == int(region_id))
        files = query.order_by(models.UploadedFile.created_at.desc()).all()
        return [{
            "id": f.id, "filename": f.filename, "original_name": f.original_name,
            "file_url": f"/uploads/{f.filename}",
            "file_size": f.file_size,
            "file_size_mb": round(f.file_size / (1024 * 1024), 2),
            "mime_type": f.mime_type, "category": f.category,
            "region_id": f.region_id, "description": f.description,
            "created_at": str(f.created_at)
        } for f in files]
    except Exception as e:
        return []

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    try:
        uploaded_file = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
        if not uploaded_file:
            raise HTTPException(status_code=404, detail="File not found")
        if os.path.exists(uploaded_file.file_path):
            os.remove(uploaded_file.file_path)
        db.delete(uploaded_file)
        db.commit()
        return {"success": True, "message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SECTIONS / CATEGORIES
# ============================================
@app.post("/api/sections")
def create_section(
    name: str = Form(...), description: str = Form(""), display_order: int = Form(0),
    db: Session = Depends(get_db)
):
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        existing = db.query(models.Section).filter(models.Section.slug == slug).first()
        if existing:
            raise HTTPException(status_code=400, detail="Section name already exists")
        new_section = models.Section(name=name, slug=slug, description=description, display_order=display_order)
        db.add(new_section)
        db.commit()
        db.refresh(new_section)
        return {"success": True, "section_id": new_section.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sections")
def get_sections(active_only: int = 1, db: Session = Depends(get_db)):
    try:
        if active_only:
            sections = db.query(models.Section).filter(models.Section.is_active == 1).order_by(models.Section.display_order).all()
        else:
            sections = db.query(models.Section).all()
        return [{"id": s.id, "name": s.name, "slug": s.slug, "description": s.description} for s in sections]
    except Exception as e:
        return []

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    try:
        section = db.query(models.Section).filter(models.Section.id == section_id).first()
        if not section:
            raise HTTPException(status_code=404, detail="Not found")
        section.is_active = 0
        db.commit()
        return {"success": True, "message": "Section deactivated"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# STATS & IMPORT/EXPORT
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
    try:
        total_regions = db.query(models.Region).count()
        total_files = db.query(models.UploadedFile).count()
        total_video = db.query(models.UploadedFile).filter(models.UploadedFile.category == "video").count()
        total_audio = db.query(models.UploadedFile).filter(models.UploadedFile.category == "audio").count()
        total_images = db.query(models.UploadedFile).filter(models.UploadedFile.category == "image").count()
        db_path = "echostack.db"
        size_mb = round(os.path.getsize(db_path) / 1024 / 1024, 2) if os.path.exists(db_path) else 0
        return {
            "total_regions": total_regions, "total_files": total_files,
            "with_video": total_video, "with_audio": total_audio,
            "with_images": total_images, "database_size_mb": size_mb
        }
    except Exception as e:
        return {"total_regions": 0, "database_size_mb": 0}

@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    try:
        if not isinstance(data, list):
            data = [data]
        imported = 0
        for region_data in data:
            try:
                new_region = models.Region(**region_data)
                db.add(new_region)
                imported += 1
            except Exception as e:
                continue
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
