"""
数据清洗服务：第一层 + 第二层清洗
"""
import math
from collections import Counter
from sqlalchemy.orm import Session

from ..models.evaluation import Evaluation, EvalSession
from ..models.image_pair import ImagePair
from ..core.config import (
    CLEANING_ENTROPY_THRESHOLD,
    CLEANING_RETEST_THRESHOLD,
    CLEANING_AGREEMENT_THRESHOLD,
    CLEANING_MIN_VALID_USERS,
)

# 评分到方向的映射
SCORE_DIRECTION_MAP = {
    "a_much": "a_win",
    "a_slight": "a_win",
    "same": "tie",
    "b_slight": "b_win",
    "b_much": "b_win",
}


def get_score_direction(score: str) -> str:
    """将评分映射为方向"""
    return SCORE_DIRECTION_MAP.get(score, "unknown")


def calculate_entropy(scores: list[str]) -> float:
    """
    计算评分分布的信息熵 H = -Σ p_i * log2(p_i)

    Args:
        scores: 评分列表，如 ["a_much", "same", "b_slight", ...]

    Returns:
        信息熵值 (0 ~ log2(5)≈2.32)
    """
    counts = Counter(scores)
    total = len(scores)
    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


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
    pair_map: dict[int, list[Evaluation]] = {}
    for ev in evaluations:
        pair_map.setdefault(ev.pair_id, []).append(ev)

    results = []
    for pair_id, evals in pair_map.items():
        if len(evals) >= 2:
            evals_sorted = sorted(evals, key=lambda e: e.is_repeat)
            d1 = get_score_direction(evals_sorted[0].score)
            d2 = get_score_direction(evals_sorted[1].score)
            results.append(d1 == d2)

    if not results:
        return 1.0, True  # 无重复图对时，重测信度视为通过

    reliability = sum(results) / len(results)
    return reliability, reliability >= CLEANING_RETEST_THRESHOLD


def run_layer1_cleaning(db: Session, user_id: int, session_id: int) -> dict:
    """
    执行第一层清洗（submit-round 后自动调用）

    检查项：
    1. 熵检查：评分分布是否过于集中
    2. 重测信度：重复图对的一致率

    Args:
        db: 数据库会话
        user_id: 用户ID
        session_id: 会话ID

    Returns:
        清洗结果字典
    """
    # 获取 session
    session = db.query(EvalSession).filter(
        EvalSession.id == session_id,
        EvalSession.user_id == user_id,
    ).first()

    if not session:
        return {"success": False, "reason": "session not found"}

    # 获取该 session 的所有 submitted 评测
    evaluations = db.query(Evaluation).filter(
        Evaluation.user_id == user_id,
        Evaluation.session_id == session_id,
        Evaluation.status == "submitted",
    ).all()

    if not evaluations:
        return {"success": False, "reason": "no evaluations found"}

    scores = [ev.score for ev in evaluations]

    # 检查 1: 熵
    entropy = calculate_entropy(scores)
    if entropy == 0:
        # 全部选同一选项 → session invalid
        session.cleaning_status = "invalid"
        session.reject_reason = "评分无差异（熵=0）"
        session.entropy_weight = 0.0
        session.retest_weight = 0.0
        for ev in evaluations:
            ev.cleaning_status = "rejected"
            ev.reject_reason = "session无效：评分无差异"
        db.commit()
        return {
            "success": True,
            "session_status": "invalid",
            "reason": "评分无差异（熵=0）",
            "entropy": 0.0,
        }

    entropy_weight = min(1.0, entropy / CLEANING_ENTROPY_THRESHOLD)

    # 检查 2: 重测信度
    reliability, retest_passed = check_retest_reliability(evaluations)
    if not retest_passed:
        # 重测信度不足 → session invalid
        session.cleaning_status = "invalid"
        session.reject_reason = f"重测信度不足（{reliability:.2f} < {CLEANING_RETEST_THRESHOLD}）"
        session.entropy_weight = entropy_weight
        session.retest_weight = reliability
        for ev in evaluations:
            ev.cleaning_status = "rejected"
            ev.reject_reason = "session无效：重测信度不足"
        db.commit()
        return {
            "success": True,
            "session_status": "invalid",
            "reason": f"重测信度不足（{reliability:.2f} < {CLEANING_RETEST_THRESHOLD}）",
            "entropy": entropy,
            "reliability": reliability,
        }

    # 通过 → session valid
    session.cleaning_status = "valid"
    session.reject_reason = ""
    session.entropy_weight = entropy_weight
    session.retest_weight = reliability

    # Evaluation 保持 pending（等第二层）
    for ev in evaluations:
        ev.cleaning_status = "pending"

    db.commit()

    return {
        "success": True,
        "session_status": "valid",
        "entropy": entropy,
        "entropy_weight": entropy_weight,
        "reliability": reliability,
    }


