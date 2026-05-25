"""
数据清洗服务
"""
from sqlalchemy.orm import Session
from ..models.evaluation import Evaluation


# 评分到方向的映射
SCORE_DIRECTION_MAP = {
    "a_much": "a_win",
    "a_slight": "a_win",
    "same": "tie",
    "b_slight": "b_win",
    "b_much": "b_win",
}

# 重测信度阈值
RETEST_THRESHOLD = 0.6


def get_score_direction(score: str) -> str:
    """将评分映射为方向"""
    return SCORE_DIRECTION_MAP.get(score, "unknown")


def check_retest_reliability(evaluations: list[Evaluation]) -> tuple[float, bool]:
    """
    计算重测信度一致率

    找出同一 pair_id 的两条记录（is_repeat=0 和 is_repeat=1）
    比较方向是否一致

    Args:
        evaluations: 一个 session 内的所有评测记录

    Returns:
        (reliability, passed): 一致率和是否通过阈值
    """