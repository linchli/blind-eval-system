"""
图像对 ORM 模型
"""
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ImagePair(Base):
    __tablename__ = "image_pairs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False, index=True)
    image_a_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    image_b_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    scene = relationship("Scene", back_populates="image_pairs")
    image_a = relationship("Image", foreign_keys=[image_a_id])
    image_b = relationship("Image", foreign_keys=[image_b_id])
    evaluations = relationship("Evaluation", back_populates="pair")

    __table_args__ = (
        UniqueConstraint("image_a_id", "image_b_id", name="uq_image_pair"),
    )
