"""User REST endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.modules.users.schemas import UserCreate, UserRead
from app.modules.users.service import create_user, retrieve_user

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=201)
def post_user(payload: UserCreate, session: Session = Depends(get_session)) -> UserRead:
    """Create a user."""
    return UserRead.model_validate(create_user(session, payload.name, str(payload.email)))


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, session: Session = Depends(get_session)) -> UserRead:
    """Get a user by ID."""
    return UserRead.model_validate(retrieve_user(session, user_id))
