"""
数据清洗相关 Pydantic 模型
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── 枚举 ──────────────────────────────────────────────────────────────────────

class RejectType(str, Enum):
    """拒绝类型"""
    RETEST_RELIABILITY = "retest_reliability"
    GROUP_CONSENSUS = "group_consensus"
    INSUFFICIENT_RETEST = "insufficient_retest"


# ── 清洗参数 ──────────────────────────────────────────────────────────────────

class CleaningParams(BaseModel):
    """清洗参数配置"""
    retest_agreement_threshold: float = Field(0.70, ge=0.50, le=0.90, description="重测一致性阈值")
    retest_hard_reject_threshold: float = Field(0.55, ge=0.30, le=0.70, description="重测硬拒绝阈值")
    group_max_threshold: float = Field(0.85, ge=0.60, le=1.00, description="用户组最大阈值")
    retest_ratio: float = Field(0.10, ge=0.05, le=0.30, description="复评比例要求")
    min_devices_per_scene: int = Field(2, ge=2, le=10, description="最小设备数")


# ── 输入记录 ──────────────────────────────────────────────────────────────────

class EvalRecord(BaseModel):
    """单条盲评记录 — 清洗必需字段"""
    eval_id: int = Field(..., description="evaluations.id")
    user_id: int = Field(..., description="evaluations.user_id")
    pair_id: int = Field(..., description="evaluations.pair_id")
    session_id: Optional[int] = Field(None, description="evaluations.session_id")
    scene_id: int = Field(..., description="image_pairs.scene_id")
    device_a_id: int = Field(..., description="image_pairs.device_a_id (通过 image_a.device_id)")
    device_b_id: int = Field(..., description="image_pairs.device_b_id (通过 image_b.device_id)")
    score_a: float = Field(..., ge=0.0, le=2.0, description="设备 A 得分 0~2")
    score_b: float = Field(..., ge=0.0, le=2.0, description="设备 B 得分 0~2")


# ── 清洗详情 ──────────────────────────────────────────────────────────────────

class RetestSceneDetail(BaseModel):
    """单场景重测信度详情 — 字段名与设计文档一致"""
    scene_id: int
    scene_name: str = ""
    retest_agreement_score: float = Field(..., description="加权一致性得分 [0,1]")
    retest_agreement_threshold: float = Field(..., description="一致性阈值")
    retest_hard_reject_threshold: float = Field(0.55, description="硬拒绝阈值")
    rejected: bool
    retest_matched_pairs: int = Field(..., description="原始与复评匹配的图对数")


class UserGroupSceneDetail(BaseModel):
    """用户组一致性 - 单场景详情"""
    scene_id: int
    scene_name: str = ""
    total_user_scenes: int = 0
    passed: int = 0
    rejected: int = 0


# ── 请求体 ────────────────────────────────────────────────────────────────────

class CleaningExecuteRequest(BaseModel):
    """执行数据清洗请求"""
    params: CleaningParams = Field(default_factory=CleaningParams)


# ── 响应体 ────────────────────────────────────────────────────────────────────

class CleaningStatusResponse(BaseModel):
    """清洗状态响应"""
    has_cleaned: bool = False
    last_cleaned_at: Optional[str] = None
    cleaned_record_count: int = 0
    current_record_count: int = 0
    new_record_count: int = 0
    needs_refresh: bool = False


class CleaningExecuteResponse(BaseModel):
    """清洗执行结果"""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    single_user_details: dict[str, Any] = Field(default_factory=dict)
    user_group_details: dict[str, Any] = Field(default_factory=dict)
    leaderboard_updated: bool = False


class ApiResponse(BaseModel):
    """统一响应包装"""
    code: int = 0
    message: str = "ok"
    data: Optional[Any] = None
