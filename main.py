from fastapi import FastAPI, Depends, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import hashlib
from database import engine, get_db, Base
import models

# Initialize Database
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Helper for passwords
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# --- NAVIGATION ROUTES ---
@app.get("/")
def home(): return FileResponse("index.html")

@app.get("/app")
def app_view(): return FileResponse("app.html")

@app.get("/signup")
def signup_view(): return FileResponse("signup.html")

@app.get("/admin")
def admin_view(): return FileResponse("admin_dashboard.html")

# --- AUTH & API ROUTES ---
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

@app.get("/api/admin/stats")
def get_stats(db: Session = Depends(get_db)):
    # Simple stats for your dashboard
    return {
        "user_count": db.query(models.User).count()
    }
