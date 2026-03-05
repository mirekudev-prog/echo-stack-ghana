from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from database import Base

class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    capital = Column(String(100))
    population = Column(String(50))
    terrain = Column(String(100))
    description = Column(Text)
    overview = Column(Text)
    source = Column(String(500))
    hero_image = Column(String(500))
    gallery_images = Column(String)
    audio_files = Column(String)
    category = Column(String(50))
    tags = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
