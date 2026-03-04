from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    overview = Column(Text)
    source = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, index=True)
    title = Column(String)
    community = Column(String)
    speaker_name = Column(String)
    date_recorded = Column(DateTime)
    duration_seconds = Column(Integer)
    synopsis = Column(Text)
    audio_url = Column(String)
