from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./echostack.db")

# Fix old Heroku/Render postgres:// prefix → postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Build engine based on DB type
if DATABASE_URL.startswith("sqlite"):
    # Local development
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # Production — Supabase / PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,       # test connection before using from pool
        pool_recycle=300,         # recycle connections every 5 min
        pool_size=5,
        max_overflow=10,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables that don't exist yet. Safe to call on every startup."""
    # Import all models so SQLAlchemy knows about them before create_all
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables verified/created")
