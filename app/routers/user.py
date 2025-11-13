# app/routers/user.py
from fastapi import APIRouter, Depends, HTTPException, Path, status, Body
from sqlalchemy.orm import Session
from typing import Literal

from .. import models, schemas, utils
from ..database import get_db


router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.UserResponse,
    summary="Create a new user",
)
def create_user(
    user: schemas.UserCreate = Body(...),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    """
    Register a new user.

    - **email** must be unique
    - **username** must be unique
    - Password is hashed with Argon2 (via `utils.hash_password`)
    """
    # Check for duplicate email OR username
    existing = db.query(models.User).filter(
        (models.User.email == user.email) |
        (models.User.username == user.username)
    ).first()

    if existing:
        field: Literal["email", "username"] = (
            "email" if existing.email == user.email else "username"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field.capitalize()} already registered",
        )

    # Hash password using shared utility
    hashed = utils.hash_password(user.password)

    db_user = models.User(
        email=user.email,
        username=user.username,
        password=hashed,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get(
    "/{user_id}",
    response_model=schemas.UserResponse,
    summary="Get user by ID",
)
def get_user(
    user_id: int = Path(..., ge=1, description="The ID of the user to retrieve"),
    db: Session = Depends(get_db),
) -> schemas.UserResponse:
    """
    Retrieve a user by their numeric ID.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found",
        )
    return user