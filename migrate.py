"""
migrate.py — EchoStack Ghana Final Migration
============================================
Run this on Render to sync your database with your new models.
"""

from database import engine, Base
import models
from sqlalchemy import text

def column_exists(conn, table, column):
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": column})
    return result.fetchone() is not None

def table_exists(conn, table):
    result = conn.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name=:t"
    ), {"t": table})
    return result.fetchone() is not None

def add_column_if_missing(conn, table, column, col_type, default=None):
    if not column_exists(conn, table, column):
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}'))
        print(f"  ✅ Added: {table}.{column}")
    else:
        print(f"  ✔  Exists: {table}.{column}")

# These are the specific columns your new main.py and models.py require
MIGRATIONS = {
    "users": [
        ("hashed_password", "VARCHAR(255)", "''"),
        ("bio", "TEXT", "''"),
        ("avatar_url", "VARCHAR(500)", "''"),
        ("channel_name", "VARCHAR(200)", "''"),
        ("channel_desc", "TEXT", "''"),
        ("role", "VARCHAR(50)", "'user'"),
        ("is_premium", "INTEGER", "0"),
        ("is_suspended", "INTEGER", "0"),
        ("follower_count", "INTEGER", "0"),
        ("email_verified", "BOOLEAN", "FALSE"),
        ("verification_token", "VARCHAR(255)", "NULL"),
        ("verification_token_expires", "TIMESTAMP", "NULL"),
        ("reset_token", "VARCHAR(255)", "NULL"),
        ("reset_token_expires", "TIMESTAMP", "NULL"),
    ],
    "posts": [
        ("audio_url", "VARCHAR(500)", "''"),
        ("video_url", "VARCHAR(500)", "''"),
        ("gallery", "TEXT", "''"),
        ("cover_image", "VARCHAR(500)", "''"),
        ("is_locked", "INTEGER", "0"),
        ("tags", "TEXT", "''"),
        ("views", "INTEGER", "0"),
        ("likes", "INTEGER", "0"),
    ],
    "regions": [
        ("overview", "TEXT", "''"),
        ("video_files", "TEXT", "''"),
        ("documents", "TEXT", "''"),
    ],
    "uploaded_files": [
        ("file_path", "VARCHAR(500)", "''"),
        ("uploaded_by", "VARCHAR(200)", "'user'"),
        ("is_public", "INTEGER", "1"),
    ]
}

def run():
    print("\n🚀 EchoStack Ghana: Starting Database Sync...\n")

    # Step 1: Create new tables (StorySubmission, Payment, etc.)
    print("📋 Checking for new tables...")
    Base.metadata.create_all(bind=engine)
    print("   Done.\n")

    # Step 2: Add missing columns to existing tables (User, Post, etc.)
    with engine.connect() as conn:
        for table, columns in MIGRATIONS.items():
            if not table_exists(conn, table):
                continue
            
            print(f"📦 Patching table: {table}")
            for col_name, col_type, col_default in columns:
                try:
                    add_column_if_missing(conn, table, col_name, col_type, col_default)
                except Exception as e:
                    print(f"  ⚠️  Could not add {table}.{col_name}: {e}")
            conn.commit()
            print()

    print("✅ Database is now up to date!\n")

if __name__ == "__main__":
    run()
