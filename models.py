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


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(200), nullable=False, unique=True)
    password_hash = Column(String(500), nullable=False)
    full_name = Column(String(200))
    bio = Column(Text)
    interests = Column(String)
    avatar_url = Column(String(500))
    role = Column(String(50), default="user")  # user, creator, superuser
    is_active = Column(Integer, default=1)
    is_verified = Column(Integer, default=0)
    is_premium = Column(Integer, default=0)   # 1 = subscribed, unlocks AI
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    password_hash = Column(String(500), nullable=False)
    organisation_name = Column(String(200))
    phone = Column(String(50))
    plan = Column(String(50), default="freemium")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    author_username = Column(String(100))
    title = Column(String(300), nullable=False)
    excerpt = Column(Text)
    content = Column(Text)
    cover_image = Column(String(500))
    content_type = Column(String(50), default="article")  # article, audio, photo_essay, video
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    status = Column(String(50), default="draft")  # draft, published, pending, rejected
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    is_premium = Column(Integer, default=0)  # 1 = requires subscription to read full
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(100))
    content = Column(Text, nullable=False)
    is_approved = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    following_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('posts.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(100))
    message = Column(Text, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    is_approved = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class StorySubmission(Base):
    __tablename__ = "story_submissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    username = Column(String(100))
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    region_id = Column(Integer, ForeignKey('regions.id'), nullable=True)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), nullable=False, unique=True)
    full_name = Column(String(200))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    event_date = Column(String(100))
    location = Column(String(300))
    image_url = Column(String(500))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


class CreatorChannel(Base):
    __tablename__ = "creator_channels"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    channel_name = Column(String(200))
    channel_description = Column(Text)
    channel_image = Column(String(500))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
