from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from user_note.backend.core.security import DUMMY_HASH, hash_password, verify_password
from user_note.backend.models import User
from user_note.backend.schemas.auth import UserCreate


class UsernameTakenError(Exception):
    pass


def register(db: Session, data: UserCreate) -> User:
    user = User(username=data.username, password_hash=hash_password(data.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise UsernameTakenError
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.scalar(select(User).where(func.lower(User.username) == username.lower()))
    if user is None:
        verify_password(password, DUMMY_HASH)
        return None
    if not verify_password(password, user.password_hash) or not user.is_active:
        return None
    return user
