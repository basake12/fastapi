# app/routers/comment.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List
from .. import models, schemas, database, oauth2


router = APIRouter(
    prefix="/posts/{post_id}/comments",
    tags=["comments"],
    responses={404: {"description": "Not found"}}
)


def get_post_or_404(db: Session, post_id: int) -> models.Post:
    """Helper: fetch post with joinedload or 404"""
    post = db.query(models.Post).options(
        joinedload(models.Post.owner),
        joinedload(models.Post.voted_by)
    ).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail=f"Post with id {post_id} not found")
    return post


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.CommentResponse,
    summary="Create a comment or reply"
)
def create_comment(
    post_id: int,
    comment_in: schemas.CommentCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    post = get_post_or_404(db, post_id)

    # Validate parent_id if provided
    if comment_in.parent_id:
        parent = db.query(models.Comment).filter(
            models.Comment.id == comment_in.parent_id,
            models.Comment.post_id == post_id
        ).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent comment not found")

    db_comment = models.Comment(
        **comment_in.dict(),
        post_id=post_id,
        owner_id=current_user.id
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)

    # Load full tree for response
    return _load_comment_with_replies(db, db_comment)


@router.get(
    "/",
    response_model=List[schemas.CommentResponse],
    summary="Get all top-level comments with nested replies"
)
def get_comments(
    post_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user, use_cache=True)
):
    post = get_post_or_404(db, post_id)

    # Get top-level comments (parent_id IS NULL)
    top_comments = db.query(models.Comment).filter(
        models.Comment.post_id == post_id,
        models.Comment.parent_id.is_(None)
    ).order_by(models.Comment.created_at.asc()).all()

    return [_load_comment_with_replies(db, c, current_user=current_user) for c in top_comments]


def _load_comment_with_replies(
    db: Session,
    comment: models.Comment,
    current_user: models.User = None
) -> schemas.CommentResponse:
    """
    Recursively load comment + replies with owner data.
    Uses joinedload to avoid N+1.
    """
    # Reload with full relationships
    db_comment = db.query(models.Comment).options(
        joinedload(models.Comment.owner),
        joinedload(models.Comment.replies).joinedload(models.Comment.owner)
    ).filter(models.Comment.id == comment.id).first()

    response = schemas.CommentResponse.from_orm(db_comment)
    response.replies = [
        _load_comment_with_replies(db, reply, current_user)
        for reply in db_comment.replies
    ]
    return response