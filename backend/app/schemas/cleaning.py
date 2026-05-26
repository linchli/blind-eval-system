"""
数据清洗相关 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class RepeatPairResult(BaseModel):
    """单个重复图对的比较结果"""
    pair_id: int
    first_score: str
    second_score: str
    first_direction: str
    second_direction: str
    consistent: bool


class RetestReliabilityResponse(BaseModel):
    """重测信度计算响应"""
    session_id: int
    user_id: int
    repeat_pairs: list[RepeatPairResult]
    total_repeat: int
    consistent_count: int
    reliability: float
    passed: bool
    reject_reason: Optional[str] = None


class RetestReliabilityRequest(BaseModel):
    """重测信度计算请求"""
    session_id: int


class DeviceRankingItem(BaseModel):
    """排行榜单项"""
    model_config = ConfigDict(protected_namespaces=())

    device_id: int
    device_name: str
    main_chip: str = ""
    sensor_model: str = ""
    score: float
    rank: int
    confidence_min: float
    confidence_max: float
    eval_count: int


class RankingListResponse(BaseModel):
    """排行榜列表响应"""
    items: list[DeviceRankingItem]
    scene_id: int | None = None
    total_devices: int


class CleaningReportItem(BaseModel):
    """清洗报告单项"""
    user_id: int
    username: str
    session_id: int
    session_status: str
    retest_weight: float
    entropy_weight: float
    reject_reason: str = ""


class UserAgreementItem(BaseModel):
    """用户一致率单项"""
    user_id: int
    username: str
    agreement: float
    status: str  # "valid" | "invalid"


class CleaningReportResponse(BaseModel):
    """清洗报告响应"""
    total_sessions: int
    valid_sessions: int
    invalid_sessions: int
    pending_sessions: int
    details: list[CleaningReportItem]
    user_agreements: list[UserAgreementItem] = []


class PipelineRunResponse(BaseModel):
    """清洗流程执行响应"""
    success: bool
    reason: str = ""
    consensus_count: int = 0
    device_count: int = 0
    ranking_saved: int = 0
    layer2: dict = {}


class SessionPairDetail(BaseModel):
    pair_id: int
    device_a_name: str
    device_b_name: str
    score: str
    direction: str  # "A 胜", "B 胜", "平局"


class SessionDetailResponse(BaseModel):
    session_id: int
    user_id: int
    username: str
    cleaning_status: str
    retest_weight: float
    entropy_weight: float
    reject_reason: str
    pairs: list[SessionPairDetail]


class DeviceWinRate(BaseModel):
    opponent_id: int
    opponent_name: str
    win_count: int
    lose_count: int
    win_rate: float


class DeviceWinRateResponse(BaseModel):
    device_id: int
    device_name: str
    win_rates: list[DeviceWinRate]
    scene_rankings: list[dict]


class SceneCompareItem(BaseModel):
    device_id: int
    device_name: str
    scores: dict[str, float]  # scene_name -> score
    average_score: float


class SceneCompareResponse(BaseModel):
    scenes: list[str]
    items: list[SceneCompareItem]
