"""
设备 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class DeviceModel(Base):
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, comment="设备名称（需含版本后缀）")
    folder_name = Column(String(200), unique=True, nullable=False, comment="存储目录名")

    # 核心参数（高频筛选）
    main_chip = Column(String(100), default="", comment="主控型号")
    lens_model = Column(String(100), default="", comment="镜头型号")
    sensor_model = Column(String(100), default="", comment="Sensor型号")
    aperture = Column(String(50), default="", comment="光圈 (如 f/1.6)")
    focal_length = Column(String(50), default="", comment="焦距")
    resolution = Column(String(50), default="", comment="分辨率")
    frame_rate = Column(String(50), default="", comment="帧率 (如 30fps)")
    white_led = Column(String(100), default="", comment="白光灯珠料号")
    ir_led = Column(String(100), default="", comment="红外灯珠料号")
    housing_info = Column(String(100), default="", comment="壳体信息")

    # 扩展参数
    device_attrs = Column(JSON, default=dict, comment="低频扩展参数 (固件版本等)")
    features = Column(Text, default="", comment="设备特点")
    created_at = Column(DateTime, server_default=func.now())

    images = relationship("Image", back_populates="device")
