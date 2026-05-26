"""
排行榜结果 ORM 模型
"""
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.sql import func

from ..core.database import Base


class RankingResult(Base):
    __tablename__ = "ranking_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False, index=True)
    scene_id = Column(Integer, ForeignKey("scenes.id"), nullable=True, index=True)
    score = Column(Float, nullable=False, comment="0-100 综合得分")
    rank = Column(Integer, nullable=False, comment="排名")
    confidence_min = Column(Float, default=0, comment="置信区间下限偏移")
    confidence_max = Column(Float, default=0, comment="置信区间上限偏移")
    eval_count = Column(Integer, default=0, comment="参与评测的图对数")
    created_at = Column(DateTime, server_default=func.now())
