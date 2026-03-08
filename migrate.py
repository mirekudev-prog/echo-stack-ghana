"""
migrate.py — EchoStack Safe Migration
======================================
Run this ONCE after deploying the new models.py to add all missing columns
to the existing PostgreSQL database WITHOUT destroying any data.

On Render: add this as a one-time job or call it from startup.
Locally:   python migrate.py
"""

from database import engine, Base
import models
from sqlalchemy import text, inspect

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

# ============================================================
# ALL MIGRATIONS
# ============================================================
MIGRATIONS = {

    # ── regions ──────────────────────────────────────────────
    "regions": [
        ("video_files",  "TEXT",    None),
        ("documents",    "TEXT",    None),
        ("overview",     "TEXT",    None),
    ],

    # ── users ────────────────────────────────────────────────
    # This table may not exist at all — created fresh by Base.metadata.create_all
    "users": [
        ("full_name",     "VARCHAR(200)", None),
        ("bio",           "TEXT",         None),
        ("interests",     "TEXT",         None),
        ("avatar_url",    "VARCHAR(500)", None),
        ("role",          "VARCHAR(20)",  "'user'"),
        ("is_premium",    "BOOLEAN",      "FALSE"),
        ("is_active",     "BOOLEAN",      "TRUE"),
        ("updated_at",    "TIMESTAMP",    "NOW()"),
    ],

    # ── posts ────────────────────────────────────────────────
    "posts": [
        ("author_username", "VARCHAR(80)",  "''"),
        ("audio_url",       "VARCHAR(500)", None),
        ("video_url",       "VARCHAR(500)", None),
        ("gallery",         "TEXT",         None),
        ("tags",            "VARCHAR",      None),
        ("views",           "INTEGER",      "0"),
        ("likes",           "INTEGER",      "0"),
        ("comment_count",   "INTEGER",      "0"),
        ("published_at",    "TIMESTAMP",    None),
        ("updated_at",      "TIMESTAMP",    "NOW()"),
    ],

    # ── story_submissions ────────────────────────────────────
    "story_submissions": [
        ("user_id",    "VARCHAR(36)", None),
        ("updated_at", "TIMESTAMP",  "NOW()"),
    ],

    # ── uploaded_files ───────────────────────────────────────
    "uploaded_files": [
        ("updated_at", "TIMESTAMP", "NOW()"),
    ],

    # ── creator_channels ─────────────────────────────────────
    # May be brand new — create_all handles it, but patch if partial
    "creator_channels": [
        ("channel_desc",  "TEXT",         None),
        ("cover_image",   "VARCHAR(500)", None),
        ("avatar_url",    "VARCHAR(500)", None),
        ("updated_at",    "TIMESTAMP",    "NOW()"),
    ],

    # ── comments ─────────────────────────────────────────────
    "comments": [
        ("author_username", "VARCHAR(80)", "''"),
        ("is_approved",     "INTEGER",     "1"),
    ],

    # ── events ───────────────────────────────────────────────
    "events": [
        ("updated_at", "TIMESTAMP", "NOW()"),
        ("is_active",  "BOOLEAN",   "TRUE"),
    ],

    # ── payments ─────────────────────────────────────────────
    "payments": [
        ("updated_at", "TIMESTAMP", "NOW()"),
    ],
}


def run():
    print("\n🚀 EchoStack Migration Starting...\n")

    # Step 1: Create any completely new tables (safe — skips existing)
    print("📋 Creating new tables (if not exist)...")
    Base.metadata.create_all(bind=engine)
    print("   Done.\n")

    # Step 2: Add missing columns to existing tables
    with engine.connect() as conn:
        for table, columns in MIGRATIONS.items():
            if not table_exists(conn, table):
                print(f"  ⏭  Table '{table}' not found — skipping column patches (created fresh above)")
                continue
            print(f"📦 Patching table: {table}")
            for col_name, col_type, col_default in columns:
                try:
                    add_column_if_missing(conn, table, col_name, col_type, col_default)
                except Exception as e:
                    print(f"  ⚠️  Could not add {table}.{col_name}: {e}")
            conn.commit()
            print()

    print("✅ Migration complete!\n")


if __name__ == "__main__":
    run()
