from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from user_note.backend.core.dependencies import get_current_user_id
from user_note.backend.db.session import get_db
from user_note.backend.models import Note
from user_note.backend.schemas.note import NoteCreate, NoteRead, NoteUpdate
from user_note.backend.services import note_service

router = APIRouter(prefix="/notes", tags=["notes"])


def get_owned_note(
    note_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
) -> Note:
    # Same 404 for missing, deleted or someone else's note, to hide existence.
    note = note_service.get_active_note(db, user_id, note_id)
    if note is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    return note


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(
    data: NoteCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    return note_service.create_note(db, user_id, data)


@router.get("", response_model=list[NoteRead])
def list_notes(
    db: Session = Depends(get_db), user_id: int = Depends(get_current_user_id)
):
    return note_service.list_notes(db, user_id)


@router.get("/{note_id}", response_model=NoteRead)
def get_note(note: Note = Depends(get_owned_note)):
    return note


@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    data: NoteUpdate,
    note: Note = Depends(get_owned_note),
    db: Session = Depends(get_db),
):
    return note_service.update_note(db, note, data)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note: Note = Depends(get_owned_note), db: Session = Depends(get_db)):
    note_service.soft_delete_note(db, note)
