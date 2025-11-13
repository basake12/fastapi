# app/routers/vote.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas, database, oauth2


router = APIRouter(prefix="/vote", tags=["vote"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=schemas.PostResponse)
def vote(
    vote: schemas.VoteCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(oauth2.get_current_user),
):
    # Load post + voted_by in ONE query
    post = (
        db.query(models.Post)
        .options(joinedload(models.Post.voted_by))
        .filter(models.Post.id == vote.post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    already_voted = current_user in post.voted_by

    if vote.dir == 1:  # Upvote
        if already_voted:
            raise HTTPException(status_code=409, detail="Already voted")
        post.voted_by.append(current_user)
    else:  # Remove vote
        if not already_voted:
            raise HTTPException(status_code=404, detail="Vote does not exist")
        post.voted_by.remove(current_user)

    db.commit()
    db.refresh(post)

    # Build response with correct fields
    response = schemas.PostResponse.from_orm(post)
    response.votes_count = len(post.voted_by)
    response.is_voted = current_user in post.voted_by
    return response