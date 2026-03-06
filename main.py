from fastapi import FastAPI, Depends, HTTPException, Form, Request
from sqlalchemy.orm import Session
from database import engine, get_db, Base
import models
import hashlib

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# THIS IS THE PART THAT WAS CAUSING THE 404
@app.post("/api/users/register") 
async def user_signup(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # Check if user exists
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = models.User(
        username=username,
        email=email.lower(),
        password_hash=hash_password(password)
    )
    db.add(new_user)
    db.commit()
    return {"success": True}

# ... (Keep your other existing routes below here)
