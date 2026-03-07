from fastapi import FastAPI, Depends, HTTPException, Form, Request, UploadFile, File, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import os, json, re, hashlib, datetime, shutil, urllib.request
from pathlib import Path

from database import engine, get_db, Base, init_db
import models

init_db()

app = FastAPI(title="EchoStack API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

try:
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
except:
    pass

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def verify_password(p, h): return hash_password(p) == h

# Superuser emails — Emmanuel (developer) always has full access

# ════════════════════════════════════════════════════════════════════════════
# ADMIN SECRET KEY AUTH
# ════════════════════════════════════════════════════════════════════════════
ADMIN_SECRET_KEY = "admin"  # Change this to whatever you want

@app.post("/api/auth/admin")
async def admin_auth(secret: str = Form(...), response: Response = None):
    if secret.lower().strip() == ADMIN_SECRET_KEY:
        resp = JSONResponse(content={"success": True, "message": "Admin access granted"})
        resp.set_cookie(key="admin_session", value=ADMIN_SECRET_KEY,
                       max_age=86400*7, path="/", httponly=False, samesite="lax")
        return resp
    raise HTTPException(status_code=401, detail="Wrong secret key")

@app.post("/api/auth/logout")
async def admin_logout(response: Response):
    resp = JSONResponse(content={"success": True})
    resp.delete_cookie("admin_session")
    resp.delete_cookie("user_session")
    return resp

SUPERUSERS = {"memmanuel06@outlook.com", "admin@echostack.com"}

def get_user_from_request(request: Request, db: Session):
    """Get current user from localStorage token passed as header or cookie."""
    user_id = request.cookies.get("user_session")
    if not user_id:
        return None
    try:
        import uuid as _uuid
        uid = _uuid.UUID(str(user_id))
        user = db.query(models.User).filter(models.User.id == uid).first()
        return user
    except Exception as e:
        print(f"get_user error: {e}")
        return None

def require_role(user, *roles):
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    # Superusers bypass all role checks
    if user.role == "superuser" or user.email in SUPERUSERS:
        return user
    if user.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return user


# ════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ════════════════════════════════════════════════════════════════════════════

def serve(filename):
    if os.path.exists(filename):
        return FileResponse(filename)
    raise HTTPException(status_code=404, detail=f"{filename} not found")

@app.get("/")                 
def home(): return serve("index.html")

@app.get("/signup")           
def signup(): return serve("signup.html")

@app.get("/user-login")       
def user_login_page(): return serve("user-login.html")

@app.get("/dashboard")        
def dashboard(): return serve("dashboard.html")

@app.get("/creator")          
def creator_portal(): return serve("creator.html")

@app.get("/admin")            
def admin_portal(): return serve("admin_dashboard.html")

@app.get("/app")              
def app_page(): return serve("app.html")

@app.get("/echostack-logo.png")
def logo(): return serve("echostack-logo.png")

@app.get("/sw.js")
def sw():
    if os.path.exists("sw.js"):
        return FileResponse("sw.js", media_type="application/javascript",
                            headers={"Service-Worker-Allowed": "/"})
    raise HTTPException(status_code=404)

@app.get("/manifest.json")
def manifest():
    if os.path.exists("manifest.json"):
        with open("manifest.json") as f: return JSONResponse(json.load(f))
    raise HTTPException(status_code=404)


# ════════════════════════════════════════════════════════════════════════════
# AUTH — REGISTER
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/users/register")
async def register(
    username:  str = Form(...),
    email:     str = Form(...),
    password:  str = Form(...),
    interests: str = Form("General"),
    db: Session = Depends(get_db)
):
    try:
        username = username.strip()
        email    = email.lower().strip()
        if len(password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        if db.query(models.User).filter(models.User.email == email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        if db.query(models.User).filter(models.User.username == username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

        # Automatically assign superuser role to developer emails
        role = "superuser" if email in SUPERUSERS else "user"
        plan = "premium" if email in SUPERUSERS else "free"

        user = models.User(
            username=username, email=email,
            password_hash=hash_password(password),
            interests=interests or "General",
            role=role, plan=plan, is_active=True
        )
        db.add(user); db.commit(); db.refresh(user)
        return {"success": True, "id": str(user.id), "username": user.username, "message": "Account created!"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ REGISTER ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# AUTH — LOGIN (supports email OR username, cookie + JSON response)
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/users/login")
async def login(
    email:    str = Form(default=""),
    username: str = Form(default=""),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    login_val = (email or username).lower().strip()
    if not login_val:
        raise HTTPException(status_code=400, detail="Email or username required")
    try:
        user = db.query(models.User).filter(models.User.email == login_val).first()
        if not user:
            user = db.query(models.User).filter(models.User.username == login_val).first()
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="Account suspended")

        # Auto-promote developer email to superuser if not already
        if user.email in SUPERUSERS and user.role != "superuser":
            user.role = "superuser"; user.plan = "premium"; db.commit()

        resp = JSONResponse(content={
            "success":  True,
            "id":       str(user.id),
            "username": user.username,
            "email":    user.email,
            "role":     user.role,
            "plan":     user.plan,
            "loggedIn": True
        })
        resp.set_cookie(key="user_session", value=str(user.id),
                        max_age=86400*7, path="/", httponly=False, samesite="lax")
        return resp
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ LOGIN ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/logout")
def logout(response: Response):
    response.delete_cookie("user_session")
    return {"success": True}


@app.get("/api/users/me")
async def me(request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    return {
        "id": user.id, "username": user.username, "email": user.email,
        "role": user.role, "plan": user.plan, "full_name": user.full_name or "",
        "bio": user.bio or "", "avatar_url": user.avatar_url or "",
        "interests": user.interests or "", "channel_name": user.channel_name or "",
        "channel_desc": user.channel_desc or "", "follower_count": user.follower_count,
        "post_count": user.post_count, "created_at": str(user.created_at)
    }


# ════════════════════════════════════════════════════════════════════════════
# ADMIN AUTH (secret answer for admin dashboard)
# ════════════════════════════════════════════════════════════════════════════

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "THE ADMIN")

@app.post("/api/auth/login")
async def admin_login(answer: str = Form(...)):
    if answer.strip().upper() != ADMIN_SECRET.upper():
        raise HTTPException(status_code=403, detail="Wrong answer")
    resp = JSONResponse(content={"success": True})
    resp.set_cookie(key="admin_session", value="ADMIN_AUTHORIZED",
                    max_age=86400, path="/", httponly=False)
    return resp

@app.post("/api/auth/logout")
def admin_logout(response: Response):
    response.delete_cookie("admin_session")
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════════
# CREATOR — UPGRADE & MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/users/become-creator")
async def become_creator(
    channel_name: str = Form(...),
    channel_desc: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")
    if user.role in ("admin", "superuser"):
        raise HTTPException(status_code=400, detail="Admins don't need creator accounts")
    user.role = "creator"
    user.plan = "premium"
    user.channel_name = channel_name.strip()
    user.channel_desc = channel_desc.strip()
    user.creator_since = datetime.datetime.utcnow()
    db.commit()
    return {"success": True, "message": "You are now a creator!", "role": "creator"}


@app.get("/api/creators")
def get_creators(db: Session = Depends(get_db)):
    creators = db.query(models.User).filter(
        models.User.role.in_(["creator", "superuser"]),
        models.User.is_active == True
    ).all()
    return [{
        "id": c.id, "username": c.username,
        "channel_name": c.channel_name or c.username,
        "channel_desc": c.channel_desc or "",
        "avatar_url": c.avatar_url or "",
        "follower_count": c.follower_count,
        "post_count": c.post_count
    } for c in creators]


# ════════════════════════════════════════════════════════════════════════════
# POSTS
# ════════════════════════════════════════════════════════════════════════════

def make_slug(title, post_id=None):
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')[:80]
    if post_id:
        slug = f"{slug}-{post_id}"
    return slug

@app.get("/api/posts")
def get_posts(
    status: str = "published",
    author_id: int = None,
    content_type: str = "",
    limit: int = 20,
    db: Session = Depends(get_db)
):
    try:
        q = db.query(models.Post)
        if status != "all": q = q.filter(models.Post.status == status)
        if author_id: q = q.filter(models.Post.author_id == author_id)
        if content_type: q = q.filter(models.Post.content_type == content_type)
        posts = q.order_by(models.Post.created_at.desc()).limit(limit).all()
        return [{
            "id": p.id, "title": p.title, "slug": p.slug,
            "excerpt": p.excerpt or p.content[:150] + "..." if p.content else "",
            "cover_image": p.cover_image or "", "content_type": p.content_type,
            "audio_url": p.audio_url or "", "video_url": p.video_url or "",
            "tags": p.tags or "", "status": p.status, "is_premium": p.is_premium,
            "view_count": p.view_count, "like_count": p.like_count,
            "comment_count": p.comment_count,
            "author_id": str(p.author_id),
            "author_username": p.author.username if p.author else "",
            "author_channel": p.author.channel_name if p.author else "",
            "published_at": str(p.published_at) if p.published_at else "",
            "created_at": str(p.created_at)
        } for p in posts]
    except Exception as e:
        print(f"❌ GET POSTS: {e}")
        return []

@app.get("/api/posts/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(status_code=404, detail="Post not found")
    p.view_count += 1; db.commit()
    return {
        "id": p.id, "title": p.title, "slug": p.slug, "content": p.content,
        "excerpt": p.excerpt or "", "cover_image": p.cover_image or "",
        "content_type": p.content_type, "audio_url": p.audio_url or "",
        "video_url": p.video_url or "", "gallery": p.gallery or "",
        "tags": p.tags or "", "status": p.status, "is_premium": p.is_premium,
        "view_count": p.view_count, "like_count": p.like_count,
        "comment_count": p.comment_count, "author_id": str(p.author_id),
        "author_username": p.author.username if p.author else "",
        "author_channel": p.author.channel_name if p.author else "",
        "published_at": str(p.published_at) if p.published_at else "",
        "created_at": str(p.created_at)
    }

@app.post("/api/posts")
async def create_post(
    title:        str = Form(...),
    content:      str = Form(""),
    excerpt:      str = Form(""),
    cover_image:  str = Form(""),
    content_type: str = Form("article"),
    audio_url:    str = Form(""),
    video_url:    str = Form(""),
    gallery:      str = Form(""),
    tags:         str = Form(""),
    is_premium:   str = Form("0"),
    status:       str = Form("draft"),
    region_id:    str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    require_role(user, "creator", "admin", "superuser")
    try:
        post = models.Post(
            author_id=user.id, title=title.strip(),
            content=content, excerpt=excerpt,
            cover_image=cover_image, content_type=content_type,
            audio_url=audio_url, video_url=video_url,
            gallery=gallery, tags=tags,
            is_premium=(is_premium == "1"),
            status=status,
            region_id=int(region_id) if region_id.isdigit() else None,
            published_at=datetime.datetime.utcnow() if status == "published" else None
        )
        db.add(post); db.commit(); db.refresh(post)
        post.slug = make_slug(title, post.id)
        user.post_count = db.query(models.Post).filter(models.Post.author_id == user.id).count()
        db.commit()
        return {"success": True, "id": post.id, "slug": post.slug}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/posts/{post_id}")
async def update_post(
    post_id: int,
    title:        str = Form(None),
    content:      str = Form(None),
    excerpt:      str = Form(None),
    cover_image:  str = Form(None),
    audio_url:    str = Form(None),
    video_url:    str = Form(None),
    gallery:      str = Form(None),
    tags:         str = Form(None),
    is_premium:   str = Form(None),
    status:       str = Form(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    require_role(user, "creator", "admin", "superuser")
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(status_code=404)
    # Only author, admin or superuser can edit
    if p.author_id != user.id and user.role not in ("admin", "superuser"):
        raise HTTPException(status_code=403, detail="Not your post")
    try:
        if title is not None: p.title = title.strip(); p.slug = make_slug(title, post_id)
        if content is not None: p.content = content
        if excerpt is not None: p.excerpt = excerpt
        if cover_image is not None: p.cover_image = cover_image
        if audio_url is not None: p.audio_url = audio_url
        if video_url is not None: p.video_url = video_url
        if gallery is not None: p.gallery = gallery
        if tags is not None: p.tags = tags
        if is_premium is not None: p.is_premium = (is_premium == "1")
        if status is not None:
            p.status = status
            if status == "published" and not p.published_at:
                p.published_at = datetime.datetime.utcnow()
        p.updated_at = datetime.datetime.utcnow()
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/posts/{post_id}")
async def delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    require_role(user, "creator", "admin", "superuser")
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(status_code=404)
    if p.author_id != user.id and user.role not in ("admin", "superuser"):
        raise HTTPException(status_code=403, detail="Not your post")
    try:
        db.delete(p); db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# COMMENTS
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(models.Comment).filter(
        models.Comment.post_id == post_id,
        models.Comment.is_approved == True
    ).order_by(models.Comment.created_at.asc()).all()
    return [{
        "id": c.id, "content": c.content,
        "author_username": c.author.username if c.author else "Anonymous",
        "author_avatar": c.author.avatar_url if c.author else "",
        "created_at": str(c.created_at)
    } for c in comments]

@app.post("/api/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    content: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    user = get_user_from_request(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Must be logged in to comment")
    try:
        comment = models.Comment(post_id=post_id, author_id=user.id, content=content.strip())
        db.add(comment)
        post = db.query(models.Post).filter(models.Post.id == post_id).first()
        if post: post.comment_count += 1
        db.commit(); db.refresh(comment)
        return {"success": True, "id": comment.id}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/comments/{comment_id}")
async def delete_comment(comment_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    require_role(user, "admin", "superuser", "creator", "user")
    c = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if not c: raise HTTPException(status_code=404)
    if c.author_id != user.id and user.role not in ("admin", "superuser"):
        raise HTTPException(status_code=403)
    try:
        db.delete(c); db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# FOLLOWS
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/follow/{creator_id}")
async def follow(creator_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user: raise HTTPException(status_code=401)
    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == user.id,
        models.Follow.creator_id == _uuid.UUID(str(creator_id))
    ).first()
    if existing:
        db.delete(existing)
        creator = db.query(models.User).filter(models.User.id == creator_id).first()
        if creator: creator.follower_count = max(0, creator.follower_count - 1)
        db.commit()
        return {"success": True, "following": False}
    import uuid as _uuid2
    follow = models.Follow(follower_id=user.id, creator_id=_uuid2.UUID(str(creator_id)))
    db.add(follow)
    creator = db.query(models.User).filter(models.User.id == creator_id).first()
    if creator: creator.follower_count += 1
    db.commit()
    return {"success": True, "following": True}

@app.get("/api/follow/{creator_id}/status")
async def follow_status(creator_id: str, request: Request, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user: return {"following": False}
    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == user.id,
        models.Follow.creator_id == _uuid.UUID(str(creator_id))
    ).first()
    return {"following": bool(existing)}


# ════════════════════════════════════════════════════════════════════════════
# ADMIN — USER MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/admin/users")
async def admin_get_users(request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin", "superuser")):
        raise HTTPException(status_code=403)
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    result = []
    for u in users:
        try:
            result.append({
                "id": u.id, "username": u.username, "email": u.email,
                "role": getattr(u, 'role', 'user') or 'user',
                "plan": getattr(u, 'plan', 'free') or 'free',
                "is_active": getattr(u, 'is_active', True),
                "is_premium": getattr(u, 'is_premium', 0) or 0,
                "full_name": getattr(u, 'full_name', '') or '',
                "follower_count": getattr(u, 'follower_count', 0) or 0,
                "post_count": getattr(u, 'post_count', 0) or 0,
                "created_at": str(u.created_at)
            })
        except Exception:
            result.append({
                "id": u.id, "username": u.username, "email": u.email,
                "role": "user", "plan": "free", "is_active": True,
                "is_premium": 0, "full_name": "", "follower_count": 0,
                "post_count": 0, "created_at": str(u.created_at)
            })
    return result

@app.put("/api/admin/users/{user_id}/role")
async def set_role(
    user_id: str, role: str = Form(...),
    request: Request = None, db: Session = Depends(get_db)
):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin", "superuser")):
        raise HTTPException(status_code=403)
    import uuid as _u
    target = db.query(models.User).filter(models.User.id == _u.UUID(str(user_id))).first()
    if not target: raise HTTPException(status_code=404)
    if role not in ("user", "creator", "admin", "superuser"):
        raise HTTPException(status_code=400, detail="Invalid role")
    target.role = role
    if role in ("creator", "admin", "superuser"): target.plan = "premium"
    db.commit()
    return {"success": True, "role": role}

@app.put("/api/admin/users/{user_id}/suspend")
async def suspend_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin", "superuser")):
        raise HTTPException(status_code=403)
    import uuid as _u
    target = db.query(models.User).filter(models.User.id == _u.UUID(str(user_id))).first()
    if not target: raise HTTPException(status_code=404)
    target.is_active = not target.is_active
    db.commit()
    return {"success": True, "is_active": target.is_active}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: str, request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin", "superuser")):
        raise HTTPException(status_code=403)
    import uuid as _u
    target = db.query(models.User).filter(models.User.id == _u.UUID(str(user_id))).first()
    if not target: raise HTTPException(status_code=404)
    if target.role == "superuser": raise HTTPException(status_code=403, detail="Cannot delete superuser")
    try:
        db.delete(target); db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/admin/posts/{post_id}/status")
async def admin_post_status(
    post_id: int, status: str = Form(...),
    request: Request = None, db: Session = Depends(get_db)
):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin", "superuser")):
        raise HTTPException(status_code=403)
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(status_code=404)
    p.status = status
    if status == "published" and not p.published_at:
        p.published_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True}


# ════════════════════════════════════════════════════════════════════════════
# STATS
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    try:
        return {
            "total_regions":  db.query(models.Region).count(),
            "total_users":    db.query(models.User).filter(models.User.role == "user").count(),
            "total_creators": db.query(models.User).filter(models.User.role == "creator").count(),
            "total_posts":    db.query(models.Post).filter(models.Post.status == "published").count(),
            "total_comments": db.query(models.Comment).count(),
            "total_follows":  db.query(models.Follow).count(),
            "with_audio":     db.query(models.UploadedFile).filter(models.UploadedFile.category == "audio").count(),
            "with_images":    db.query(models.UploadedFile).filter(models.UploadedFile.category == "image").count(),
            "file_count":     db.query(models.UploadedFile).count(),
            "user_count":     db.query(models.User).count(),
            "database_size_mb": 0
        }
    except Exception as e:
        print(f"❌ STATS: {e}")
        return {"total_regions": 0, "total_users": 0, "total_posts": 0}


# ════════════════════════════════════════════════════════════════════════════
# REGIONS
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/regions")
def get_regions(db: Session = Depends(get_db)):
    try:
        return [{
            "id": r.id, "name": r.name or "", "capital": r.capital or "",
            "population": r.population or "", "terrain": r.terrain or "",
            "description": r.description or "", "overview": r.overview or "",
            "category": r.category or "", "tags": r.tags or "",
            "hero_image": r.hero_image or "", "gallery_images": r.gallery_images or "",
            "audio_files": r.audio_files or "", "source": r.source or ""
        } for r in db.query(models.Region).all()]
    except:
        return []

@app.get("/api/regions/{region_id}")
def get_region(region_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not r: raise HTTPException(status_code=404)
    return {"id": r.id, "name": r.name, "capital": r.capital or "",
            "description": r.description or "", "overview": r.overview or "",
            "hero_image": r.hero_image or "", "gallery_images": r.gallery_images or "",
            "audio_files": r.audio_files or "", "tags": r.tags or ""}

@app.post("/api/regions")
def create_region(
    name: str = Form(...), capital: str = Form(""), population: str = Form(""),
    terrain: str = Form(""), description: str = Form(""), category: str = Form(""),
    tags: str = Form(""), hero_image: str = Form(""), gallery_images: str = Form(""),
    audio_files: str = Form(""), source: str = Form(""), overview: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        r = models.Region(name=name.strip(), capital=capital.strip(), population=population,
                          terrain=terrain, description=description, overview=overview or description,
                          category=category, tags=tags, hero_image=hero_image,
                          gallery_images=gallery_images, audio_files=audio_files, source=source)
        db.add(r); db.commit(); db.refresh(r)
        return {"success": True, "id": r.id}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/regions/{region_id}")
def update_region(
    region_id: int, name: str = Form(None), capital: str = Form(None),
    population: str = Form(None), terrain: str = Form(None), description: str = Form(None),
    category: str = Form(None), tags: str = Form(None), hero_image: str = Form(None),
    gallery_images: str = Form(None), audio_files: str = Form(None),
    source: str = Form(None), overview: str = Form(None), db: Session = Depends(get_db)
):
    r = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not r: raise HTTPException(status_code=404)
    try:
        if name is not None: r.name = name.strip()
        if capital is not None: r.capital = capital
        if population is not None: r.population = population
        if terrain is not None: r.terrain = terrain
        if description is not None: r.description = description
        if overview is not None: r.overview = overview
        if category is not None: r.category = category
        if tags is not None: r.tags = tags
        if hero_image is not None: r.hero_image = hero_image
        if gallery_images is not None: r.gallery_images = gallery_images
        if audio_files is not None: r.audio_files = audio_files
        if source is not None: r.source = source
        db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/regions/{region_id}")
def delete_region(region_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Region).filter(models.Region.id == region_id).first()
    if not r: raise HTTPException(status_code=404)
    try:
        db.delete(r); db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# FILE UPLOADS
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/upload/file")
async def upload_file(
    file: UploadFile = File(...), filename: str = Form(""),
    category: str = Form("general"), description: str = Form(""),
    region_id: str = Form(""), is_public: str = Form("1"),
    db: Session = Depends(get_db)
):
    try:
        ext = Path(file.filename).suffix.lower()
        safe = f"{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}{ext or '.bin'}"
        dest = UPLOAD_DIR / safe
        content = await file.read()
        dest.write_bytes(content)
        size_mb = round(len(content) / (1024*1024), 2)
        uf = models.UploadedFile(
            filename=safe, original_name=file.filename or filename,
            file_path=str(dest), file_url=f"/uploads/{safe}",
            file_size=len(content), file_size_mb=size_mb,
            mime_type=file.content_type or "", category=category,
            description=description, is_public=(is_public == "1"),
            region_id=int(region_id) if region_id.isdigit() else None
        )
        db.add(uf); db.commit(); db.refresh(uf)
        return {"success": True, "url": f"/uploads/{safe}", "file_size_mb": size_mb,
                "original_name": file.filename, "category": category}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/files")
def get_files(category: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.UploadedFile)
        if category: q = q.filter(models.UploadedFile.category == category)
        return [{"id": f.id, "filename": f.filename, "original_name": f.original_name,
                 "file_url": f.file_url or f"/uploads/{f.filename}",
                 "file_size_mb": f.file_size_mb or 0, "category": f.category,
                 "created_at": str(f.created_at)} for f in q.order_by(models.UploadedFile.created_at.desc()).all()]
    except:
        return []

@app.delete("/api/files/{file_id}")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not f: raise HTTPException(status_code=404)
    try:
        if f.file_path and Path(f.file_path).exists(): Path(f.file_path).unlink()
        db.delete(f); db.commit(); return {"success": True}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/publish-file")
async def admin_publish_file(
    file_id: int = Form(...),
    title: str = Form(""),
    excerpt: str = Form(""),
    status: str = Form("published"),
    is_premium: str = Form("0"),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Create a Post from an uploaded file so it appears in the news feed."""
    # Require admin session or admin/superuser role
    admin_cookie = request.cookies.get("admin_session", "") if request else ""
    user = get_user_from_request(request, db) if request else None
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin", "superuser")):
        raise HTTPException(status_code=403, detail="Admin access required")

    f = db.query(models.UploadedFile).filter(models.UploadedFile.id == file_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")

    try:
        file_url = f.file_url or f"/uploads/{f.filename}"
        mime = f.mime_type or ""

        # Determine content type from mime / category
        if mime.startswith("video/") or f.category == "video":
            content_type = "video"
            cover_image = ""
            content = f"[video]{file_url}[/video]"
        elif mime.startswith("audio/") or f.category == "audio":
            content_type = "audio"
            cover_image = ""
            content = f"[audio]{file_url}[/audio]"
        elif mime.startswith("image/") or f.category == "image":
            content_type = "photo_essay"
            cover_image = file_url
            content = f"![{f.original_name}]({file_url})"
        else:
            content_type = "article"
            cover_image = ""
            content = f"[Download / View file]({file_url})"

        post_title = title.strip() if title.strip() else (f.original_name or f.filename or "Untitled Upload")
        post_excerpt = excerpt.strip() if excerpt.strip() else (f.description or f"Uploaded {f.category or 'file'} — {f.original_name}")

        # Use admin user or find/create a system admin user
        author = user
        if not author:
            author = db.query(models.User).filter(
                models.User.role.in_(["admin", "superuser"])
            ).first()
        if not author:
            raise HTTPException(status_code=500, detail="No admin user found to author post")

        post = models.Post(
            author_id=author.id,
            title=post_title,
            excerpt=post_excerpt,
            content=content,
            cover_image=cover_image,
            content_type=content_type,
            status=status,
            is_premium=(is_premium == "1"),
            region_id=f.region_id,
            published_at=datetime.datetime.utcnow() if status == "published" else None
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        post.slug = make_slug(post_title, post.id)
        db.commit()

        return {"success": True, "post_id": post.id, "status": status, "content_type": content_type}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ════════════════════════════════════════════════════════════════════════════
# SECTIONS, CHAT, STORIES, NEWSLETTER, EVENTS (kept from original)
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/sections")
def get_sections(db: Session = Depends(get_db)):
    try:
        return [{"id": s.id, "name": s.name, "slug": s.slug} for s in
                db.query(models.Section).filter(models.Section.is_active == True).order_by(models.Section.display_order).all()]
    except: return []

@app.post("/api/sections")
def create_section(name: str = Form(...), description: str = Form(""), db: Session = Depends(get_db)):
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        if db.query(models.Section).filter(models.Section.slug == slug).first():
            raise HTTPException(status_code=400, detail="Already exists")
        s = models.Section(name=name, slug=slug, description=description)
        db.add(s); db.commit(); db.refresh(s)
        return {"success": True, "id": s.id}
    except HTTPException: raise
    except Exception as e: db.rollback(); raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/sections/{sid}")
def delete_section(sid: int, db: Session = Depends(get_db)):
    s = db.query(models.Section).filter(models.Section.id == sid).first()
    if not s: raise HTTPException(status_code=404)
    s.is_active = False; db.commit(); return {"success": True}

@app.get("/api/chat")
def get_chat(region_id: str = "", db: Session = Depends(get_db)):
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.is_approved == True)
        if region_id and region_id.isdigit(): q = q.filter(models.ChatMessage.region_id == int(region_id))
        return [{"id": m.id, "username": m.username, "message": m.message,
                 "region_id": m.region_id, "created_at": str(m.created_at)}
                for m in q.order_by(models.ChatMessage.created_at.desc()).limit(50).all()]
    except: return []

@app.post("/api/chat")
async def post_chat(message: str = Form(...), region_id: str = Form(""), request: Request = None, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user: raise HTTPException(status_code=401, detail="Must be logged in")
    msg = models.ChatMessage(user_id=user.id, username=user.username, message=message.strip()[:500],
                              region_id=int(region_id) if region_id.isdigit() else None)
    db.add(msg); db.commit(); db.refresh(msg)
    return {"success": True, "id": msg.id, "username": msg.username, "message": msg.message}

@app.get("/api/stories")
def get_stories(status: str = "approved", db: Session = Depends(get_db)):
    stories = db.query(models.StorySubmission).filter(models.StorySubmission.status == status).all()
    return [{"id": s.id, "username": s.username, "title": s.title,
             "content": s.content[:200], "status": s.status, "created_at": str(s.created_at)} for s in stories]

@app.post("/api/stories")
async def post_story(title: str = Form(...), content: str = Form(...), region_id: str = Form(""),
                     request: Request = None, db: Session = Depends(get_db)):
    user = get_user_from_request(request, db)
    if not user: raise HTTPException(status_code=401)
    s = models.StorySubmission(user_id=user.id, username=user.username,
                                title=title, content=content, status="pending",
                                region_id=int(region_id) if region_id.isdigit() else None)
    db.add(s); db.commit()
    return {"success": True, "message": "Story submitted for review!"}

@app.put("/api/stories/{sid}/approve")
async def approve_story(sid: int, request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin","superuser")):
        raise HTTPException(status_code=403)
    s = db.query(models.StorySubmission).filter(models.StorySubmission.id == sid).first()
    if not s: raise HTTPException(status_code=404)
    s.status = "approved"; db.commit(); return {"success": True}

@app.put("/api/stories/{sid}/reject")
async def reject_story(sid: int, request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin","superuser")):
        raise HTTPException(status_code=403)
    s = db.query(models.StorySubmission).filter(models.StorySubmission.id == sid).first()
    if not s: raise HTTPException(status_code=404)
    s.status = "rejected"; db.commit(); return {"success": True}

@app.post("/api/newsletter/subscribe")
async def newsletter_sub(email: str = Form(...), full_name: str = Form(""), db: Session = Depends(get_db)):
    existing = db.query(models.NewsletterSubscriber).filter(models.NewsletterSubscriber.email == email.lower()).first()
    if existing: return {"success": True, "message": "Already subscribed!"}
    db.add(models.NewsletterSubscriber(email=email.lower(), full_name=full_name))
    db.commit(); return {"success": True}

@app.get("/api/newsletter/subscribers")
async def get_subs(request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin","superuser","creator")):
        raise HTTPException(status_code=403)
    return [{"id": s.id, "email": s.email, "full_name": s.full_name, "created_at": str(s.subscribed_at)}
            for s in db.query(models.NewsletterSubscriber).filter(models.NewsletterSubscriber.is_active == True).all()]

@app.get("/api/events")
def get_events(db: Session = Depends(get_db)):
    return [{"id": e.id, "title": e.title, "description": e.description,
             "event_date": e.event_date, "location": e.location, "image_url": e.image_url}
            for e in db.query(models.Event).filter(models.Event.is_active == True).all()]

@app.post("/api/events")
async def create_event(title: str = Form(...), description: str = Form(""), event_date: str = Form(""),
                        location: str = Form(""), image_url: str = Form(""),
                        request: Request = None, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin","superuser")):
        raise HTTPException(status_code=403)
    e = models.Event(title=title, description=description, event_date=event_date, location=location, image_url=image_url)
    db.add(e); db.commit(); db.refresh(e)
    return {"success": True, "id": e.id}

@app.get("/api/theme")
def get_theme():
    try:
        if os.path.exists("theme.json"):
            with open("theme.json") as f: return json.load(f)
        return {}
    except: return {}

@app.post("/api/theme")
async def save_theme(request: Request):
    try:
        body = await request.json()
        with open("theme.json", "w") as f: json.dump(body, f)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/import/json")
async def import_json(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        if not isinstance(data, list): data = [data]
        count = 0
        for rd in data:
            try:
                db.add(models.Region(
                    name=rd.get("name",""), capital=rd.get("capital",""),
                    description=rd.get("description",""), overview=rd.get("overview",""),
                    category=rd.get("category",""), tags=rd.get("tags",""),
                    hero_image=rd.get("hero_image",""), gallery_images=rd.get("gallery_images",""),
                    audio_files=rd.get("audio_files",""), source=rd.get("source","")
                )); count += 1
            except: continue
        db.commit()
        return {"success": True, "imported": count}
    except Exception as e:
        db.rollback(); raise HTTPException(status_code=500, detail=str(e))



# ════════════════════════════════════════════════════════════════════════════
# ADMIN — EXTRA ENDPOINTS (post edit, user edit, homepage settings, etc.)
# ════════════════════════════════════════════════════════════════════════════

def is_admin(request: Request):
    return request.cookies.get("admin_session") == "ADMIN_AUTHORIZED"

@app.get("/api/admin/posts")
async def admin_get_posts(request: Request, status: str = "all", limit: int = 200, db: Session = Depends(get_db)):
    if not is_admin(request): raise HTTPException(status_code=403)
    q = db.query(models.Post)
    if status != "all": q = q.filter(models.Post.status == status)
    posts = q.order_by(models.Post.created_at.desc()).limit(limit).all()
    return [{
        "id": p.id, "title": p.title, "excerpt": p.excerpt or "",
        "content": p.content or "", "cover_image": p.cover_image or "",
        "content_type": p.content_type, "audio_url": p.audio_url or "",
        "video_url": p.video_url or "", "tags": p.tags or "",
        "status": p.status, "is_premium": p.is_premium,
        "view_count": p.view_count, "like_count": p.like_count,
        "comment_count": p.comment_count,
        "author_id": str(p.author_id),
        "author_username": p.author.username if p.author else "",
        "created_at": str(p.created_at)
    } for p in posts]

@app.put("/api/admin/posts/{post_id}")
async def admin_update_post(
    post_id: int, title: str = Form(None), content: str = Form(None),
    excerpt: str = Form(None), cover_image: str = Form(None),
    audio_url: str = Form(None), video_url: str = Form(None),
    tags: str = Form(None), is_premium: str = Form(None),
    status: str = Form(None), request: Request = None, db: Session = Depends(get_db)
):
    if not is_admin(request): raise HTTPException(status_code=403)
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(status_code=404)
    if title is not None: p.title = title.strip()
    if content is not None: p.content = content
    if excerpt is not None: p.excerpt = excerpt
    if cover_image is not None: p.cover_image = cover_image
    if audio_url is not None: p.audio_url = audio_url
    if video_url is not None: p.video_url = video_url
    if tags is not None: p.tags = tags
    if is_premium is not None: p.is_premium = (is_premium == "1")
    if status is not None:
        p.status = status
        if status == "published" and not p.published_at:
            p.published_at = datetime.datetime.utcnow()
    p.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True}

@app.delete("/api/admin/posts/{post_id}")
async def admin_delete_post(post_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request): raise HTTPException(status_code=403)
    p = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not p: raise HTTPException(status_code=404)
    db.delete(p); db.commit()
    return {"success": True}

@app.get("/api/admin/comments")
async def admin_get_comments(request: Request, db: Session = Depends(get_db)):
    if not is_admin(request): raise HTTPException(status_code=403)
    comments = db.query(models.Comment).order_by(models.Comment.created_at.desc()).limit(200).all()
    return [{"id": c.id, "content": c.content, "post_id": c.post_id,
             "author": c.author.username if c.author else "?", "created_at": str(c.created_at)} for c in comments]

@app.delete("/api/admin/comments/{cid}")
async def admin_del_comment(cid: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin(request): raise HTTPException(status_code=403)
    c = db.query(models.Comment).filter(models.Comment.id == cid).first()
    if not c: raise HTTPException(status_code=404)
    db.delete(c); db.commit()
    return {"success": True}

@app.put("/api/admin/users/{user_id}/edit")
async def admin_edit_user(
    user_id: str, full_name: str = Form(None), bio: str = Form(None),
    avatar_url: str = Form(None), plan: str = Form(None),
    request: Request = None, db: Session = Depends(get_db)
):
    if not is_admin(request): raise HTTPException(status_code=403)
    import uuid as _u
    u = db.query(models.User).filter(models.User.id == _u.UUID(str(user_id))).first()
    if not u: raise HTTPException(status_code=404)
    if full_name is not None: u.full_name = full_name
    if bio is not None: u.bio = bio
    if avatar_url is not None: u.avatar_url = avatar_url
    if plan is not None: u.plan = plan
    db.commit()
    return {"success": True}

@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int, request: Request, db: Session = Depends(get_db)):
    admin_cookie = request.cookies.get("admin_session")
    user = get_user_from_request(request, db)
    if admin_cookie != "ADMIN_AUTHORIZED" and (not user or user.role not in ("admin","superuser")):
        raise HTTPException(status_code=403)
    e = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not e: raise HTTPException(status_code=404)
    e.is_active = False; db.commit()
    return {"success": True}

@app.post("/api/admin/create-post")
async def admin_create_post(
    title: str = Form(...), content: str = Form(""), excerpt: str = Form(""),
    cover_image: str = Form(""), content_type: str = Form("article"),
    audio_url: str = Form(""), video_url: str = Form(""), tags: str = Form(""),
    is_premium: str = Form("0"), status: str = Form("published"),
    author_username: str = Form(""),
    request: Request = None, db: Session = Depends(get_db)
):
    if not is_admin(request): raise HTTPException(status_code=403)
    # Find author by username or use first superuser
    author = None
    if author_username:
        author = db.query(models.User).filter(models.User.username == author_username).first()
    if not author:
        author = db.query(models.User).filter(models.User.role == "superuser").first()
    if not author:
        author = db.query(models.User).first()
    if not author:
        raise HTTPException(status_code=400, detail="No users exist yet. Create a user account first.")
    p = models.Post(
        author_id=author.id, title=title.strip(), content=content,
        excerpt=excerpt, cover_image=cover_image, content_type=content_type,
        audio_url=audio_url, video_url=video_url, tags=tags,
        is_premium=(is_premium=="1"), status=status,
        published_at=datetime.datetime.utcnow() if status=="published" else None
    )
    db.add(p); db.commit(); db.refresh(p)
    p.slug = re.sub(r"[^a-z0-9]+","-",title.lower()).strip("-")[:80] + f"-{p.id}"
    db.commit()
    return {"success": True, "id": p.id}

# ════════════════════════════════════════════════════════════════════════════
# ECHOBOT AI (Hugging Face — kept from original)
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/ai/chat")
async def ai_chat(
    message: str = Form(...),
    region_context: str = Form(""),
    request: Request = None,
    db: Session = Depends(get_db)
):
    try:
        hf_token = os.environ.get("HF_TOKEN", "")
        if not hf_token:
            return {"reply": "EchoBot is not configured yet. Ask the admin to add HF_TOKEN to the server environment.", "success": False}

        # Check premium — admins always get access
        user = get_user_from_request(request, db) if request else None
        admin_cookie = request.cookies.get("admin_session", "") if request else ""
        is_premium = (
            admin_cookie == "ADMIN_AUTHORIZED"
            or (user and (user.is_premium or user.role in ("admin", "superuser", "creator")))
        )
        if not is_premium:
            return {
                "reply": "EchoBot is a Premium feature. Upgrade to GH₵150/month to unlock full AI heritage responses.",
                "success": False, "locked": True
            }

        system_prompt = (
            "You are EchoBot, a friendly and knowledgeable AI heritage guide for Ghana. "
            "You specialise in Ghana's 16 regions, culture, history, traditions, food, music, festivals, and people. "
            "Keep answers concise (3-5 sentences), warm, and educational. Always respond in English."
        )
        if region_context:
            system_prompt += f" The user is currently viewing the {region_context} region on the heritage map."

        # Build prompt in Mistral instruct format
        prompt = f"<s>[INST] <<SYS>>\n{system_prompt}\n<</SYS>>\n\n{message} [/INST]"

        # Try primary model first, fall back to smaller model if loading
        models_to_try = [
            "mistralai/Mistral-7B-Instruct-v0.2",
            "HuggingFaceH4/zephyr-7b-beta",
            "microsoft/phi-2",
        ]

        last_error = ""
        for model_id in models_to_try:
            try:
                payload = json.dumps({
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": 300,
                        "temperature": 0.7,
                        "return_full_text": False,
                        "do_sample": True
                    },
                    "options": {"wait_for_model": True, "use_cache": False}
                }).encode("utf-8")

                req = urllib.request.Request(
                    f"https://api-inference.huggingface.co/models/{model_id}",
                    data=payload,
                    headers={
                        "Authorization": f"Bearer {hf_token}",
                        "Content-Type": "application/json"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=45) as r:
                    raw = r.read().decode("utf-8")
                    result = json.loads(raw)

                # Handle model-loading response
                if isinstance(result, dict) and result.get("error", "").lower().startswith("loading"):
                    last_error = "loading"
                    continue

                if isinstance(result, list) and result:
                    reply = result[0].get("generated_text", "").strip()
                    if reply:
                        # Clean up any repeated prompt leakage
                        if "[/INST]" in reply:
                            reply = reply.split("[/INST]")[-1].strip()
                        return {"reply": reply, "success": True}

                last_error = f"empty response from {model_id}"
                continue

            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", errors="ignore")
                print(f"HF HTTPError {model_id}: {e.code} {body[:200]}")
                if e.code == 503:
                    last_error = "loading"
                    continue
                last_error = f"HTTP {e.code}"
                continue
            except Exception as ex:
                last_error = str(ex)
                print(f"AI model error {model_id}: {ex}")
                continue

        # All models failed
        if last_error == "loading":
            return {
                "reply": "⏳ EchoBot's AI model is warming up (this takes ~20 seconds on first use). Please click Retry in a moment!",
                "success": False, "warming": True
            }
        return {
            "reply": "⚠️ EchoBot couldn't get a response right now. Please try again in a few seconds.",
            "success": False
        }

    except Exception as e:
        print(f"AI chat outer error: {e}")
        return {"reply": "⚠️ Something went wrong. Please try again!", "success": False}
