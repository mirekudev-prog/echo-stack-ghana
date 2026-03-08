from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.types import TypeDecorator, CHAR
from datetime import datetime
import uuid
from database import Base


# ============================================================
# UUID TYPE — stores as CHAR(36) in SQLite, portable to Postgres
# ============================================================
class GUID(TypeDecorator):
    """Platform-independent GUID. Stores as CHAR(36) string."""
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(str(value))


def new_uuid():
    return uuid.uuid4()


# ============================================================
# REGION
# ============================================================
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
    video_files = Column(String)
    documents = Column(String)
    source = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# UPLOADED FILE
# ============================================================
class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255))
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    category = Column(String(50))
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    description = Column(Text)
    uploaded_by = Column(String(100))
    is_public = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# SECTION / CATEGORY
# ============================================================
class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), unique=True)
    description = Column(Text)
    parent_section_id = Column(Integer, ForeignKey("sections.id"), nullable=True)
    display_order = Column(Integer, default=0)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# USER
# ============================================================
class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=new_uuid)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    full_name = Column(String(200))
    bio = Column(Text)
    interests = Column(Text)
    avatar_url = Column(String(500))

    # Role & plan
    # Roles: user | creator | admin | superuser
    role = Column(String(20), default="user")
    is_premium = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# CREATOR CHANNEL
# ============================================================
class CreatorChannel(Base):
    __tablename__ = "creator_channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, unique=True)
    channel_name = Column(String(200))
    channel_desc = Column(Text)
    cover_image = Column(String(500))
    avatar_url = Column(String(500))
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# POST
# ============================================================
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    author_username = Column(String(80), default="")

    title = Column(String(500), nullable=False)
    excerpt = Column(Text)
    content = Column(Text)
    cover_image = Column(String(500))
    # article | audio | photo_essay | video
    content_type = Column(String(50), default="article")

    # Media
    audio_url = Column(String(500))
    video_url = Column(String(500))
    gallery = Column(Text)          # comma-separated or JSON array of image URLs

    tags = Column(String)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)

    # draft | published | rejected
    status = Column(String(20), default="draft")
    is_premium = Column(Boolean, default=False)

    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)

    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# COMMENT
# ============================================================
class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    author_username = Column(String(80), default="")
    content = Column(Text, nullable=False)
    is_approved = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# FOLLOW
# ============================================================
class Follow(Base):
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    following_id = Column(GUID(), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# STORY SUBMISSION
# ============================================================
class StorySubmission(Base):
    __tablename__ = "story_submissions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    username = Column(String(80))
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    # pending | approved | rejected
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# NEWSLETTER SUBSCRIBER
# ============================================================
class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    subscribed_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# EVENT
# ============================================================
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    event_date = Column(String(100))    # stored as string for flexibility
    location = Column(String(300))
    image_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# CHAT MESSAGE
# ============================================================
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    username = Column(String(80), nullable=False)
    message = Column(String(500), nullable=False)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=True)
    is_approved = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# PAYMENT
# ============================================================
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True)
    email = Column(String(200))
    amount = Column(Integer)            # in pesewas (GHS × 100)
    reference = Column(String(200), unique=True)
    # pending | success | failed
    status = Column(String(20), default="pending")
    plan = Column(String(50), default="premium")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
