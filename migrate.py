from database import engine
import models

# Drop all existing tables
models.Base.metadata.drop_all(bind=engine)

# Create fresh tables
models.Base.metadata.create_all(bind=engine)

print("✅ Database migrated successfully!")
