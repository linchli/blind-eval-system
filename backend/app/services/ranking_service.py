"""
排行榜服务：第四层 Bradley-Terry 排名 + 流程编排
"""
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.evaluation import Evaluation, EvalSession
from ..models.image_pair import ImagePair
from ..models.device_model import DeviceModel
from ..models.ranking import RankingResult
from ..services.cleaning_service import run_layer2_cleaning
from ..services.consensus_service import extract_all_consensus


def bradley_terry_solve(
    devices: list[int],
    wins: dict[int, dict[int, float]],
    comparisons: dict[int, dict[int, int]],
    max_iter: int = 1000,
    tol: float = 1e-6,
) -> dict[int, float]:
    """
    Bradley-Terry MM 算法求解

    Args:
        devices: 设备ID列表
        wins: wins[i][j] = 设备i对设备j的加权胜场
        comparisons: comparisons[i][j] = 设备i与设备j的比较次数
        max_iter: 最大迭代次数
        tol: 收敛阈值

    Returns:
        {device_id: pi_k} 各设备的实力参数
    """
    K = len(devices)
    if K == 0:
        return {}
    if K == 1:
        return {devices[0]: 1.0}

    pi = {d: 1.0 / K for d in devices}

    for _ in range(max_iter):
        pi_new = {}
        for k in devices:
            W_k = sum(wins.get(k, {}).get(j, 0) for j in devices if j != k)
            denom = sum(
                comparisons.get(k, {}).get(j, 0) / (pi[k] + pi[j])
                for j in devices if j != k and (pi[k] + pi[j]) > 0
            )
            pi_new[k] = W_k / denom if denom > 0 else 0

        # 归一化
        total = sum(pi_new.values())
        if total > 0:
            pi_new = {k: v / total for k, v in pi_new.items()}

        # 检查收敛
        max_diff = max(abs(pi_new[k] - pi[k]) for k in devices)
        if max_diff < tol:
            return pi_new

        pi = pi_new

    return pi


def normalize_to_100(pi_values: dict[int, float]) -> dict[int, float]:
    """
    将 BT 参数转换为 0-100 分，最低分保底 60

    Args:
        pi_values: {device_id: pi_k}

    Returns:
        {device_id: score} score 范围 60-100
    """
    if not pi_values:
        return {}

    pi_max = max(pi_values.values())
    pi_min = min(pi_values.values())

    if pi_max == pi_min:
        return {did: 80.0 for did in pi_values}

    return {
        did: 60 + (pi - pi_min) / (pi_max - pi_min) * 40
        for did, pi in pi_values.items()
    }


def calculate_confidence(eval_count: int) -> tuple[float, float]:
    """
    计算置信区间偏移

    Args:
        eval_count: 参与评测的图对数

    Returns:
        (confidence_min_offset, confidence_max_offset)
    """
    factor = min(eval_count / 20, 1.0)
    margin = (1 - factor) * 10
    return -margin, margin


def build_win_matrix(
    consensus_results: list[dict],
) -> tuple[dict[int, dict[int, float]], dict[int, dict[int, int]], dict[int, int]]:
    """
    从共识结果构建胜负矩阵

    Args:
        consensus_results: 第三层输出的共识结果列表

    Returns:
        (wins, comparisons, device_eval_counts)
    """
    wins: dict[int, dict[int, float]] = {}
    comparisons: dict[int, dict[int, int]] = {}
    device_eval_counts: dict[int, int] = {}

    for c in consensus_results:
        device_a = c["device_a"]
        device_b = c["device_b"]
        strength = c["strength"]

        # 初始化
        wins.setdefault(device_a, {})
        wins.setdefault(device_b, {})
        comparisons.setdefault(device_a, {})
        comparisons.setdefault(device_b, {})

        if c["is_tie"]:
            # 平局：双方各加 0.5 * strength
            wins[device_a][device_b] = wins[device_a].get(device_b, 0) + 0.5 * strength
            wins[device_b][device_a] = wins[device_b].get(device_a, 0) + 0.5 * strength
        else:
            winner = c["winner"]
            loser = c["loser"]
            wins[winner][loser] = wins[winner].get(loser, 0) + strength

        comparisons[device_a][device_b] = comparisons[device_a].get(device_b, 0) + 1
        comparisons[device_b][device_a] = comparisons[device_b].get(device_a, 0) + 1

        device_eval_counts[device_a] = device_eval_counts.get(device_a, 0) + 1
        device_eval_counts[device_b] = device_eval_counts.get(device_b, 0) + 1

    return wins, comparisons, device_eval_counts


