"""
排行榜相关 Pydantic 模型
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SceneScore(BaseModel):
    """分场景得分"""
    bt_score: float = 0.0
    mean_score: float = 0.0
    eval_count: int = 0


class RankingItem(BaseModel):
    """排行榜单项"""
    rank: int
    device_id: int
    device_name: str = ""
    main_chip: str = ""
    sensor_model: str = ""
    focal_length: str = ""
    resolution: str = ""
    bt_score: float = 0.0
    mean_score: float = 0.0
    bt_rank: int = 0
    mean_rank: int = 0
    rank_diff: int = 0
    scene_scores: dict[str, SceneScore] = Field(default_factory=dict)


class FilterInfo(BaseModel):
    """筛选信息"""
    type: str
    value: Optional[str] = None


class LeaderboardResponse(BaseModel):
    """排行榜响应"""
    ranking: list[RankingItem] = Field(default_factory=list)
    filter_info: FilterInfo = Field(default_factory=lambda: FilterInfo(type="overall"))
    total_devices: int = 0
    last_updated: Optional[str] = None


class FilterOptions(BaseModel):
    """筛选选项"""
    categories: list[dict[str, Any]] = Field(default_factory=list)
    subcategories: list[dict[str, Any]] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)
    sensors: list[str] = Field(default_factory=list)
    focal_lengths: list[str] = Field(default_factory=list)
    resolutions: list[str] = Field(default_factory=list)


class DeviceRankingDetail(BaseModel):
    """设备排名详情"""
    rank: int
    device_id: int
    device_name: str = ""
    eval_count: int = 0
    mean_score: float = 0.0
    bt_strength: float = 0.0
    bt_rank: int = 0
    mean_rank: int = 0
    rank_diff: int = 0


class SceneDetailResponse(BaseModel):
    """场景详情响应"""
    view_type: str = "scene"
    scene: dict[str, Any] = Field(default_factory=dict)
    device_ranking: list[DeviceRankingDetail] = Field(default_factory=list)
    invalid_users_by_scene: list[dict[str, Any]] = Field(default_factory=list)


class UserDetailResponse(BaseModel):
    """用户详情响应"""
    view_type: str = "user"
    user: dict[str, Any] = Field(default_factory=dict)
    scene_details: list[dict[str, Any]] = Field(default_factory=list)


class DeviceDetailResponse(BaseModel):
    """设备详情响应"""
    view_type: str = "device"
    device: dict[str, Any] = Field(default_factory=dict)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
