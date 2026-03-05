from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
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
    category = Column(String(50))
    tags = Column(String)
    hero_image = Column(String(500))
    gallery_images = Column(String)
    audio_files = Column(String)
    source = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# NEW: Track all uploaded files
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)  # in bytes
    mime_type = Column(String(100))
    category = Column(String(50))  # video, audio, image, document, other
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)  # Optional link to region
    description = Column(Text)
    uploaded_by = Column(String(100))
    is_public = Column(Integer, default=1)  # 1 = public, 0 = private
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# NEW: For dynamic sections/categories
class Section(Base):
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True)
    description = Column(Text)
    parent_section_id = Column(Integer, ForeignKey('sections.id'), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
