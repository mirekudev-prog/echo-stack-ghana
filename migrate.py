"""
migrate.py — Synchronized for EchoStack Models
"""
import os

# CRITICAL: Force reload environment variables from Render
DATABASE_URL_FROM_ENV = os.environ.get("DATABASE_URL", "NOT FOUND IN os.environ!")
print(f"")
print(f"=" * 60)
print(f"🔍 DATABASE_URL from os.environ: {DATABASE_URL_FROM_ENV[:80] if DATABASE_URL_FROM_ENV != 'NOT FOUND IN os.environ!' else 'NOT FOUND!'}")
print(f"=" * 60)
print(f"")

# If DATABASE_URL is in .env, log that too
try:
    with open('.env', 'r') as f:
        env_content = f.read()
        if 'DATABASE_URL' in env_content:
            print(f"📄 .env file has DATABASE_URL (but Render should use env var)")
except:
    pass

from database import engine, Base
import models
from sqlalchemy import text

def add_column_if_missing(conn, table, column, col_type, default=None):
    # Check if column exists
    res = conn.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{column}'"))
    if not res.fetchone():
        default_clause = f" DEFAULT {default}" if default is not None else ""
        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}'))
        print(f"  ✅ Added: {table}.{column}")

def run():
    print("\n🚀 Running Auto-Migration...")
    Base.metadata.create_all(bind=engine) # Creates missing tables
    
    with engine.connect() as conn:
        # Patching Users (matching your User class)
        cols = [
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
        ]
        for col, ctype, default in cols:
            add_column_if_missing(conn, "users", col, ctype, default)
        
        # Patching Posts
        post_cols = [("audio_url", "VARCHAR(500)", "''"), ("video_url", "VARCHAR(500)", "''"), ("gallery", "TEXT", "''")]
        for col, ctype, default in post_cols:
            add_column_if_missing(conn, "posts", col, ctype, default)

        conn.commit()
    print("✅ Migration finished successfully!\n")

if __name__ == "__main__":
    run()
