# app/oauth2.py
from jose import JWTError, jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional, Union

from . import schemas, models, database

# --- OAuth2 ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Config (move to config.py in production) ---
SECRET_KEY = "your-super-secret-key-change-in-prod"  # Use .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _verify_token(token: str) -> models.User:
    """Internal: decode and validate JWT, return user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Use dependency injection for db
    db = next(database.get_db())
    user = db.get(models.User, user_id)
    if user is None:
        raise credentials_exception
    return user


# --- HTTP Dependency ---
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db)
) -> models.User:
    """HTTP: Get current user from Bearer token."""
    return _verify_token(token)


# --- WebSocket Dependency ---
async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = None,
    db: Session = Depends(database.get_db)
) -> models.User:
    """
    WebSocket: Extract token from query param or header.
    Format: ?token=xxx or Authorization: Bearer xxx
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Try query param: ws://.../ws/123?token=xxx
    if token is None:
        query_token = websocket.query_params.get("token")
        if query_token:
            token = query_token

    # 2. Try Authorization header
    if token is None:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        await websocket.close(code=4001)  # Custom code: missing token
        raise credentials_exception

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            await websocket.close(code=4001)
            raise credentials_exception
    except JWTError:
        await websocket.close(code=4001)
        raise credentials_exception

    user = db.get(models.User, user_id)
    if user is None:
        await websocket.close(code=4001)
        raise credentials_exception

    return user