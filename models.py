from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean,
    ForeignKey, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

from database import Base


# ─── REGION ───────────────────────────────────────────────────────────────────
class Region(Base):
    __tablename__ = "regions"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    capital       = Column(String(100))
    population    = Column(String(50))
    terrain       = Column(String(100))
    description   = Column(Text)
    overview      = Column(Text)
    category      = Column(String(50))
    tags          = Column(Text)
    hero_image    = Column(String(500))
    gallery_images= Column(Text)
    audio_files   = Column(Text)
    video_files   = Column(Text)
    documents     = Column(Text)
    source        = Column(String(500))
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── USER ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username        = Column(String(100), unique=True, nullable=False)
    email           = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(255), default="")
    bio             = Column(Text, default="")
    avatar_url      = Column(String(500), default="")
    channel_name    = Column(String(200), default="")
    channel_desc    = Column(Text, default="")
    role            = Column(String(50), default="user")
    is_premium      = Column(Integer, default=0)
    is_suspended    = Column(Integer, default=0)
    follower_count  = Column(Integer, default=0)
    email_verified  = Column(Boolean, default=False)
    verification_token         = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime, nullable=True)
    reset_token                = Column(String(255), nullable=True)
    reset_token_expires        = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── POST ─────────────────────────────────────────────────────────────────────
class Post(Base):
    __tablename__ = "posts"

    id               = Column(Integer, primary_key=True, index=True)
    title            = Column(String(500), default="")
    slug             = Column(String(500), default="", index=True)
    excerpt          = Column(Text, default="")
    content          = Column(Text, default="")
    cover_image      = Column(String(500), default="")
    content_type     = Column(String(50), default="article")
    status           = Column(String(50), default="draft")
    is_locked        = Column(Integer, default=0)
    author_id        = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    author_username  = Column(String(200), default="")
    region_id        = Column(Integer, ForeignKey("regions.id"), nullable=True)
    tags             = Column(Text, default="")
    views            = Column(Integer, default=0)
    likes            = Column(Integer, default=0)
    audio_url        = Column(String(500), default="")
    video_url        = Column(String(500), default="")
    gallery          = Column(Text, default="")
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── COMMENT ──────────────────────────────────────────────────────────────────
class Comment(Base):
    __tablename__ = "comments"

    id         = Column(Integer, primary_key=True, index=True)
    post_id    = Column(Integer, ForeignKey("posts.id"), nullable=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    username   = Column(String(200), default="")
    content    = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── FOLLOW ───────────────────────────────────────────────────────────────────
class Follow(Base):
    __tablename__ = "follows"

    id           = Column(Integer, primary_key=True, index=True)
    follower_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    following_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)


# ─── UPLOADED FILE ────────────────────────────────────────────────────────────
class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id            = Column(Integer, primary_key=True, index=True)
    filename      = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path     = Column(String(500), default="")
    file_size     = Column(Integer)
    mime_type     = Column(String(100))
    category      = Column(String(50))
    region_id     = Column(Integer, ForeignKey("regions.id"), nullable=True)
    description   = Column(Text)
    uploaded_by   = Column(String(100), default="user")
    is_public     = Column(Integer, default=1)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─── SECTION ──────────────────────────────────────────────────────────────────
class Section(Base):
    __tablename__ = "sections"

    id                = Column(Integer, primary_key=True, index=True)
    name              = Column(String(100), nullable=False, unique=True)
    slug              = Column(String(100), unique=True)
    description       = Column(Text)
    parent_section_id = Column(Integer, nullable=True)
    display_order     = Column(Integer, default=0)
    is_active         = Column(Integer, default=1)
    created_at        = Column(DateTime, default=datetime.utcnow)


# ─── NEWSLETTER SUBSCRIBER ────────────────────────────────────────────────────
class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String(200), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── EVENT ────────────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(300), nullable=False)
    description = Column(Text)
    event_date  = Column(DateTime, nullable=True)
    location    = Column(String(300))
    created_at  = Column(DateTime, default=datetime.utcnow)


# ─── CHAT MESSAGE ─────────────────────────────────────────────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    username   = Column(String(200), default="Guest")
    content    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── STORY SUBMISSION ─────────────────────────────────────────────────────────
class StorySubmission(Base):
    __tablename__ = "story_submissions"

    id          = Column(Integer, primary_key=True, index=True)
    title       = Column(String(300), nullable=False)
    content     = Column(Text)
    region      = Column(String(100))
    author_name = Column(String(200))
    status      = Column(String(50), default="pending")
    created_at  = Column(DateTime, default=datetime.utcnow)


# ─── PAYMENT ──────────────────────────────────────────────────────────────────
class Payment(Base):
    __tablename__ = "payments"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    email      = Column(String(200))
    amount     = Column(Integer, default=0)
    reference  = Column(String(200))
    status     = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── TOPIC ────────────────────────────────────────────────────────────────────
class Topic(Base):
    __tablename__ = "topics"

    id   = Column(Integer, primary_key=True, index=True)
    name = Column(Text, unique=True, nullable=False)


# ─── USER TOPIC (junction) ────────────────────────────────────────────────────
class UserTopic(Base):
    __tablename__ = "user_topics"

    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True)
