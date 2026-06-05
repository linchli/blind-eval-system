"""
场景 ORM 模型
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey("scene_categories.id"), nullable=False)
    subcategory_id = Column(Integer, ForeignKey("scene_subcategories.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    category = relationship("SceneCategory", back_populates="scenes")
    subcategory = relationship("SceneSubcategory", back_populates="scenes")
    images = relationship("Image", back_populates="scene")
    image_pairs = relationship("ImagePair", back_populates="scene")

    __table_args__ = (
        UniqueConstraint("category_id", "subcategory_id", name="uq_scene_category_subcategory"),
    )

    @property
    def folder_name(self) -> str:
        return f"scene_{self.id}"

    @property
    def category_name(self) -> str:
        return self.category.name if self.category else ""

    @property
    def location(self) -> str:
        return self.category.location if self.category else ""

    @property
    def subcategory_name(self) -> str:
        return self.subcategory.name if self.subcategory else ""

    @property
    def name(self) -> str:
        """兼容旧代码：返回 大类名(地点)-子类名"""
        cat_part = self.category_name
        if self.location:
            cat_part = f"{cat_part}({self.location})"
        return f"{cat_part}-{self.subcategory_name}" if self.subcategory_name else cat_part