def save_ranking_results(
    db: Session,
    scores: dict[int, float],
    device_eval_counts: dict[int, int],
    scene_id: int | None = None,
) -> list[RankingResult]:
    """
    保存排名结果到数据库

    Args:
        db: 数据库会话
        scores: {device_id: score} 0-100 分
        device_eval_counts: {device_id: eval_count}
        scene_id: 场景ID，None 表示综合排名

    Returns:
        保存的 RankingResult 列表
    """
    # 删除旧的同类型排名
    if scene_id:
        db.query(RankingResult).filter(RankingResult.scene_id == scene_id).delete()
    else:
        db.query(RankingResult).filter(RankingResult.scene_id.is_(None)).delete()

    # 按分数排序
    sorted_devices = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    results = []
    for rank, (device_id, score) in enumerate(sorted_devices, 1):
        eval_count = device_eval_counts.get(device_id, 0)
        conf_min, conf_max = calculate_confidence(eval_count)

        result = RankingResult(
            device_id=device_id,
            scene_id=scene_id,
            score=round(score, 2),
            rank=rank,
            confidence_min=round(conf_min, 2),
            confidence_max=round(conf_max, 2),
            eval_count=eval_count,
        )
        db.add(result)
        results.append(result)

    db.commit()
    return results


def run_full_pipeline(db: Session, scene_id: int | None = None) -> dict:
    """
    执行完整清洗 + 排名流程（管理员手动触发）

    流程：第二层清洗 → 第三层共识 → 第四层排名

    Args:
        db: 数据库会话
        scene_id: 场景ID，None 表示综合排名

    Returns:
        流程执行结果
    """
    # Step 1: 第二层清洗
    layer2_result = run_layer2_cleaning(db)

    # Step 2: 获取所有 valid 评测
    valid_evaluations = db.query(Evaluation).filter(
        Evaluation.cleaning_status == "valid"
    ).all()

    if not valid_evaluations:
        return {
            "success": True,
            "reason": "no valid evaluations after cleaning",
            "layer2": layer2_result,
        }

    # 如果指定了场景，过滤图对
    if scene_id:
        scene_pair_ids = {
            p.id for p in db.query(ImagePair).filter(ImagePair.scene_id == scene_id).all()
        }
        valid_evaluations = [ev for ev in valid_evaluations if ev.pair_id in scene_pair_ids]

    if not valid_evaluations:
        return {
            "success": True,
            "reason": "no valid evaluations for this scene",
            "layer2": layer2_result,
        }

    # Step 3: 构建用户权重映射
    user_weights: dict[int, float] = {}
    for ev in valid_evaluations:
        user_weights[ev.user_id] = ev.user_weight

    # Step 4: 第三层共识提取
    consensus_results = extract_all_consensus(db, valid_evaluations, user_weights)

    # Step 5: 构建胜负矩阵
    wins, comparisons, device_eval_counts = build_win_matrix(consensus_results)

    # Step 6: Bradley-Terry 求解
    devices = list(device_eval_counts.keys())
    pi_values = bradley_terry_solve(devices, wins, comparisons)

    # Step 7: 归一化到 0-100
    scores = normalize_to_100(pi_values)

    # Step 8: 保存排名结果
    ranking_results = save_ranking_results(db, scores, device_eval_counts, scene_id)

    return {
        "success": True,
        "layer2": layer2_result,
        "consensus_count": len(consensus_results),
        "device_count": len(scores),
        "ranking_saved": len(ranking_results),
    }
