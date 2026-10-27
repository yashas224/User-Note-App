from sqlalchemy import select
from sqlalchemy.orm import Session

from user_note.backend.models import Note
from user_note.backend.schemas.note import NoteCreate


def create_note(db: Session, owner_id: int, data: NoteCreate) -> Note:
    note = Note(owner_id=owner_id, **data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, owner_id: int) -> list[Note]:
    stmt = (
        select(Note)
        .where(Note.owner_id == owner_id, Note.deleted_at.is_(None))
        .order_by(Note.updated_at.desc())
    )
    return list(db.scalars(stmt))
