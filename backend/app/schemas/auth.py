"""
认证相关 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    display_name: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    created_at: Optional[str] = None


class AdminUserOut(BaseModel):
    id: int
    username: str
    email: str
    role: str
    display_name: str
    created_at: Optional[str] = None
    last_active_at: Optional[str] = None
    has_active_reset: bool = False
    evaluation_count: int = 0


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
