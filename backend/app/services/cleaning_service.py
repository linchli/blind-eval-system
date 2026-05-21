"""
数据清洗服务：重测信度计算
"""
from sqlalchemy.orm import Session
from ..models.evaluation import Evaluation
from ..schemas.cleaning import RepeatPairResult, RetestReliabilityResponse


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


def calculate_retest_reliability(
    db: Session,
    user_id: int,
    session_id: int
) -> RetestReliabilityResponse:
    """
    计算重测信度

    Args:
        db: 数据库会话
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        重测信度计算结果
    """
    # 查找该 session 中所有已提交的评测记录
    evaluations = db.query(Evaluation).filter(
        Evaluation.user_id == user_id,
        Evaluation.session_id == session_id,
        Evaluation.status == "submitted"
    ).all()

    # 按 pair_id 分组
    pair_evaluations = {}
    for eval in evaluations:
        if eval.pair_id not in pair_evaluations:
            pair_evaluations[eval.pair_id] = []
        pair_evaluations[eval.pair_id].append(eval)

    # 找出有重复评测的图对（同一 pair_id 有多条记录）
    repeat_pairs = []
    for pair_id, evals in pair_evaluations.items():
        if len(evals) >= 2:
            # 按 is_repeat 排序，0 在前，1 在后
            evals_sorted = sorted(evals, key=lambda e: e.is_repeat)
            first_eval = evals_sorted[0]
            second_eval = evals_sorted[1]

            first_direction = get_score_direction(first_eval.score)
            second_direction = get_score_direction(second_eval.score)
            consistent = (first_direction == second_direction)

            repeat_pairs.append(RepeatPairResult(
                pair_id=pair_id,
                first_score=first_eval.score,
                second_score=second_eval.score,
                first_direction=first_direction,
                second_direction=second_direction,
                consistent=consistent,
            ))

    # 计算一致率
    total_repeat = len(repeat_pairs)
    consistent_count = sum(1 for rp in repeat_pairs if rp.consistent)
    reliability = consistent_count / total_repeat if total_repeat > 0 else 0.0
    passed = reliability >= RETEST_THRESHOLD

    # 生成拒绝原因
    reject_reason = None
    if not passed:
        if total_repeat == 0:
            reject_reason = "无重复图对数据"
        else:
            reject_reason = f"重测信度不足（{reliability:.2f} < {RETEST_THRESHOLD}）"

    return RetestReliabilityResponse(
        session_id=session_id,
        user_id=user_id,
        repeat_pairs=repeat_pairs,
        total_repeat=total_repeat,
        consistent_count=consistent_count,
        reliability=reliability,
        passed=passed,
        reject_reason=reject_reason,
    )
