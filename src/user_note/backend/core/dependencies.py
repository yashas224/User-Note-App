from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from user_note.backend.core.security import decode_access_token
from user_note.backend.db.session import get_db
from user_note.backend.models import User

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None or not user.is_active:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_user_id(user: User = Depends(get_current_user)) -> int:
    return user.id
