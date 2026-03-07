# models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as SQLAlchemyUUID
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import uuid

# ============================================
# USER ACCOUNTS
# ============================================
class User(Base):
    __tablename__ = "es_users"
    id = Column(SQLAlchemyUUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(200), nullable=False, unique=True)
    password_hash = Column(String(500), nullable=False)
    full_name = Column(String(200))
    bio = Column(Text)
    interests = Column(String)
    avatar_url = Column(String(500))
    role = Column(String(50), default="user")        # user, creator, admin, superuser
    plan = Column(String(50), default="free")        # free, premium, freemium
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = relationship("Post", back_populates="author", foreign_keys="Post.author_id")
    comments = relationship("Comment", back_populates="author", foreign_keys="Comment.author_id")
    follows_given = relationship("Follow", back_populates="follower", foreign_keys="Follow.follower_id")
    follows_received = relationship("Follow", back_populates="creator", foreign_keys="Follow.creator_id")


# ============================================
# POSTS
# ============================================
class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    slug = Column(String(400))
    excerpt = Column(Text)
    content = Column(Text)
    cover_image = Column(String(500))
    content_type = Column(String(50), default="article")
    audio_url = Column(String(500))
    video_url = Column(String(500))
    gallery = Column(Text)
    tags = Column(String)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    status = Column(String(50), default="draft")      # draft, pending, published, rejected
    view_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    is_premium = Column(Boolean, default=False)
    published_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = relationship("User", back_populates="posts", foreign_keys=[author_id])
    region = relationship("Region", foreign_keys=[region_id])
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")


# ============================================
# COMMENTS
# ============================================
class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments", foreign_keys=[author_id])


# ============================================
# FOLLOWS
# ============================================
class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=False)
    creator_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    follower = relationship("User", back_populates="follows_given", foreign_keys=[follower_id])
    creator = relationship("User", back_populates="follows_received", foreign_keys=[creator_id])


# ============================================
# REGIONS
# ============================================
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
    gallery_images = Column(Text)
    audio_files = Column(Text)
    video_files = Column(Text)
    documents = Column(Text)
    source = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================
# UPLOADED FILES
# ============================================
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500))
    file_url = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    category = Column(String(50))
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    description = Column(Text)
    uploaded_by = Column(String(100))
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================
# STORIES (Pending Submissions)
# ============================================
class StorySubmission(Base):
    __tablename__ = "story_submissions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=True)
    username = Column(String(100))
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# NEWSLETTER SUBSCRIBERS
# ============================================
class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), nullable=False, unique=True)
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# EVENTS
# ============================================
class Event(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    description = Column(Text)
    event_date = Column(String(100))
    location = Column(String(300))
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# LIKES
# ============================================
class Like(Base):
    __tablename__ = "likes"
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    user_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# CREATOR CHANNELS
# ============================================
class CreatorChannel(Base):
    __tablename__ = "creator_channels"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=False, unique=True)
    channel_name = Column(String(200))
    channel_description = Column(Text)
    channel_image = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================
# CLIENTS (for business clients)
# ============================================
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True)
    password_hash = Column(String(500), nullable=False)
    organisation_name = Column(String(200))
    phone = Column(String(50))
    plan = Column(String(50), default="freemium")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================
# PAYMENTS
# ============================================
class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(SQLAlchemyUUID(as_uuid=True), ForeignKey("es_users.id"), nullable=True)
    email = Column(String(200))
    amount = Column(Integer)                     # in pesewas (GH₵150 = 15000)
    reference = Column(String(200), unique=True)
    status = Column(String(50), default="pending")  # pending, success, failed
    plan = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
