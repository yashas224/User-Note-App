from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from user_note.backend.models import Note
from user_note.backend.schemas.note import NoteCreate, NoteUpdate


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


def get_active_note(db: Session, owner_id: int, note_id: int) -> Note | None:
    stmt = select(Note).where(
        Note.id == note_id, Note.owner_id == owner_id, Note.deleted_at.is_(None)
    )
    return db.scalar(stmt)


def update_note(db: Session, note: Note, data: NoteUpdate) -> Note:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)
    db.commit()
    db.refresh(note)
    return note


def soft_delete_note(db: Session, note: Note) -> None:
    note.deleted_at = datetime.now(UTC)
    db.commit()
