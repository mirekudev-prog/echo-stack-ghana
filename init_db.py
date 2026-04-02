import os
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import uuid

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    print("❌ Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
    exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

def init_database():
    print("🚀 Initializing EchoStack Database...")
    
    # Seed Users
    try:
        users_count = supabase.table("users").select("id", count="exact").execute()
        if users_count.count == 0:
            print("📝 Seeding users...")
            sample_users = [
                {"username": "echostack_admin", "email": "admin@echostack.com", "full_name": "Admin User", "avatar_url": "https://ui-avatars.com/api/?name=Admin+User&background=C8962E&color=fff", "bio": "Platform Administrator", "is_verified": True, "role": "admin"},
                {"username": "creative_jane", "email": "jane@example.com", "full_name": "Jane Doe", "avatar_url": "https://ui-avatars.com/api/?name=Jane+Doe&background=0D1B2A&color=fff", "bio": "Digital Artist & Creator", "is_verified": True, "role": "creator"},
                {"username": "tech_guru", "email": "tech@example.com", "full_name": "John Smith", "avatar_url": "https://ui-avatars.com/api/?name=John+Smith&background=FAF6EF&color=0D1B2A", "bio": "Tech Reviewer", "is_verified": False, "role": "user"},
            ]
            supabase.table("users").insert(sample_users).execute()
            print("✅ Users seeded.")
        else:
            print(f"ℹ️  {users_count.count} users already exist.")
    except Exception as e:
        print(f"⚠️  User seeding skipped or failed: {e}")

    # Seed Posts
    try:
        posts_count = supabase.table("posts").select("id", count="exact").execute()
        if posts_count.count == 0:
            print("📝 Seeding posts...")
            admin_res = supabase.table("users").select("id").eq("username", "echostack_admin").execute()
            admin_id = admin_res.data[0]['id'] if admin_res.data else None
            
            if admin_id:
                sample_posts = [
                    {
                        "author_id": admin_id, 
                        "title": "Welcome to EchoStack!",
                        "slug": "welcome-to-echostack",
                        "content": "Welcome to EchoStack! 🚀 This is your new no-code enabled platform.", 
                        "media_url": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=80", 
                        "media_type": "image", 
                        "content_type": "article",
                        "status": "published",
                        "likes_count": 12,
                        "author_username": "echostack_admin"
                    },
                    {
                        "author_id": admin_id, 
                        "title": "New Admin Dashboard",
                        "slug": "new-admin-dashboard",
                        "content": "Check out our new Admin Dashboard. You can now edit the whole site without code!", 
                        "media_url": None, 
                        "media_type": None, 
                        "content_type": "article",
                        "status": "published",
                        "likes_count": 45,
                        "author_username": "echostack_admin"
                    },
                ]
                supabase.table("posts").insert(sample_posts).execute()
                print("✅ Posts seeded.")
            else:
                print("⚠️  Could not find admin user to seed posts.")
        else:
            print(f"ℹ️  {posts_count.count} posts already exist.")
    except Exception as e:
        print(f"⚠️  Post seeding skipped: {e}")

    # Seed Stories
    try:
        stories_count = supabase.table("stories").select("id", count="exact").execute()
        if stories_count.count == 0:
            print("📝 Seeding stories...")
            admin_res = supabase.table("users").select("id").eq("username", "echostack_admin").execute()
            admin_id = admin_res.data[0]['id'] if admin_res.data else None
            
            if admin_id:
                expires_at = (datetime.now() + timedelta(hours=24)).isoformat()
                sample_stories = [
                    {"user_id": admin_id, "media_url": "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?ixlib=rb-1.2.1&auto=format&fit=crop&w=400&q=80", "media_type": "image", "expires_at": expires_at, "is_approved": True, "caption": "Morning in Ghana"},
                    {"user_id": admin_id, "media_url": "https://assets.mixkit.co/videos/preview/mixkit-waves-in-the-water-1164-large.mp4", "media_type": "video", "expires_at": expires_at, "is_approved": True, "caption": "Waves"},
                ]
                supabase.table("stories").insert(sample_stories).execute()
                print("✅ Stories seeded.")
            else:
                print("⚠️  Could not find admin user to seed stories.")
        else:
            print(f"ℹ️  {stories_count.count} stories already exist.")
    except Exception as e:
        print(f"⚠️  Story seeding skipped: {e}")

    print("\n🎉 Database initialization complete! Ready to load data.")

if __name__ == "__main__":
    init_database()
