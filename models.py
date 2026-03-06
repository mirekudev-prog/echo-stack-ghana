from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


# ── USERS (all roles in one table) ───────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(100), unique=True, index=True, nullable=False)
    email         = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(20), default="user")   # user | creator | admin | superuser
    full_name     = Column(String(200), default="")
    bio           = Column(Text, default="")
    avatar_url    = Column(Text, default="")
    interests     = Column(Text, default="General")
    plan          = Column(String(20), default="free")   # free | premium
    is_active     = Column(Boolean, default=True)
    # Creator-specific
    channel_name  = Column(String(200), default="")
    channel_desc  = Column(Text, default="")
    channel_banner= Column(Text, default="")
    creator_since = Column(DateTime, nullable=True)
    # Stats
    follower_count= Column(Integer, default=0)
    post_count    = Column(Integer, default=0)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)

    posts         = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments      = relationship("Comment", back_populates="author", cascade="all, delete-orphan")


# ── POSTS (creator content) ───────────────────────────────────────────────────
class Post(Base):
    __tablename__ = "posts"

    id            = Column(Integer, primary_key=True, index=True)
    author_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    title         = Column(String(400), nullable=False)
    slug          = Column(String(400), unique=True, index=True)
    content       = Column(Text, default="")
    excerpt       = Column(Text, default="")
    cover_image   = Column(Text, default="")
    content_type  = Column(String(50), default="article")  # article | audio | photo_essay | video
    audio_url     = Column(Text, default="")
    video_url     = Column(Text, default="")
    gallery       = Column(Text, default="")   # comma-separated image URLs
    region_id     = Column(Integer, ForeignKey("regions.id"), nullable=True)
    tags          = Column(Text, default="")
    status        = Column(String(20), default="draft")  # draft | pending | published | rejected
    is_premium    = Column(Boolean, default=False)
    view_count    = Column(Integer, default=0)
    like_count    = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    published_at  = Column(DateTime, nullable=True)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    author        = relationship("User", back_populates="posts")
    comments      = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


# ── COMMENTS ─────────────────────────────────────────────────────────────────
class Comment(Base):
    __tablename__ = "comments"

    id          = Column(Integer, primary_key=True, index=True)
    post_id     = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    content     = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)

    post        = relationship("Post", back_populates="comments")
    author      = relationship("User", back_populates="comments")


# ── FOLLOWS (user follows creator) ───────────────────────────────────────────
class Follow(Base):
    __tablename__ = "follows"

    id          = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator_id  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)


# ── REGIONS ───────────────────────────────────────────────────────────────────
class Region(Base):
    __tablename__ = "regions"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(200), nullable=False)
    capital        = Column(String(200), default="")
    population     = Column(String(100), default="")
    terrain        = Column(String(200), default="")
    description    = Column(Text, default="")
    overview       = Column(Text, default="")
    category       = Column(String(100), default="")
    tags           = Column(Text, default="")
    hero_image     = Column(Text, default="")
    gallery_images = Column(Text, default="")
    audio_files    = Column(Text, default="")
    source         = Column(Text, default="")
    created_at     = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


# ── UPLOADED FILES ────────────────────────────────────────────────────────────
class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id            = Column(Integer, primary_key=True, index=True)
    filename      = Column(String(500), default="")
    original_name = Column(String(500), default="")
    file_path     = Column(Text, default="")
    file_url      = Column(Text, default="")
    file_size     = Column(Integer, default=0)
    file_size_mb  = Column(Float, default=0.0)
    mime_type     = Column(String(200), default="")
    category      = Column(String(100), default="general")
    description   = Column(Text, default="")
    is_public     = Column(Boolean, default=True)
    region_id     = Column(Integer, ForeignKey("regions.id"), nullable=True)
    uploaded_by   = Column(String(100), default="")
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)


# ── SECTIONS ──────────────────────────────────────────────────────────────────
class Section(Base):
    __tablename__ = "sections"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(200), nullable=False)
    slug          = Column(String(200), unique=True, index=True)
    description   = Column(Text, default="")
    display_order = Column(Integer, default=0)
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.datetime.utcnow)


# ── CHAT MESSAGES ─────────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    username    = Column(String(100), default="Anonymous")
    message     = Column(Text, nullable=False)
    region_id   = Column(Integer, ForeignKey("regions.id"), nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)


# ── STORY SUBMISSIONS ─────────────────────────────────────────────────────────
class StorySubmission(Base):
    __tablename__ = "story_submissions"

    id        = Column(Integer, primary_key=True, index=True)
    user_id   = Column(Integer, ForeignKey("users.id"), nullable=True)
    username  = Column(String(100), default="Anonymous")
    title     = Column(String(300), nullable=False)
    content   = Column(Text, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    status    = Column(String(50), default="pending")
    created_at= Column(DateTime, default=datetime.datetime.utcnow)


# ── NEWSLETTER ────────────────────────────────────────────────────────────────
class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String(255), unique=True, index=True, nullable=False)
    full_name    = Column(String(200), default="")
    is_active    = Column(Boolean, default=True)
    subscribed_at= Column(DateTime, default=datetime.datetime.utcnow)


# ── EVENTS ────────────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text, default="")
    event_date  = Column(String(100), default="")
    location    = Column(String(300), default="")
    image_url   = Column(Text, default="")
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.datetime.utcnow)


# ── SITE PAGES ────────────────────────────────────────────────────────────────
class SitePage(Base):
    __tablename__ = "site_pages"

    id           = Column(Integer, primary_key=True, index=True)
    title        = Column(String(300), nullable=False)
    slug         = Column(String(300), unique=True, index=True)
    content      = Column(Text, default="")
    is_published = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.datetime.utcnow)
