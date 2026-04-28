# ============================================
# ECHOSTACK DATABASE CONFIGURATION
# ============================================
from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# ============================================
# DATABASE URL SETUP
# ============================================
# Get DATABASE_URL from environment (Render/Supabase) or fallback to local SQLite
# MUST read from os.environ to get Render environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")

# If not set in environment, try loading from .env file (for local development)
if not DATABASE_URL:
    try:
        from dotenv import load_dotenv
        load_dotenv()
        DATABASE_URL = os.environ.get("DATABASE_URL")
    except:
        pass

# Fallback to SQLite if still no DATABASE_URL
if not DATABASE_URL:
    DATABASE_URL = "sqlite:///./echostack.db"
    print(f"⚠️  DATABASE_URL not set! Using local SQLite: {DATABASE_URL}")
    print("   Set DATABASE_URL environment variable or create .env file")

SQLALCHEMY_DATABASE_URL = DATABASE_URL

# DEBUG: Print the actual URL being used
print(f"")
print(f"=" * 60)
print(f"🔗 SQLALCHEMY DATABASE URL: {SQLALCHEMY_DATABASE_URL[:60]}...")
print(f"=" * 60)
print(f"")

# Fix legacy postgres:// protocol (Render/Heroku old format)
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )

# Add sslmode=require for Supabase PostgreSQL (required for secure connection)
if (
    SQLALCHEMY_DATABASE_URL.startswith("postgresql://")
    and "sslmode" not in SQLALCHEMY_DATABASE_URL
):
    connector = "&" if "?" in SQLALCHEMY_DATABASE_URL else "?"
    SQLALCHEMY_DATABASE_URL += f"{connector}sslmode=require"

# Log which database we're connecting to
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    print(f"✅ Connecting to Supabase PostgreSQL database")
else:
    print(f"⚠️  Using local SQLite database: {SQLALCHEMY_DATABASE_URL}")
    print("   Set DATABASE_URL in .env to use Supabase.")

# ============================================
# ENGINE CONFIGURATION
# ============================================
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    # Production: PostgreSQL with connection pooling for pgBouncer (Supabase/Render)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,  # Auto-recycle stale connections
        pool_size=5,  # Max persistent connections
        max_overflow=0,  # Required for pgBouncer transaction mode
        connect_args={
            "options": "-c timezone=utc"  # Ensure UTC timestamps
        },
    )
else:
    # Local development: SQLite (no pooling needed)
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},  # Allow SQLite in threads
    )

# ============================================
# SESSION FACTORY
# ============================================
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()


# ============================================
# DATABASE DEPENDENCY (for FastAPI)
# ============================================
def get_db() -> Session:
    """
    FastAPI dependency: yields a database session.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# DATABASE INITIALIZATION
# ============================================
def init_db() -> None:
    """
    Create all database tables if they don't exist.
    Safe to call multiple times (idempotent).
    Call this once at app startup.
    """
    try:
        # Import models to register them with Base.metadata
        # (This ensures all tables are created)
        import models  # noqa: F401

        # Create tables (safe: won't error if tables already exist)
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created/verified successfully")
    except Exception as e:
        print(f"❌ Database init error: {e}")
        # Don't re-raise: let app continue (tables may already exist)
        # If critical, the app will fail on first query anyway


# ============================================
# HEALTH CHECK (optional utility)
# ============================================
def check_db_connection() -> bool:
    """
    Test database connection.
    Returns True if connected, False otherwise.
    """
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except:
        return False
