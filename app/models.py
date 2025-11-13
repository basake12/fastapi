# app/models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime


# Many-to-many: Users vote on Posts
votes = Table(
    "votes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("post_id", Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Argon2 hash
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=True)  # Fixed typo

    # Relationships
    posts = relationship("Post", back_populates="owner", cascade="all, delete-orphan")
    voted_posts = relationship(
        "Post",
        secondary=votes,
        back_populates="voted_by",
        lazy="joined"
    )
    comments = relationship("Comment", back_populates="owner", cascade="all, delete-orphan")
    sent_messages = relationship("ChatMessage", foreign_keys="ChatMessage.sender_id", back_populates="sender")
    received_messages = relationship("ChatMessage", foreign_keys="ChatMessage.receiver_id", back_populates="receiver")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    content = Column(String, nullable=False)
    published = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    owner = relationship("User", back_populates="posts")
    voted_by = relationship(
        "User",
        secondary=votes,
        back_populates="voted_posts",
        lazy="joined"
    )
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    @property
    def votes_count(self) -> int:
        return len(self.voted_by)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Foreign Keys
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Relationships
    post = relationship("Post", back_populates="comments")
    owner = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", back_populates="parent", cascade="all, delete-orphan")

    @property
    def depth(self) -> int:
        """Calculate reply depth (0 = top-level, 1 = reply, etc.)"""
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    sender_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")