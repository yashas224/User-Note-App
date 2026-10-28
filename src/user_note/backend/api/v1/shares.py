from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from user_note.backend.api.v1.notes import get_owned_note
from user_note.backend.db.session import get_db
from user_note.backend.models import Note
from user_note.backend.schemas.share import (
    ShareCreate,
    ShareCreated,
    SharedNote,
    ShareRead,
)
from user_note.backend.services import share_service

router = APIRouter(tags=["sharing"])


@router.post(
    "/notes/{note_id}/shares",
    response_model=ShareCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_share(
    data: ShareCreate,
    note: Note = Depends(get_owned_note),
    db: Session = Depends(get_db),
):
    share, share_url = share_service.create_share(db, note, data.expires_in_days)
    return ShareCreated(id=share.id, share_url=share_url, expires_at=share.expires_at)


@router.get("/notes/{note_id}/shares", response_model=list[ShareRead])
def list_shares(note: Note = Depends(get_owned_note), db: Session = Depends(get_db)):
    return share_service.list_shares(db, note)


@router.delete(
    "/notes/{note_id}/shares/{share_id}", status_code=status.HTTP_204_NO_CONTENT
)
def revoke_share(
    share_id: int,
    note: Note = Depends(get_owned_note),
    db: Session = Depends(get_db),
):
    share = share_service.get_share(db, note, share_id)
    if share is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share not found")
    share_service.revoke_share(db, share)


@router.get("/shared/{token}", response_model=SharedNote)
def read_shared_note(token: str = Path(max_length=128), db: Session = Depends(get_db)):
    # One generic error for unknown, revoked, expired and deleted-note links.
    note = share_service.get_shared_note(db, token)
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Link is invalid or has expired")
    return note
