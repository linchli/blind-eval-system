"""
依赖注入：当前用户、管理员权限校验
"""
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from .database import get_db
from .security import decode_token
from ..models.user import User


async def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = authorization[7:]
    payload = decode_token(token)
    user_id = int(payload.get("sub", 0))
    if not user_id:
        raise HTTPException(status_code=401, detail="令牌无效")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_optional_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """可选的用户认证，未登录时返回 None"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization[7:]
        payload = decode_token(token)
        user_id = int(payload.get("sub", 0))
        if not user_id:
            return None
        return db.query(User).filter(User.id == user_id).first()
    except Exception:
        return None


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user
