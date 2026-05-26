"""
图对共识提取服务：第三层清洗
"""
from sqlalchemy.orm import Session

from ..models.evaluation import Evaluation
from ..models.image_pair import ImagePair


def get_device_winner(pair: ImagePair, score: str) -> tuple[int, int, str]:
    """
    根据评分判断设备胜负

    Args:
        pair: 图对对象
        score: 评分字符串

    Returns:
        (winner_device_id, loser_device_id, result_type)
        result_type: "win" 或 "tie"
    """
    device_a = pair.image_a.device_id
    device_b = pair.image_b.device_id

    if score in ("a_much", "a_slight"):
        return device_a, device_b, "win"
    elif score in ("b_much", "b_slight"):
        return device_b, device_a, "win"
    else:  # same
        return device_a, device_b, "tie"


def extract_pair_consensus(
    pair: ImagePair,
    evaluations: list[Evaluation],
    user_weights: dict[int, float],
) -> dict:
    """
    对单个图对进行加权投票

    Args:
        pair: 图对对象
        evaluations: 该图对的有效评测记录
        user_weights: {user_id: final_weight}

    Returns:
        共识结果字典
    """
    device_a_id = pair.image_a.device_id
    device_b_id = pair.image_b.device_id

    a_score = 0.0
    b_score = 0.0

    for ev in evaluations:
        weight = user_weights.get(ev.user_id, 1.0)
        if ev.score in ("a_much", "a_slight"):
            a_score += weight
        elif ev.score in ("b_much", "b_slight"):
            b_score += weight
        else:  # same
            a_score += weight * 0.5
            b_score += weight * 0.5

    total = a_score + b_score
    if total == 0:
        return {
            "pair_id": pair.id,
            "device_a": device_a_id,
            "device_b": device_b_id,
            "winner": None,
            "loser": None,
            "strength": 0.0,
            "is_tie": True,
        }

    strength = abs(a_score - b_score) / total

    if a_score > b_score:
        return {
            "pair_id": pair.id,
            "device_a": device_a_id,
            "device_b": device_b_id,
            "winner": device_a_id,
            "loser": device_b_id,
            "strength": strength,
            "is_tie": False,
        }
    elif b_score > a_score:
        return {
            "pair_id": pair.id,
            "device_a": device_a_id,
            "device_b": device_b_id,
            "winner": device_b_id,
            "loser": device_a_id,
            "strength": strength,
            "is_tie": False,
        }
    else:
        return {
            "pair_id": pair.id,
            "device_a": device_a_id,
            "device_b": device_b_id,
            "winner": None,
            "loser": None,
            "strength": 0.0,
            "is_tie": True,
        }


def extract_all_consensus(
    db: Session,
    valid_evaluations: list[Evaluation],
    user_weights: dict[int, float],
) -> list[dict]:
    """
    批量提取所有图对的共识

    Args:
        db: 数据库会话
        valid_evaluations: 所有有效评测记录
        user_weights: {user_id: final_weight}

    Returns:
        共识结果列表
    """
    # 按 pair_id 分组
    pair_eval_map: dict[int, list[Evaluation]] = {}
    for ev in valid_evaluations:
        pair_eval_map.setdefault(ev.pair_id, []).append(ev)

    # 获取所有涉及的图对
    pair_ids = list(pair_eval_map.keys())
    pairs = db.query(ImagePair).filter(ImagePair.id.in_(pair_ids)).all()
    pair_map = {p.id: p for p in pairs}

    results = []
    for pair_id, evals in pair_eval_map.items():
        pair = pair_map.get(pair_id)
        if not pair:
            continue
        consensus = extract_pair_consensus(pair, evals, user_weights)
        results.append(consensus)

    return results
