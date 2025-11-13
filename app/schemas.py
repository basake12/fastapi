# app/schemas.py
from pydantic import BaseModel, validator
from typing import Optional, Literal, List
from datetime import datetime


# --- Existing Schemas (unchanged, cleaned) ---
class PostBase(BaseModel):
    title: str
    content: str


class PostCreate(PostBase):
    pass


class PostUpdate(PostBase):
    title: Optional[str] = None
    content: Optional[str] = None

    class Config:
        from_attributes = True


class UserBase(BaseModel):
    email: str
    username: str
    phone_number: Optional[str] = None  # Added to match model


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostResponse(PostBase):
    id: int
    created_at: datetime
    owner_id: int
    owner: UserResponse
    votes_count: int
    is_voted: bool = False

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[int] = None
    username: Optional[str] = None


class VoteCreate(BaseModel):
    post_id: int
    dir: Literal[1, 0]

    @validator("dir")
    def dir_must_be_0_or_1(cls, v):
        if v not in (0, 1):
            raise ValueError("dir must be 0 or 1")
        return v


# --- NEW: Comment Schemas ---
class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    parent_id: Optional[int] = None  # For threaded replies


class CommentResponse(CommentBase):
    id: int
    created_at: datetime
    post_id: int
    owner_id: int
    parent_id: Optional[int] = None
    depth: int
    owner: UserResponse
    replies: List["CommentResponse"] = []  # Recursive replies

    class Config:
        from_attributes = True


# --- NEW: Chat Message Schemas ---
class ChatMessageCreate(BaseModel):
    content: str
    receiver_id: int


class ChatMessageResponse(BaseModel):
    id: int
    content: str
    created_at: datetime
    sender_id: int
    receiver_id: int
    sender: UserResponse
    receiver: UserResponse

    class Config:
        from_attributes = True


# Enable forward reference for CommentResponse
CommentResponse.update_forward_refs()