"""User persistence queries."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def get_user(session: Session, user_id: uuid.UUID) -> User | None:
    """Find a user by primary key."""
    return session.get(User, user_id)


def get_by_email(session: Session, email: str) -> User | None:
    """Find a user by normalized email."""
    return session.scalar(select(User).where(User.email == email))


def add_user(session: Session, name: str, email: str) -> User:
    """Persist a new user in the caller's transaction."""
    user = User(name=name, email=email)
    session.add(user)
    session.flush()
    return user
