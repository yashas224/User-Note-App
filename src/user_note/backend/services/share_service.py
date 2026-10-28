import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from user_note.backend.core.config import settings
from user_note.backend.models import Note, NoteShare


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_share(
    db: Session, note: Note, expires_in_days: int | None
) -> tuple[NoteShare, str]:
    """Create a share and return it with its share URL, the only time the raw
    token is available."""
    token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) + timedelta(days=expires_in_days)
        if expires_in_days is not None
        else None
    )
    share = NoteShare(
        note_id=note.id, token_hash=_hash_token(token), expires_at=expires_at
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share, f"{settings.PUBLIC_BASE_URL.rstrip('/')}/?share={token}"


def list_shares(db: Session, note: Note) -> list[NoteShare]:
    stmt = (
        select(NoteShare)
        .where(NoteShare.note_id == note.id)
        .order_by(NoteShare.created_at.desc(), NoteShare.id.desc())
    )
    return list(db.scalars(stmt))


def get_share(db: Session, note: Note, share_id: int) -> NoteShare | None:
    stmt = select(NoteShare).where(
        NoteShare.id == share_id, NoteShare.note_id == note.id
    )
    return db.scalar(stmt)


def revoke_share(db: Session, share: NoteShare) -> None:
    if share.revoked_at is None:
        share.revoked_at = datetime.now(UTC)
        db.commit()


def get_shared_note(db: Session, token: str) -> Note | None:
    """Return the note for a valid link: not revoked, not expired, note not
    deleted."""
    stmt = (
        select(Note)
        .join(NoteShare, NoteShare.note_id == Note.id)
        .where(
            NoteShare.token_hash == _hash_token(token),
            NoteShare.revoked_at.is_(None),
            or_(
                NoteShare.expires_at.is_(None),
                NoteShare.expires_at > datetime.now(UTC),
            ),
            Note.deleted_at.is_(None),
        )
    )
    return db.scalar(stmt)
