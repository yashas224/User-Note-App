from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from user_note.backend.core.dependencies import get_current_user_id
from user_note.backend.db.session import get_db
from user_note.backend.schemas.note import NoteCreate, NoteRead
from user_note.backend.services import note_service

router = APIRouter(prefix="/notes", tags=["notes"])


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
