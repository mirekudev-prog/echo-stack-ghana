from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
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


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    category = Column(String(50))
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    description = Column(Text)
    uploaded_by = Column(String(100))
    is_public = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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


# ── USER ──────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(200), unique=True)
    password_hash = Column(String(255))
    role = Column(String(30), default="user")        # user | creator | admin | superuser
    plan = Column(String(30), default="free")        # free | premium
    avatar_url = Column(String(500), default="")
    channel_name = Column(String(150), default="")
    channel_desc = Column(Text, default="")
    follower_count = Column(Integer, default=0)
    session_token = Column(String(255), default="")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── POST ──────────────────────────────────────────────────────────────────────
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    title = Column(String(300), nullable=False)
    excerpt = Column(Text, default="")
    content = Column(Text, default="")
    content_type = Column(String(30), default="article")  # article|audio|photo_essay|video
    cover_image = Column(String(500), default="")
    audio_url = Column(String(500), default="")
    video_url = Column(String(500), default="")
    gallery = Column(Text, default="")               # comma-separated URLs
    tags = Column(String(300), default="")
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    status = Column(String(20), default="draft")     # draft | published | rejected
    is_premium = Column(Integer, default=0)
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ── COMMENT ───────────────────────────────────────────────────────────────────
class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── LIKE ──────────────────────────────────────────────────────────────────────
class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── FOLLOW ────────────────────────────────────────────────────────────────────
class Follow(Base):
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
