from datetime import UTC, datetime

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from user_note.backend.models import Note
from user_note.backend.schemas.note import (
    Importance,
    NoteCreate,
    NoteUpdate,
    Order,
    SortBy,
    Status,
)

# Rank importance by severity rather than alphabetically.
_IMPORTANCE_RANK = case(
    {level.value: rank for rank, level in enumerate(Importance)},
    value=Note.importance,
)
_SORT_COLUMNS = {
    SortBy.created_at: Note.created_at,
    SortBy.updated_at: Note.updated_at,
    SortBy.title: Note.title,
    SortBy.importance: _IMPORTANCE_RANK,
}


def create_note(db: Session, owner_id: int, data: NoteCreate) -> Note:
    note = Note(owner_id=owner_id, **data.model_dump())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(
    db: Session,
    owner_id: int,
    *,
    status: Status | None = None,
    importance: Importance | None = None,
    search: str | None = None,
    sort_by: SortBy = SortBy.updated_at,
    order: Order = Order.desc,
    limit: int = 50,
    offset: int = 0,
) -> list[Note]:
    stmt = select(Note).where(Note.owner_id == owner_id, Note.deleted_at.is_(None))
    if status is not None:
        stmt = stmt.where(Note.status == status)
    if importance is not None:
        stmt = stmt.where(Note.importance == importance)
    if search:
        stmt = stmt.where(Note.title.icontains(search, autoescape=True))
    column = _SORT_COLUMNS[sort_by]
    direction = column.asc() if order == Order.asc else column.desc()
    tiebreak = Note.id.asc() if order == Order.asc else Note.id.desc()
    stmt = stmt.order_by(direction, tiebreak).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def list_deleted_notes(db: Session, owner_id: int) -> list[Note]:
    stmt = (
        select(Note)
        .where(Note.owner_id == owner_id, Note.deleted_at.is_not(None))
        .order_by(Note.deleted_at.desc(), Note.id.desc())
    )
    return list(db.scalars(stmt))


def get_active_note(db: Session, owner_id: int, note_id: int) -> Note | None:
    stmt = select(Note).where(
        Note.id == note_id, Note.owner_id == owner_id, Note.deleted_at.is_(None)
    )
    return db.scalar(stmt)


def get_deleted_note(db: Session, owner_id: int, note_id: int) -> Note | None:
    stmt = select(Note).where(
        Note.id == note_id, Note.owner_id == owner_id, Note.deleted_at.is_not(None)
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


def restore_note(db: Session, note: Note) -> Note:
    note.deleted_at = None
    db.commit()
    db.refresh(note)
    return note
