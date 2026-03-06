from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from database import Base


# ============================================
# USERS
# ============================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)

    password_hash = Column(String(256), nullable=False)

    full_name = Column(String(120))
    bio = Column(Text)

    interests = Column(Text)

    avatar_url = Column(String(255))

    is_active = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("ChatMessage", back_populates="user")
    stories = relationship("StorySubmission", back_populates="user")


# ============================================
# CLIENTS (Organisations using EchoStack)
# ============================================

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(120), nullable=False)

    email = Column(String(120), unique=True, index=True, nullable=False)

    password_hash = Column(String(256), nullable=False)

    organisation_name = Column(String(255))

    plan = Column(String(50), default="freemium")

    is_active = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# CHAT MESSAGES
# ============================================

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    username = Column(String(50))

    message = Column(Text, nullable=False)

    region_id = Column(Integer, ForeignKey("regions.id"))

    is_approved = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="messages")
    region = relationship("Region")


# ============================================
# STORY SUBMISSIONS
# ============================================

class StorySubmission(Base):
    __tablename__ = "story_submissions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    username = Column(String(50))

    title = Column(String(255), nullable=False)

    content = Column(Text, nullable=False)

    region_id = Column(Integer, ForeignKey("regions.id"))

    status = Column(String(20), default="pending")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="stories")
    region = relationship("Region")


# ============================================
# NEWSLETTER
# ============================================

class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)

    email = Column(String(120), unique=True, index=True, nullable=False)

    full_name = Column(String(120))

    is_active = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# EVENTS
# ============================================

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)

    description = Column(Text)

    event_date = Column(String(50))

    location = Column(String(255))

    image_url = Column(String(255))

    is_active = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# REGIONS
# ============================================

class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(120), nullable=False)

    capital = Column(String(120))

    population = Column(String(120))

    terrain = Column(String(120))

    description = Column(Text)

    overview = Column(Text)

    category = Column(String(120))

    tags = Column(Text)

    hero_image = Column(String(255))

    gallery_images = Column(Text)

    audio_files = Column(Text)

    source = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============================================
# FILE UPLOADS
# ============================================

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)

    filename = Column(String(255), nullable=False)

    original_name = Column(String(255))

    file_path = Column(String(255))

    file_size = Column(Integer)

    mime_type = Column(String(120))

    category = Column(String(50))

    region_id = Column(Integer, ForeignKey("regions.id"))

    description = Column(Text)

    uploaded_by = Column(String(120))

    is_public = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    region = relationship("Region")


# ============================================
# CONTENT SECTIONS
# ============================================

class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(120), nullable=False)

    slug = Column(String(120), unique=True, index=True)

    description = Column(Text)

    display_order = Column(Integer, default=0)

    is_active = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
