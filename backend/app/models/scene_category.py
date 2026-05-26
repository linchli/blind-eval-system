"""
大类 × 地点 ORM 模型
"""
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class SceneCategory(Base):
    __tablename__ = "scene_categories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, comment="大类名：车库、池塘、天台")
    location = Column(String(200), nullable=False, default="", comment="采集地点：留仙洞、光明塘、32楼花园")
    created_at = Column(DateTime, server_default=func.now())

    scenes = relationship("Scene", back_populates="category")

    __table_args__ = (
        UniqueConstraint("name", "location", name="uq_category_name_location"),
    )

    def __repr__(self):
        return f"<SceneCategory {self.name}({self.location})>"
