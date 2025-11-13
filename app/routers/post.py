# app/routers/post.py
from fastapi import APIRouter, Depends, HTTPException, Path, status, Body, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from sqlalchemy import or_

from .. import models, schemas, database, oauth2


router = APIRouter(
    prefix="/posts",
    tags=["posts"],
    responses={404: {"description": "Not found"}},
)

forbidden_exception = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Not authorized to perform this action"
)


def _enrich_post(post: models.Post, current_user: Optional[models.User] = None):
    """Add votes_count & is_voted to PostResponse."""
    response = schemas.PostResponse.from_orm(post)
    response.votes_count = len(post.voted_by)
    response.is_voted = current_user in post.voted_by if current_user else False
    return response


# ---------- GET (public) ----------
@router.get("/", response_model=List[schemas.PostResponse])
def get_posts(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    q: Optional[str] = Query(None, alias="q"),
    current_user: Optional[models.User] = Depends(oauth2.get_current_user, use_cache=True),
):
    query = db.query(models.Post).options(joinedload(models.Post.voted_by)).order_by(models.Post.id.desc())

    if q:
        pattern = f"%{q}%"
        query = query.filter(or_(models.Post.title.ilike(pattern), models.Post.content.ilike(pattern)))

    posts = query.offset(skip).limit(limit).all()
    return [_enrich_post(p, current_user) for p in posts]


@router.get("/{post_id}", response_model=schemas.PostResponse)
def get_post(
    post_id: int = Path(..., ge=1),
    db: Session = Depends(database.get_db),
    current_user: Optional[models.User] = Depends(oauth2.get_current_user, use_cache=True),
):
    post = db.query(models.Post).options(joinedload(models.Post.voted_by)).get(post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {post_id} not found")
    return _enrich_post(post, current_user)


# ---------- CREATE ----------
@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PostResponse)
def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    new_post = models.Post(**post.dict(), owner_id=current_user.id)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    return _enrich_post(new_post, current_user)


# ---------- UPDATE / DELETE ----------
@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int = Path(..., ge=1),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    post = db.get(models.Post, post_id)
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {post_id} not found")
    if post.owner_id != current_user.id:
        raise forbidden_exception
    db.delete(post)
    db.commit()
    return None


@router.put("/{post_id}", response_model=schemas.PostResponse)
def update_post(
    post_id: int = Path(..., ge=1),
    post: schemas.PostCreate = Body(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    db_post = db.get(models.Post, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail=f"Post with id {post_id} not found")
    if db_post.owner_id != current_user.id:
        raise forbidden_exception

    for k, v in post.dict().items():
        setattr(db_post, k, v)

    db.commit()
    db.refresh(db_post)
    return _enrich_post(db_post, current_user)


@router.patch("/{post_id}", response_model=schemas.PostResponse)
def partial_update_post(
    post_id: int = Path(..., ge=1),
    post: schemas.PostUpdate = Body(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    db_post = db.get(models.Post, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail=f"Post with id {post_id} not found")
    if db_post.owner_id != current_user.id:
        raise forbidden_exception

    data = post.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(db_post, k, v)

    db.commit()
    db.refresh(db_post)
    return _enrich_post(db_post, current_user)