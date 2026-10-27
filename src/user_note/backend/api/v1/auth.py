from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from user_note.backend.core.config import settings
from user_note.backend.core.dependencies import get_current_user
from user_note.backend.core.rate_limit import auth_rate_limiter
from user_note.backend.core.security import create_access_token
from user_note.backend.db.session import get_db
from user_note.backend.models import User
from user_note.backend.schemas.auth import LoginRequest, Token, UserCreate, UserRead
from user_note.backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limiter)],
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    try:
        return auth_service.register(db, data)
    except auth_service.UsernameTakenError:
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")


@router.post("/login", response_model=Token, dependencies=[Depends(auth_rate_limiter)])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = auth_service.authenticate(db, data.username, data.password)
    if user is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(
        access_token=create_access_token(user.id),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