def calculate_user_agreement(
    target_user_id: int,
    pair_evaluations: dict[int, list[tuple[int, str]]],
) -> float:
    """
    计算目标用户与群体共识的一致率 (Leave-One-Out)

    Args:
        target_user_id: 目标用户ID
        pair_evaluations: {pair_id: [(user_id, score), ...]}

    Returns:
        一致率 (0-1)
    """
    agree_count = 0
    total_count = 0

    for pair_id, evals in pair_evaluations.items():
        target_score = None
        other_directions = []

        for user_id, score in evals:
            if user_id == target_user_id:
                target_score = score
            else:
                other_directions.append(get_score_direction(score))

        if target_score is None or not other_directions:
            continue

        # 群体共识（投票）
        vote = Counter(other_directions)
        consensus = vote.most_common(1)[0][0]

        target_direction = get_score_direction(target_score)
        if target_direction == consensus:
            agree_count += 1
        total_count += 1

    return agree_count / total_count if total_count > 0 else 0.0


def run_layer2_cleaning(db: Session) -> dict:
    """
    执行第二层清洗（管理员手动触发）

    1. 找出所有 valid session 的用户
    2. 计算每个用户的群体一致率
    3. 一致率 < 0.5 → 标记为 rejected
    4. 一致率 >= 0.5 → 回写 agreement_weight

    Returns:
        清洗结果字典
    """
    # 找出所有 valid session
    valid_sessions = db.query(EvalSession).filter(
        EvalSession.cleaning_status == "valid"
    ).all()

    if not valid_sessions:
        return {"success": True, "reason": "no valid sessions", "results": []}

    # 收集所有 valid session 的用户
    user_ids = list(set(s.user_id for s in valid_sessions))

    if len(user_ids) < CLEANING_MIN_VALID_USERS:
        # 用户数不足，跳过第二层
        return {
            "success": True,
            "reason": f"有效用户数不足（{len(user_ids)} < {CLEANING_MIN_VALID_USERS}）",
            "skipped": True,
            "user_count": len(user_ids),
        }

    # 收集所有 valid session 中的 submitted 评测
    valid_session_ids = [s.id for s in valid_sessions]
    all_evaluations = db.query(Evaluation).filter(
        Evaluation.session_id.in_(valid_session_ids),
        Evaluation.status == "submitted",
        Evaluation.is_repeat == 0,  # 排除重复图对
    ).all()

    # 按 pair_id 构建评测矩阵
    pair_evaluations: dict[int, list[tuple[int, str]]] = {}
    for ev in all_evaluations:
        pair_evaluations.setdefault(ev.pair_id, []).append((ev.user_id, ev.score))

    # 计算每个用户的一致率
    user_agreements: dict[int, float] = {}
    for uid in user_ids:
        agreement = calculate_user_agreement(uid, pair_evaluations)
        user_agreements[uid] = agreement

    # 处理结果
    results = []
    for uid, agreement in user_agreements.items():
        if agreement < CLEANING_AGREEMENT_THRESHOLD:
            # 一致率不足 → 该用户所有 valid session 标记 invalid
            user_sessions = [s for s in valid_sessions if s.user_id == uid]
            for s in user_sessions:
                s.cleaning_status = "invalid"
                s.reject_reason = f"群体一致率不足（{agreement:.2f} < {CLEANING_AGREEMENT_THRESHOLD}）"
                # 该 session 的所有 Evaluation 标记 rejected
                session_evals = [ev for ev in all_evaluations if ev.session_id == s.id]
                for ev in session_evals:
                    ev.cleaning_status = "rejected"
                    ev.reject_reason = "用户群体一致率不足"
            results.append({
                "user_id": uid,
                "agreement": agreement,
                "status": "invalid",
                "reason": f"群体一致率不足（{agreement:.2f} < {CLEANING_AGREEMENT_THRESHOLD}）",
            })
        else:
            # 通过 → 回写权重
            user_evals = [ev for ev in all_evaluations if ev.user_id == uid]
            for ev in user_evals:
                session = next((s for s in valid_sessions if s.id == ev.session_id), None)
                if session:
                    ev.user_weight = session.retest_weight * session.entropy_weight * agreement
                    ev.cleaning_status = "valid"
            results.append({
                "user_id": uid,
                "agreement": agreement,
                "status": "valid",
            })

    db.commit()

    return {
        "success": True,
        "user_count": len(user_ids),
        "results": results,
    }
