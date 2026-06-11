"""
排行榜排名 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.sql import func

from ..core.database import Base


class LeaderboardRanking(Base):
    __tablename__ = "leaderboard_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 筛选维度
    filter_type = Column(String(50), nullable=False, comment="筛选类型: overall/category/location/subcategory/scene/chip/sensor/focal_length/resolution")
    filter_value = Column(String(200), nullable=True, comment="筛选值")

    # 设备基础信息
    device_id = Column(Integer, nullable=False, index=True)
    device_name = Column(String(100))

    # 高频筛选字段
    main_chip = Column(String(100))
    sensor_model = Column(String(100))
    focal_length = Column(String(50))
    resolution = Column(String(50))

    # 扩展属性
    device_attrs = Column(JSON, comment="设备扩展属性")

    # 得分
    bt_score = Column(Float, comment="BT得分")
    mean_score = Column(Float, comment="评分均值")
    rank_position = Column(Integer, comment="排名")

    # 分场景得分
    scene_scores = Column(JSON, comment='分场景得分 {"场景名": {"bt_score": xx, "mean_score": xx, "eval_count": xx}, ...}')

    # 管理员详细数据
    detail_data = Column(JSON, comment="详细评测数据")

    # 元数据
    total_devices = Column(Integer, nullable=False, default=0, comment="参评设备数")
    cleaned_record_count = Column(Integer, nullable=False, default=0, comment="清洗时有效记录数")
    last_cleaned_at = Column(DateTime, nullable=False, comment="最后清洗时间")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("filter_type", "filter_value", "device_id", name="uk_filter_device"),
        Index("idx_rank", "filter_type", "filter_value", "rank_position"),
        Index("idx_lb_device", "device_id"),
    )
