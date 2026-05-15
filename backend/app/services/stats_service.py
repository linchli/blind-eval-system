"""
统计服务
"""
import math
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.evaluation import Evaluation, EvalSession
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.scene import Scene
from ..models.device_model import DeviceModel
from ..models.user import User
from ..core.config import SCORE_MAP, CORRELATION_THRESHOLD, MAX_DISCARD_THRESHOLD


def get_overview(db: Session) -> dict:
    """获取系统概览统计"""
    return {
        "scene_count": db.query(Scene).count(),
        "model_count": db.query(DeviceModel).count(),
        "image_count": db.query(Image).count(),
        "pair_count": db.query(ImagePair).count(),
        "eval_count": db.query(Evaluation).filter(Evaluation.status == "submitted").count(),
        "user_count": db.query(User).count(),
    }


def get_scene_stats(db: Session, scene_id: int) -> dict:
    """获取指定场景的统计信息"""
    image_count = db.query(Image).filter(Image.scene_id == scene_id).count()
    pair_count = db.query(ImagePair).filter(ImagePair.scene_id == scene_id).count()
    return {
        "image_count": image_count,
        "pair_count": pair_count,
    }


def compute_cleaning(db: Session, scene_id: int = None) -> dict:
    """数据清洗与排行"""
    query = db.query(Evaluation).filter(Evaluation.status == "submitted")
    if scene_id:
        pair_ids = [p.id for p in db.query(ImagePair).filter(ImagePair.scene_id == scene_id).all()]
        query = query.filter(Evaluation.pair_id.in_(pair_ids))

    evaluations = query.all()
    if not evaluations:
        return {"user_consistency": [], "group_discarded_users": [], "final_valid_users": 0, "model_ranking": []}

    # 按用户分组
    user_evals = {}
    for e in evaluations:
        user_evals.setdefault(e.user_id, [])
        user_evals[e.user_id].append(e)

    # 计算用户一致性
    consistency = []
    for uid, evals in user_evals.items():
        user = db.query(User).filter(User.id == uid).first()
        if len(evals) < 3:
            consistency.append({
                "user_id": uid, "username": user.username if user else "",
                "correlation": 0.0, "is_valid": False, "reason": "评分数量不足"
            })
            continue
        # 简化：用评分方差近似一致性
        scores = []
        for ev in evals:
            s = SCORE_MAP.get(ev.score, {})
            diff = abs(s.get("score_a", 0) - s.get("score_b", 0))
            scores.append(diff)
        mean = sum(scores) / len(scores)
        var = sum((s - mean) ** 2 for s in scores) / len(scores)
        std = math.sqrt(var)
        corr = max(0, 1 - std)
        is_valid = corr >= CORRELATION_THRESHOLD
        consistency.append({
            "user_id": uid, "username": user.username if user else "",
            "correlation": round(corr, 3), "is_valid": is_valid,
            "reason": "" if is_valid else "一致性过低"
        })

    valid_users = [c for c in consistency if c["is_valid"]]
    discarded = [c for c in consistency if not c["is_valid"]]

    # 机型排行（基于有效用户）
    valid_uids = {c["user_id"] for c in valid_users}
    valid_evals = [e for e in evaluations if e.user_id in valid_uids]

    model_scores = {}
    for ev in valid_evals:
        pair = db.query(ImagePair).filter(ImagePair.id == ev.pair_id).first()
        if not pair:
            continue
        img_a = db.query(Image).filter(Image.id == pair.image_a_id).first()
        img_b = db.query(Image).filter(Image.id == pair.image_b_id).first()
        if not img_a or not img_b:
            continue
        # A 侧
        model_scores.setdefault(img_a.model_id, []).append(ev.score_a)
        # B 侧
        model_scores.setdefault(img_b.model_id, []).append(ev.score_b)

    ranking = []
    for mid, scores in model_scores.items():
        m = db.query(DeviceModel).filter(DeviceModel.id == mid).first()
        sorted_scores = sorted(scores)
        median = sorted_scores[len(sorted_scores) // 2]
        ranking.append({
            "model_id": mid, "model_name": m.name if m else "",
            "median_score": round(median, 3), "eval_count": len(scores), "rank": 0
        })

    ranking.sort(key=lambda x: x["median_score"], reverse=True)
    for i, r in enumerate(ranking):
        r["rank"] = i + 1

    return {
        "user_consistency": consistency,
        "group_discarded_users": discarded,
        "final_valid_users": len(valid_users),
        "model_ranking": ranking,
    }
