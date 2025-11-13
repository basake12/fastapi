# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from . import models
from .database import engine
from .routers import user, post, auth, vote, comment, chat  # Added comment & chat
from .config import settings
from fastapi.middleware.cors import CORSMiddleware


# Allow all origins in development (update for production)
origins = ["*"]  # or ["https://your-frontend.com"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Optional: Auto-create tables (dev only)
    # models.Base.metadata.create_all(bind=engine)
    print(f"API started with DB: {settings.DATABASE_URL}")
    yield


app = FastAPI(
    title="Twitter Clone API",
    version="1.0.0",
    description="Clean, modern API — no nested paths",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with prefixes and tags (NO trailing slashes)
app.include_router(post.router, tags=["posts"])
app.include_router(user.router,  tags=["users"])
app.include_router(auth.router, tags=["auth"])
app.include_router(vote.router,  tags=["vote"])
app.include_router(comment.router, prefix="", tags=["comments"])  # /posts/{post_id}/comments
app.include_router(chat.router,  tags=["chat"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to the clean API!",
        "endpoints": {
            "login": "/auth/login",
            "users": "/users",
            "posts": "/posts",
            "vote": "/vote",
            "comments": "/posts/{post_id}/comments",
            "chat": "/chat/ws/{receiver_id}",
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }