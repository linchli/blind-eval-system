"""
用户 ORM 模型
"""
from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("admin", "evaluator", "guest"), default="evaluator")
    display_name = Column(String(100), default="")
    created_at = Column(DateTime, server_default=func.now())
    last_active_at = Column(DateTime, nullable=True)
    reset_token = Column(String(100), nullable=True, index=True)
    reset_token_expires = Column(DateTime, nullable=True)

    evaluations = relationship("Evaluation", back_populates="user")
    sessions = relationship("EvalSession", back_populates="user")
