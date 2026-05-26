"""
认证路由
"""
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.security import verify_password, hash_password, create_access_token
from ..core.dependencies import get_current_user
from ..models.user import User
from ..schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut, ResetPasswordRequest
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.last_active_at = datetime.now()
    db.commit()

    token = create_access_token({"sub": str(user.id), "role": user.role})
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        display_name=user.display_name or user.username,
    )


@router.post("/register", response_model=ApiResponse)
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, req.email):
        raise HTTPException(status_code=400, detail="邮箱格式无效")

    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被使用")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        role="evaluator",
        display_name=req.username,
    )
    db.add(user)
    db.commit()
    return ApiResponse(success=True, message="注册成功，请使用新账号登录")


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        display_name=current_user.display_name or current_user.username,
        created_at=str(current_user.created_at) if current_user.created_at else None,
    )


@router.get("/verify-reset-token")
async def verify_reset_token(token: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="无效的重置链接")
    if user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="重置链接已过期，请联系管理员重新生成")
    return {"valid": True, "username": user.username}


@router.post("/reset-password", response_model=ApiResponse)
async def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")

    user = db.query(User).filter(User.reset_token == req.token).first()
    if not user:
        raise HTTPException(status_code=400, detail="无效的重置链接")
    if user.reset_token_expires < datetime.utcnow():
        raise HTTPException(status_code=400, detail="重置链接已过期，请联系管理员重新生成")

    user.password_hash = hash_password(req.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()
    return ApiResponse(success=True, message="密码重置成功，请使用新密码登录")
