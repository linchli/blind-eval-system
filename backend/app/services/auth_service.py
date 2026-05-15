"""
认证服务
"""
from sqlalchemy.orm import Session

from ..models.user import User
from ..core.security import verify_password, hash_password, create_access_token


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_token_for_user(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {
        "access_token": token,
        "role": user.role,
        "username": user.username,
        "display_name": user.display_name or user.username,
    }
