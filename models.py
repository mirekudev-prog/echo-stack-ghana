from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# ============================================
# USER ACCOUNTS (Public Users)
# ============================================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), default="")
    bio = Column(Text, default="")
    interests = Column(Text, default="")  # JSON string of selected topics
    avatar_url = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# REGIONS (Ghana's 16 Regions)
# ============================================
class Region(Base):
    __tablename__ = "regions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    capital = Column(String(100), default="")
    population = Column(String(50), default="")
    terrain = Column(String(100), default="")
    description = Column(Text, default="")
    overview = Column(Text, default="")
    category = Column(String(50), default="", index=True)
    tags = Column(String(500), default="")  # Comma-separated tags
    hero_image = Column(String(500), default="")
    gallery_images = Column(Text, default="")  # Comma-separated URLs
    audio_files = Column(Text, default="")  # Comma-separated URLs
    source = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# UPLOADED FILES (Media Manager)
# ============================================
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), default="")
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, default=0)
    mime_type = Column(String(100), default="")
    category = Column(String(50), default="general", index=True)  # image, audio, video, document
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True, index=True)
    description = Column(Text, default="")
    uploaded_by = Column(String(100), default="admin")
    is_public = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# SECTIONS/CATEGORIES
# ============================================
class Section(Base):
    __tablename__ = "sections"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True, index=True)
    description = Column(Text, default="")
    display_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# SITE BUILDER - THEMES
# ============================================
class SiteTheme(Base):
    __tablename__ = "site_themes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    theme_data = Column(JSON, default={})  # Colors, fonts, layout settings
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# SITE BUILDER - PAGES
# ============================================
class SitePage(Base):
    __tablename__ = "site_pages"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    slug = Column(String(200), unique=True, index=True)
    content = Column(Text, default="")
    meta_description = Column(String(500), default="")
    meta_keywords = Column(String(500), default="")
    is_published = Column(Boolean, default=False)
    template = Column(String(100), default="default")
    parent_id = Column(Integer, ForeignKey('site_pages.id'), nullable=True)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# SITE BUILDER - WIDGETS
# ============================================
class SiteWidget(Base):
    __tablename__ = "site_widgets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    widget_type = Column(String(50), nullable=False)  # text, image, video, form, etc.
    widget_data = Column(JSON, default={})
    page_id = Column(Integer, ForeignKey('site_pages.id'), nullable=True, index=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# NEWSLETTER SUBSCRIBERS
# ============================================
class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    full_name = Column(String(200), default="")
    is_active = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# CHAT MESSAGES (Region Comments)
# ============================================
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(80), nullable=False)
    message = Column(Text, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True, index=True)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# STORY SUBMISSIONS (User Content)
# ============================================
class StorySubmission(Base):
    __tablename__ = "story_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(80), default="Anonymous")
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True, index=True)
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ============================================
# EVENTS
# ============================================
class Event(Base):
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    event_date = Column(String(50), default="")
    location = Column(String(200), default="")
    image_url = Column(String(500), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# ANALYTICS (Page Views, etc.)
# ============================================
class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    page_url = Column(String(500), index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    session_id = Column(String(100), index=True)
    ip_address = Column(String(50), default="")
    user_agent = Column(String(500), default="")
    visited_at = Column(DateTime, default=datetime.utcnow)

# ============================================
# API KEYS (For External Integrations)
# ============================================
class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_name = Column(String(100), nullable=False)
    key_value = Column(String(255), unique=True, nullable=False)
    permissions = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
