"""
图像记录 ORM 模型
"""
from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class Image(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=False, index=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False, comment="图像文件相对路径")
    thumb_path = Column(String(500), default="", comment="缩略图相对路径")
    model_attrs = Column(JSON, default=dict, comment="采集设备属性快照")
    env_attrs = Column(JSON, default=dict, comment="场景环境属性")
    isp_attrs = Column(JSON, default=dict, comment="ISP参数")
    note_attrs = Column(JSON, default=dict, comment="备注信息")
    created_at = Column(DateTime, server_default=func.now())

    scene = relationship("Scene", back_populates="images")
    model = relationship("DeviceModel", back_populates="images")

    __table_args__ = (
        UniqueConstraint("scene_id", "model_id", name="uq_scene_model"),
    )
