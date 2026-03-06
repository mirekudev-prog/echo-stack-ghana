from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import json
import re
import hashlib
import urllib.request

from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI(title="EchoStack API")

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
except Exception as e:
    print(f"Warning: Could not mount uploads folder")

CORRECT_ANSWER = "THE ADMIN"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def get_user_from_request(request: Request, db: Session):
    user_id = request.cookies.get("user_session")
    if not user_id:
        return None
    try:
        return db.query(models.User).filter(models.User.id == int(user_id)).first()
    except:
        return None

# ============================================
# STATIC PAGES
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

@app.get("/dashboard")
async def dashboard_page(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/user-login")
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    raise HTTPException(status_code=404)

@app.get("/creator")
async def creator_page(request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/user-login")
    if os.path.exists("creator.html"):
        return FileResponse("creator.html")
    raise HTTPException(status_code=404)

@app.get("/post/{post_id}")
async def post_page(post_id: int, request: Request):
    token = request.cookies.get("user_session")
    if not token:
        return RedirectResponse(url="/user-login")
    if os.path.exists("post.html"):
        return FileResponse("post.html")
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

@app.get("/client-login")
def client_login_page():
    if os.path.exists("client_login.html"):
        return FileResponse("client_login.html")
    raise HTTPException(status_code=404)

@app.get("/client-dashboard")
async def client_dashboard_page(request: Request):
    token = request.cookies.get("client_session")
    if not token:
        return RedirectResponse(url="/client-login")
    if os.path.exists("client_dashboard.html"):
        return FileResponse("client_dashboard.html")
    raise HTTPException(status_code=404)

@app.get("/test")
def test_endpoint():
    return {"status": "ok", "backend": "working"}

@app.get("/echostack-logo.png")
def serve_logo():
    if os.path.exists("echostack-logo.png"):
        return FileResponse("echostack-logo.png", media_type="image/png")
    raise HTTPException(status_code=404)

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
            content = json.load(f)
        return JSONResponse(content=content, media_type="application/json")
    raise HTTPException(status_code=404)

# ============================================
# SUPER ADMIN (Emmanuel)
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
async def admin_login(answer: str = Form(...)):
    cleaned = CORRECT_ANSWER.lower().replace(" ", "")
    given = answer.strip().lower().replace(" ", "")
    if cleaned == given:
        response = JSONResponse(content={"success": True})
        response.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED",
                            max_age=86400, path="/")
        return response
    raise HTTPException(status_code=403, detail="Incorrect answer")

@app.post("/api/auth/logout")
def admin_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="admin_session", path="/")
    return response

# ============================================
# PUBLIC USER ACCOUNTS
# ============================================
@app.post("/api/users/signup")
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    interests: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        if db.query(models.User).filter(models.User.email == email.lower().strip()).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        if db.query(models.User).filter(models.User.username == username.strip()).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        new_user = models.User(
            username=username.strip(),
            email=email.lower().strip(),
            password_hash=hash_password(password),
            interests=interests,
            role="user"
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
        response.set_cookie(key="user_session", value=str(new_user.id),
                            max_age=86400 * 7, path="/")
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
        user = db.query(models.User).filter(
            (models.User.email == username.lower().strip()) |
            (models.User.username == username.strip())
        ).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        response = JSONResponse(content={
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "role": user.role or "user",
            "is_premium": user.is_premium or 0
        })
        response.set_cookie(key="user_session", value=str(user.id),
                            max_age=86400 * 7, path="/")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/users/logout")
def user_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="user_session", path="/")
    return response

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
        "full_name": user.full_name or "",
        "bio": user.bio or "",
        "interests": user.interests or "",
        "avatar_url": user.avatar_url or "",
        "role": user.role or "user",
        "is_premium": user.is_premium or 0,
        "created_at": str(user.created_at)
    }

@app.get("/api/admin/users")
async def get_all_users(request: Request, db: Session = Depends(get_db)):
    admin_token = request.cookies.get("admin_session")
    client_token = request.cookies.get("client_session")
    if not admin_token and not client_token:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return [{
        "id": u.id,
        "username": u.username,
        "email": u.email,
        "full_name": u.full_name or "",
        "role": u.role or "user",
        "is_premium": u.is_premium or 0,
        "is_active": u.is_active,
        "created_at": str(u.created_at)
    } for u in users]

