"""
数据库连接与会话管理
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _get_url():
    if DATABASE_URL:
        return DATABASE_URL
    from .config import SQLALCHEMY_DATABASE_URL
    return SQLALCHEMY_DATABASE_URL


engine = create_engine(
    _get_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖注入：获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
