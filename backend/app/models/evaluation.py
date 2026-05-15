"""
评测相关 ORM 模型（EvalSession + Evaluation）
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class EvalSession(Base):
    __tablename__ = "eval_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(Enum("active", "completed"), default="active", nullable=False)
    pair_ids = Column(JSON, nullable=False)
    batch_size = Column(Integer, nullable=False)
    started_at = Column(DateTime, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
    evaluations = relationship("Evaluation", back_populates="session")


class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    pair_id = Column(Integer, ForeignKey("image_pairs.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("eval_sessions.id"), nullable=True)
    score = Column(String(20), nullable=False)
    score_label = Column(String(20), nullable=False)
    score_a = Column(Float, nullable=False)
    score_b = Column(Float, nullable=False)
    left_model_key = Column(String(1), nullable=False)
    right_model_key = Column(String(1), nullable=False)
    view_duration_ms = Column(Integer, default=0)
    status = Column(Enum("draft", "submitted"), default="draft", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    submitted_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="evaluations")
    pair = relationship("ImagePair", back_populates="evaluations")
    session = relationship("EvalSession", back_populates="evaluations")

    __table_args__ = (
        UniqueConstraint("user_id", "pair_id", name="uq_user_pair"),
    )
