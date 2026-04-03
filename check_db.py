import os
import sys
from sqlalchemy import text
from database import engine, SessionLocal
import models

def check_diagnostics():
    print("--- EchoStack Diagnostics ---")
    
    # 1. Check Environment
    db_url = os.environ.get("DATABASE_URL", "sqlite:///./echostack.db")
    is_supabase = "supabase" in db_url.lower() or "postgresql" in db_url.lower()
    
    print(f"Database Type: {'PRODUCTION (Supabase/Postgres)' if is_supabase else 'LOCAL (SQLite)'}")
    if not is_supabase:
        print("⚠️  Warning: Currently using local SQLite. You will not see your live Supabase data.")
    
    # 2. Check Connection
    try:
        db = SessionLocal()
        # Test query
        db.execute(text("SELECT 1")).fetchone()
        print("✅ Database Connection: SUCCESS")
    except Exception as e:
        print(f"❌ Database Connection: FAILED - {e}")
        return

    # 3. Check Counts
    try:
        user_count = db.query(models.User).count()
        post_count = db.query(models.Post).count()
        story_count = db.query(models.Story).count()
        region_count = db.query(models.Region).count()
        
        print(f"👥 Total Users: {user_count}")
        print(f"📝 Total Posts: {post_count}")
        print(f"🎬 Total Stories: {story_count}")
        print(f"🗺️  Total Regions: {region_count}")
        
        if user_count < 15:
            print("⚠️  Note: You mentioned about 17 users. Only found {user_count}. Check your connection.")
    except Exception as e:
        print(f"❌ Error querying data: {e}")
    finally:
        db.close()

    print("--------------------------------")

if __name__ == "__main__":
    check_diagnostics()
