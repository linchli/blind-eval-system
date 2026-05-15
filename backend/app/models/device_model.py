"""
机型 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class DeviceModel(Base):
    __tablename__ = "models"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="机型名称（需含版本后缀）")
    folder_name = Column(String(200), unique=True, nullable=False, comment="存储目录名")
    main_chip = Column(String(100), default="", comment="主控型号")
    lens_model = Column(String(100), default="", comment="镜头型号")
    sensor_model = Column(String(100), default="", comment="Sensor型号")
    focal_length = Column(String(50), default="", comment="焦距")
    resolution = Column(String(50), default="", comment="分辨率")
    housing_info = Column(String(100), default="", comment="壳体信息")
    device_attrs = Column(JSON, default=dict, comment="低频扩展参数")
    features = Column(Text, default="", comment="机型特点")
    created_at = Column(DateTime, server_default=func.now())

    images = relationship("Image", back_populates="model")
