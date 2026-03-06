from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./echostack.db")

# Fix Render/Supabase URL format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite needs special arg, PostgreSQL does not
if "sqlite" in DATABASE_URL:
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,        # auto-reconnect if connection drops
        pool_recycle=300,          # recycle connections every 5 minutes
        pool_size=5,               # max 5 connections (safe for free tier)
        max_overflow=2             # allow 2 extra connections if needed
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### 📄 `requirements.txt`
```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
python-multipart
aiofiles
