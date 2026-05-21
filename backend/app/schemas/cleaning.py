"""
数据清洗相关 Pydantic 模型
"""
from pydantic import BaseModel
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
