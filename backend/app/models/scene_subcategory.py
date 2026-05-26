"""
子类/时段 ORM 模型（全局共享）
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class SceneSubcategory(Base):
    __tablename__ = "scene_subcategories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, comment="白天、低照、夜晚红外、夜晚白光")
    created_at = Column(DateTime, server_default=func.now())

    scenes = relationship("Scene", back_populates="subcategory")

    def __repr__(self):
        return f"<SceneSubcategory {self.name}>"
