"""
场景分类 ORM 模型
"""
from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False, comment="大类（如：池塘、公园）")
    subcategory = Column(String(50), nullable=False, comment="子类/时段（如：白天、傍晚）")
    name = Column(String(100), unique=True, nullable=False, comment="场景全名=大类-子类")
    folder_name = Column(String(200), unique=True, nullable=False, comment="存储目录名")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    images = relationship("Image", back_populates="scene")
    image_pairs = relationship("ImagePair", back_populates="scene")
