from fastapi import FastAPI
import os

print("🚀 Starting EchoStack...")

app = FastAPI(title="EchoStack API")

@app.on_event("startup")
async def startup():
    """Test database connection on startup"""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables!")
        return
    
    print(f"✅ DATABASE_URL found: {db_url[:50]}...")
    
    try:
        from sqlalchemy import create_engine, inspect
        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"✅ Connected to database! Tables: {tables}")
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")

@app.get("/")
def read_root():
    return {"message": "EchoStack Backend Running!", "status": "success"}

@app.get("/test")
def test_endpoint():
    return {"test": "passed"}
