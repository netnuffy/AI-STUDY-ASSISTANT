"""User registration and authentication logic."""

from sqlalchemy.orm import Session

from core.exceptions import ConflictError
from core.security import hash_password, verify_password
from models.user import User
from schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def register_user(db: Session, data: UserCreate) -> User:
    if get_user_by_email(db, data.email):
        raise ConflictError("An account with this email already exists")
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
