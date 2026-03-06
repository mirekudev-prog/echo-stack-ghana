from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(100), unique=True, index=True, nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    interests     = Column(Text, default="General")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)


class Region(Base):
    __tablename__ = "regions"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)
    capital          = Column(String(200))
    population       = Column(String(100))
    terrain          = Column(String(200))
    description      = Column(Text)
    category         = Column(String(100))
    tags             = Column(Text)           # comma-separated
    hero_image       = Column(Text)
    gallery_images   = Column(Text)           # comma-separated URLs
    audio_files      = Column(Text)           # comma-separated URLs
    source           = Column(Text)
    overview         = Column(Text)
    created_at       = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.datetime.utcnow,
                              onupdate=datetime.datetime.utcnow)


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id            = Column(Integer, primary_key=True, index=True)
    filename      = Column(String(500))
    original_name = Column(String(500))
    file_path     = Column(Text)
    file_url      = Column(Text)
    category      = Column(String(100), default="general")
    description   = Column(Text)
    file_size_mb  = Column(Float, default=0.0)
    is_public     = Column(Boolean, default=True)
    region_id     = Column(Integer, ForeignKey("regions.id"), nullable=True)
    uploaded_at   = Column(DateTime, default=datetime.datetime.utcnow)


class Section(Base):
    __tablename__ = "sections"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    slug          = Column(String(200), unique=True, index=True)
    display_order = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)


class SitePage(Base):
    __tablename__ = "site_pages"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(300), nullable=False)
    slug         = Column(String(300), unique=True, index=True)
    content      = Column(Text, default="")
    widgets      = Column(Text, default="[]")   # JSON string
    template     = Column(String(100), default="default")
    is_published = Column(Boolean, default=False)
    is_home      = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.datetime.utcnow)


class SiteTheme(Base):
    __tablename__ = "site_themes"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    theme_data = Column(Text, default="{}")     # JSON string
    is_active  = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String(255), unique=True, index=True, nullable=False)
    full_name    = Column(String(200))
    is_active    = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    username    = Column(String(100))
    message     = Column(Text, nullable=False)
    region_id   = Column(Integer, ForeignKey("regions.id"), nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)


class StorySubmission(Base):
    __tablename__ = "story_submissions"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=True)
    title      = Column(String(300), nullable=False)
    content    = Column(Text, nullable=False)
    status     = Column(String(50), default="pending")   # pending/approved/rejected
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Event(Base):
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text)
    event_date  = Column(DateTime)
    location    = Column(String(300))
    image_url   = Column(Text)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)