@app.put("/api/admin/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if not request.cookies.get("admin_session"):
        raise HTTPException(status_code=403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    user.role = role
    db.commit()
    return {"success": True}

@app.put("/api/admin/users/{user_id}/premium")
async def toggle_premium(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not request.cookies.get("admin_session"):
        raise HTTPException(status_code=403)
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404)
    user.is_premium = 1 if not user.is_premium else 0
    db.commit()
    return {"success": True, "is_premium": user.is_premium}

# ============================================
# CLIENT
# ============================================
@app.post("/api/client/login")
async def client_login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    try:
        client = db.query(models.Client).filter(
            models.Client.email == email.lower().strip()
        ).first()
        if not client or not verify_password(password, client.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not client.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")
        response = JSONResponse(content={
            "success": True,
            "client_id": client.id,
            "full_name": client.full_name,
            "organisation_name": client.organisation_name or ""
        })
        response.set_cookie(key="client_session", value=str(client.id),
                            max_age=86400 * 7, path="/")
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/client/logout")
def client_logout():
    response = JSONResponse(content={"success": True})
    response.delete_cookie(key="client_session", path="/")
    return response

@app.get("/api/client/me")
async def get_client(request: Request, db: Session = Depends(get_db)):
    client_id = request.cookies.get("client_session")
    if not client_id:
        raise HTTPException(status_code=401, detail="Not logged in")
    client = db.query(models.Client).filter(
        models.Client.id == int(client_id)
    ).first()
    if not client:
        raise HTTPException(status_code=404)
    return {
        "id": client.id,
        "full_name": client.full_name,
        "email": client.email,
        "organisation_name": client.organisation_name or "",
        "plan": client.plan,
        "created_at": str(client.created_at)
    }

@app.get("/api/client/stats")
async def get_client_stats(request: Request, db: Session = Depends(get_db)):
    if not request.cookies.get("client_session"):
        raise HTTPException(status_code=401)
    return {
        "total_regions": db.query(models.Region).count(),
        "total_users": db.query(models.User).count(),
        "total_messages": db.query(models.ChatMessage).count(),
        "total_stories": db.query(models.StorySubmission).count(),
        "pending_stories": db.query(models.StorySubmission).filter(
            models.StorySubmission.status == "pending").count(),
        "total_subscribers": db.query(models.NewsletterSubscriber).count(),
        "total_events": db.query(models.Event).count(),
        "total_files": db.query(models.UploadedFile).count()
    }

@app.post("/api/admin/create-client")
async def create_client(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    organisation_name: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    if request.cookies.get("admin_session") != "ADMIN_AUTHORIZED":
        raise HTTPException(status_code=403)
    if db.query(models.Client).filter(models.Client.email == email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    client = models.Client(
        full_name=full_name, email=email.lower(),
        password_hash=hash_password(password),
        organisation_name=organisation_name, plan="freemium"
    )
    db.add(client); db.commit(); db.refresh(client)
    return {"success": True, "client_id": client.id}

# ============================================
# POSTS (Creator content)
# ============================================
@app.get("/api/posts")
async def get_posts(
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
        return []

@app.get("/api/posts/my")
async def get_my_posts(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    posts = db.query(models.Post).filter(
        models.Post.author_id == user.id
    ).order_by(models.Post.created_at.desc()).all()
    return [{
        "id": p.id, "title": p.title, "excerpt": p.excerpt or "",
        "cover_image": p.cover_image or "",
        "content_type": p.content_type or "article",
        "status": p.status, "views": p.views or 0,
        "likes": p.likes or 0, "created_at": str(p.created_at)
    } for p in posts]

@app.get("/api/posts/{post_id}")
async def get_single_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    user = get_user_from_request(request, db)
    # increment views
    post.views = (post.views or 0) + 1
    db.commit()
    # check if full content is locked
    is_locked = bool(post.is_premium) and (not user or not user.is_premium)
    return {
        "id": post.id,
        "title": post.title,
        "excerpt": post.excerpt or "",
        "content": post.content if not is_locked else None,
        "cover_image": post.cover_image or "",
        "content_type": post.content_type or "article",
        "author_username": post.author_username or "",
        "author_id": post.author_id,
        "status": post.status,
        "views": post.views or 0,
        "likes": post.likes or 0,
        "is_premium": post.is_premium or 0,
        "is_locked": is_locked,
        "region_id": post.region_id,
        "created_at": str(post.created_at)
    }

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
        raise HTTPException(status_code=401)
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
    db.add(post); db.commit(); db.refresh(post)
    return {"success": True, "post_id": post.id, "status": post.status}

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int,
    title: str = Form(None), excerpt: str = Form(None),
    content: str = Form(None), cover_image: str = Form(None),
    content_type: str = Form(None), status: str = Form(None),
    is_premium: str = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404)
    if post.author_id != user.id and user.role not in ["superuser", "admin"]:
        raise HTTPException(status_code=403)
    if title: post.title = title.strip()
    if excerpt is not None: post.excerpt = excerpt.strip()
    if content is not None: post.content = content.strip()
    if cover_image is not None: post.cover_image = cover_image.strip()
    if content_type: post.content_type = content_type
    if status: post.status = status
    if is_premium is not None: post.is_premium = int(is_premium)
    db.commit()
    return {"success": True}

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    admin = request.cookies.get("admin_session")
    if not user and not admin:
        raise HTTPException(status_code=401)
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404)
    db.delete(post); db.commit()
    return {"success": True}

# ============================================
# COMMENTS
# ============================================
@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(models.Comment).filter(
        models.Comment.post_id == post_id,
        models.Comment.is_approved == 1
    ).order_by(models.Comment.created_at.asc()).all()
    return [{"id": c.id, "username": c.username, "content": c.content,
             "created_at": str(c.created_at)} for c in comments]

@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    content: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in")
    comment = models.Comment(
        post_id=post_id, user_id=user.id,
        username=user.username, content=content.strip()
    )
    db.add(comment); db.commit(); db.refresh(comment)
    return {"success": True, "id": comment.id,
            "username": comment.username, "content": comment.content}

# ============================================
# FOLLOWS & LIKES
# ============================================
@app.post("/api/follow/{user_id}")
async def follow_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == user.id,
        models.Follow.following_id == user_id
    ).first()
    if existing:
        db.delete(existing); db.commit()
        return {"success": True, "following": False}
    follow = models.Follow(follower_id=user.id, following_id=user_id)
    db.add(follow); db.commit()
    return {"success": True, "following": True}

@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    existing = db.query(models.Like).filter(
        models.Like.post_id == post_id,
        models.Like.user_id == user.id
    ).first()
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if existing:
        db.delete(existing)
        if post: post.likes = max(0, (post.likes or 1) - 1)
        db.commit()
        return {"success": True, "liked": False, "likes": post.likes if post else 0}
    like = models.Like(post_id=post_id, user_id=user.id)
    db.add(like)
    if post: post.likes = (post.likes or 0) + 1
    db.commit()
    return {"success": True, "liked": True, "likes": post.likes if post else 1}

# ============================================
# CREATOR CHANNEL
# ============================================
@app.get("/api/creator/channel")
async def get_channel(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    channel = db.query(models.CreatorChannel).filter(
        models.CreatorChannel.user_id == user.id
    ).first()
    post_count = db.query(models.Post).filter(
        models.Post.author_id == user.id,
        models.Post.status == "published"
    ).count()
    follower_count = db.query(models.Follow).filter(
        models.Follow.following_id == user.id
    ).count()
    return {
        "username": user.username,
        "channel_name": channel.channel_name if channel else user.username,
        "channel_description": channel.channel_description if channel else "",
        "channel_image": channel.channel_image if channel else "",
        "post_count": post_count,
        "follower_count": follower_count,
        "role": user.role or "user"
    }

@app.post("/api/creator/channel")
async def update_channel(
    channel_name: str = Form(""),
    channel_description: str = Form(""),
    channel_image: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    if user.role not in ["creator", "superuser", "admin"]:
        user.role = "creator"
    channel = db.query(models.CreatorChannel).filter(
        models.CreatorChannel.user_id == user.id
    ).first()
    if channel:
        channel.channel_name = channel_name or user.username
        channel.channel_description = channel_description
        channel.channel_image = channel_image
    else:
        channel = models.CreatorChannel(
            user_id=user.id,
            channel_name=channel_name or user.username,
            channel_description=channel_description,
            channel_image=channel_image
        )
        db.add(channel)
    db.commit()
    return {"success": True}

@app.post("/api/creator/become")
async def become_creator(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    user.role = "creator"
    existing = db.query(models.CreatorChannel).filter(
        models.CreatorChannel.user_id == user.id
    ).first()
    if not existing:
        channel = models.CreatorChannel(
            user_id=user.id, channel_name=user.username
        )
        db.add(channel)
    db.commit()
    return {"success": True, "message": "You are now a creator!"}

@app.get("/api/creators")
def get_creators(db: Session = Depends(get_db)):
    creators = db.query(models.User).filter(
        models.User.role.in_(["creator", "superuser"])
    ).all()
    result = []
    for c in creators:
        follower_count = db.query(models.Follow).filter(
            models.Follow.following_id == c.id
        ).count()
        post_count = db.query(models.Post).filter(
            models.Post.author_id == c.id,
            models.Post.status == "published"
        ).count()
        result.append({
            "id": c.id, "username": c.username,
            "full_name": c.full_name or "",
            "avatar_url": c.avatar_url or "",
            "follower_count": follower_count,
            "post_count": post_count
        })
    return result

# ============================================
# REGIONS
# ============================================
@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        regions = db.query(models.Region).all()
        return [{
            "id": int(r.id), "name": str(r.name) if r.name else "",
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
        } for r in regions]
    except:
        return []

@app.post("/api/regions")
def create_region(
    name: str = Form(...), capital: str = Form(""),
    population: str = Form(""), terrain: str = Form(""),
    description: str = Form(""), category: str = Form(""),
    tags: str = Form(""), hero_image: str = Form(""),
    gallery_images: str = Form(""), audio_files: str = Form(""),
    source: str = Form(""), overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        if not name.strip():
            raise HTTPException(status_code=400, detail="Region name required")
        r = models.Region(
            name=name.strip(), capital=capital.strip(),
            population=population.strip(), terrain=terrain.strip(),
            description=description.strip(),
            overview=overview.strip() or description.strip(),
            category=category.strip(), tags=tags.strip(),
            hero_image=hero_image.strip(), gallery_images=gallery_images.strip(),
            audio_files=audio_files.strip(), source=source.strip()
        )
        db.add(r); db.commit(); db.refresh(r)
        return {"success": True, "region_id": r.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/regions/{region_id}")
def update_region(
    region_id: int, name: str = Form(None), capital: str = Form(None),
    population: str = Form(None), terrain: str = Form(None),
    description: str = Form(None), category: str = Form(None),
    tags: str = Form(None), hero_image: str = Form(None),
    gallery_images: str = Form(None), audio_files: str = Form(None),
    source: str = Form(None), overview: str = Form(None),
    db: Session = Depends(get_db)
):
    try:
        r = db.query(models.Region).filter(models.Region.id == region_id).first()
        if not r:
            raise HTTPException(status_code=404)
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
        if source is not None: r.source = source.strip()
        db.commit(); db.refresh(r)
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
            raise HTTPException(status_code=404)
        db.delete(r); db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# FILE UPLOADS
# ============================================
@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(...),
    category: str = Form("general"), description: str = Form(""),
    region_id: str = Form(""), is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        ext = os.path.splitext(filename)[1].lower()
        safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename.replace(' ','_')}"
        file_path = os.path.join(UPLOAD_DIR, safe_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        uf = models.UploadedFile(
            filename=safe_name, original_name=filename,
            file_path=file_path, file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            category=category,
            region_id=int(region_id) if region_id and region_id.isdigit() else None,
            description=description, uploaded_by="admin",
            is_public=int(is_public) if is_public else 1
        )
        db.add(uf); db.commit(); db.refresh(uf)
        return {
            "success": True, "file_id": uf.id,
            "url": f"/uploads/{safe_name}",
            "filename": safe_name, "original_name": filename,
            "category": category, "size_bytes": len(content),
            "file_size_mb": round(len(content) / (1024 * 1024), 2),
            "mime_type": file.content_type
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files(category: str = "", region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category: q = q.filter(models.UploadedFile.category == category)
        if region_id: q = q.filter(models.UploadedFile.region_id == int(region_id))
        return [{
            "id": f.id, "filename": f.filename,
            "original_name": f.original_name,
            "file_url": f"/uploads/{f.filename}",
            "file_size": f.file_size,
            "file_size_mb": round(f.file_size / (1024 * 1024), 2),
            "mime_type": f.mime_type, "category": f.category,
            "region_id": f.region_id, "description": f.description,
            "created_at": str(f.created_at)
        } for f in q.order_by(models.UploadedFile.created_at.desc()).all()]
    except:
        return []

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    try:
        f = db.query(models.UploadedFile).filter(
            models.UploadedFile.id == file_id
        ).first()
        if not f: raise HTTPException(status_code=404)
        if os.path.exists(f.file_path): os.remove(f.file_path)
        db.delete(f); db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# SECTIONS
# ============================================
@app.post("/api/sections")
def create_section(
    name: str = Form(...), description: str = Form(""),
    display_order: int = Form(0), db: Session = Depends(get_db)
):
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        if db.query(models.Section).filter(models.Section.slug == slug).first():
            raise HTTPException(status_code=400, detail="Already exists")
        s = models.Section(name=name, slug=slug, description=description,
                           display_order=display_order)
        db.add(s); db.commit(); db.refresh(s)
        return {"success": True, "section_id": s.id}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sections")
def get_sections(active_only: int = 1, db: Session = Depends(get_db)):
    try:
        q = db.query(models.Section)
        if active_only:
            q = q.filter(models.Section.is_active == 1).order_by(
                models.Section.display_order)
        return [{"id": s.id, "name": s.name, "slug": s.slug,
                 "description": s.description} for s in q.all()]
    except:
        return []

@app.delete("/api/sections/{section_id}")
def delete_section(section_id: int, db: Session = Depends(get_db)):
    try:
        s = db.query(models.Section).filter(
            models.Section.id == section_id
        ).first()
        if not s: raise HTTPException(status_code=404)
        s.is_active = 0; db.commit()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# CHAT
# ============================================
@app.get("/api/chat")
def get_messages(region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.is_approved == 1)
        if region_id:
            q = q.filter(models.ChatMessage.region_id == int(region_id))
        msgs = q.order_by(models.ChatMessage.created_at.desc()).limit(50).all()
        return [{"id": m.id, "username": m.username, "message": m.message,
                 "region_id": m.region_id, "created_at": str(m.created_at)}
                for m in msgs]
    except:
        return []

@app.post("/api/chat")
async def post_message(
    message: str = Form(...), region_id: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to chat")
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    msg = models.ChatMessage(
        user_id=user.id, username=user.username,
        message=message.strip()[:500],
        region_id=int(region_id) if region_id and region_id.isdigit() else None
    )
    db.add(msg); db.commit(); db.refresh(msg)
    return {"success": True, "id": msg.id,
            "username": msg.username, "message": msg.message}

@app.delete("/api/chat/{message_id}")
async def delete_message(message_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("client_session") or request.cookies.get("admin_session")
    if not token: raise HTTPException(status_code=403)
    msg = db.query(models.ChatMessage).filter(
        models.ChatMessage.id == message_id
    ).first()
    if not msg: raise HTTPException(status_code=404)
    db.delete(msg); db.commit()
    return {"success": True}

# ============================================
# STORIES
# ============================================
@app.post("/api/stories")
async def submit_story(
    title: str = Form(...), content: str = Form(...),
    region_id: str = Form(""), request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401)
    story = models.StorySubmission(
        user_id=user.id, username=user.username,
        title=title.strip(), content=content.strip(),
        region_id=int(region_id) if region_id and region_id.isdigit() else None,
        status="pending"
    )
    db.add(story); db.commit(); db.refresh(story)
    return {"success": True, "story_id": story.id,
            "message": "Story submitted for review!"}

@app.get("/api/stories")
def get_stories(status: str = "approved", db: Session = Depends(get_db)):
    stories = db.query(models.StorySubmission).filter(
        models.StorySubmission.status == status
    ).all()
    return [{
        "id": s.id, "username": s.username, "title": s.title,
        "content": s.content[:200] + "..." if len(s.content) > 200 else s.content,
        "region_id": s.region_id, "status": s.status,
        "created_at": str(s.created_at)
    } for s in stories]

@app.put("/api/stories/{story_id}/approve")
async def approve_story(story_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("client_session") or request.cookies.get("admin_session")
    if not token: raise HTTPException(status_code=403)
    s = db.query(models.StorySubmission).filter(
        models.StorySubmission.id == story_id
    ).first()
    if not s: raise HTTPException(status_code=404)
    s.status = "approved"; db.commit()
    return {"success": True}

@app.put("/api/stories/{story_id}/reject")
async def reject_story(story_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("client_session") or request.cookies.get("admin_session")
    if not token: raise HTTPException(status_code=403)
    s = db.query(models.StorySubmission).filter(
        models.StorySubmission.id == story_id
    ).first()
    if not s: raise HTTPException(status_code=404)
    s.status = "rejected"; db.commit()
    return {"success": True}

# ============================================
# NEWSLETTER
# ============================================
@app.post("/api/newsletter/subscribe")
async def newsletter_subscribe(
    email: str = Form(...), full_name: str = Form(""),
    db: Session = Depends(get_db)
):
    existing = db.query(models.NewsletterSubscriber).filter(
        models.NewsletterSubscriber.email == email.lower()
    ).first()
    if existing:
        return {"success": True, "message": "Already subscribed!"}
    sub = models.NewsletterSubscriber(email=email.lower(), full_name=full_name)
    db.add(sub); db.commit()
    return {"success": True, "message": "Subscribed successfully!"}

@app.get("/api/newsletter/subscribers")
async def get_subscribers(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("client_session") or request.cookies.get("admin_session")
    if not token: raise HTTPException(status_code=403)
    subs = db.query(models.NewsletterSubscriber).filter(
        models.NewsletterSubscriber.is_active == 1
    ).all()
    return [{"id": s.id, "email": s.email, "full_name": s.full_name,
             "created_at": str(s.created_at)} for s in subs]

# ============================================
# EVENTS
# ============================================
@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    events = db.query(models.Event).filter(models.Event.is_active == 1).all()
    return [{"id": e.id, "title": e.title, "description": e.description,
             "event_date": e.event_date, "location": e.location,
             "image_url": e.image_url} for e in events]

@app.post("/api/events")
async def create_event(
    title: str = Form(...), description: str = Form(""),
    event_date: str = Form(""), location: str = Form(""),
    image_url: str = Form(""), request: Request = None,
    db: Session = Depends(get_db)
):
    token = request.cookies.get("client_session") or request.cookies.get("admin_session")
    if not token: raise HTTPException(status_code=403)
    event = models.Event(title=title, description=description,
                         event_date=event_date, location=location,
                         image_url=image_url)
    db.add(event); db.commit(); db.refresh(event)
    return {"success": True, "event_id": event.id}

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("client_session") or request.cookies.get("admin_session")
    if not token: raise HTTPException(status_code=403)
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event: raise HTTPException(status_code=404)
    event.is_active = 0; db.commit()
    return {"success": True}

# ============================================
# STATS
# ============================================
@app.get("/api/stats")
def get_stats(db: Session = Depends(get_db)):
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
    except:
        return {"total_regions": 0, "database_size_mb": 0}

@app.post("/api/theme")
async def save_theme(theme: str = Form(...)):
    try:
        with open("theme.json", "w") as f: f.write(theme)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/theme")
def get_theme():
    try:
        if os.path.exists("theme.json"):
            with open("theme.json", "r") as f: return json.load(f)
        return {}
    except:
        return {}

@app.post("/api/import/json")
def import_json(data: dict, db: Session = Depends(get_db)):
    try:
        if not isinstance(data, list): data = [data]
        imported = 0
        for rd in data:
            try: db.add(models.Region(**rd)); imported += 1
            except: continue
        db.commit()
        return {"success": True, "imported": imported}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# ============================================
# ECHOBOT AI — premium users only on dashboard
# ============================================
@app.post("/api/ai/chat")
async def ai_chat(
    message: str = Form(...),
    region_context: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    try:
        user = get_user_from_request(request, db)
        if not user:
            return {"reply": "Please log in to use EchoBot.", "success": False,
                    "locked": True}
        if not user.is_premium and user.role not in ["superuser", "admin", "creator"]:
            return {
                "reply": "EchoBot is a premium feature. Subscribe to unlock unlimited AI heritage assistance!",
                "success": False,
                "locked": True
            }
        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            return {"reply": "EchoBot is not configured yet. Add HF_TOKEN to environment.",
                    "success": False}
        system_prompt = """You are EchoBot, a friendly and knowledgeable AI heritage guide for Ghana.
You specialise in Ghana's 16 regions, culture, history, traditions, food, music, festivals, and people.
Keep answers concise (3-5 sentences), warm, and educational.
If asked about something unrelated to Ghana or heritage, politely redirect to Ghana topics.
Always respond in English."""
        if region_context:
            system_prompt += f"\n\nThe user is currently viewing the {region_context} region."
        full_prompt = f"<s>[INST] {system_prompt}\n\nUser question: {message} [/INST]"
        payload = json.dumps({
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": 300, "temperature": 0.7,
                "do_sample": True, "return_full_text": False
            }
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2",
            data=payload,
            headers={"Authorization": f"Bearer {hf_token}",
                     "Content-Type": "application/json"},
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
        return {"reply": "EchoBot is warming up! Please try again in a moment.",
                "success": False}
