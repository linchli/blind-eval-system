"""
统计与分析路由
"""
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..core.config import CORRELATION_THRESHOLD, MAX_DISCARD_THRESHOLD
from ..models.user import User
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.device_model import DeviceModel
from ..models.evaluation import Evaluation
from ..schemas.eval import (
    StatsOverview, ScoreCount, UserConsistency,
    ModelScore, CleaningResult,
)

router = APIRouter(prefix="/api/stats", tags=["统计分析"])


@router.get("/overview", response_model=StatsOverview)
async def stats_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    total_evals = db.query(Evaluation).filter(Evaluation.status == "submitted").count()
    total_users = db.query(User).filter(User.role == "evaluator").count()
    total_pairs = db.query(ImagePair).count()

    counts = {"a_much": 0, "a_slight": 0, "same": 0, "b_slight": 0, "b_much": 0}
    for e in db.query(Evaluation).filter(Evaluation.status == "submitted").all():
        if e.score in counts:
            counts[e.score] += 1

    return StatsOverview(
        total_evaluations=total_evals,
        total_users=total_users,
        total_pairs=total_pairs,
        score_counts=ScoreCount(**counts),
    )


@router.get("/cleaning", response_model=CleaningResult)
async def data_cleaning(
    scene_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    evaluators = db.query(User).filter(User.role == "evaluator").all()
    if not evaluators:
        return CleaningResult(
            user_consistency=[], group_discarded_users=[],
            final_valid_users=0, model_ranking=[]
        )

    # 构建用户评分矩阵
    user_scores = {}
    pair_ids = set()

    for ev in db.query(Evaluation).filter(Evaluation.status == "submitted").all():
        if scene_id:
            pair = db.query(ImagePair).filter(ImagePair.id == ev.pair_id).first()
            if pair and pair.scene_id != scene_id:
                continue
        user_scores.setdefault(ev.user_id, {})[ev.pair_id] = ev.score_a
        pair_ids.add(ev.pair_id)

    pair_list = sorted(pair_ids)

    # 步骤 1：单用户一致性验证
    user_consistency = []
    for user in evaluators:
        scores = user_scores.get(user.id, {})
        if len(scores) < 2:
            user_consistency.append(UserConsistency(
                user_id=user.id, username=user.username,
                correlation=0.0, is_valid=False,
                reason="评价数量不足（<2）"
            ))
            continue

        vec = [scores.get(pid, 0) for pid in pair_list]
        if np.std(vec) == 0:
            user_consistency.append(UserConsistency(
                user_id=user.id, username=user.username,
                correlation=0.0, is_valid=False,
                reason="评分无差异（标准差为0）"
            ))
            continue

        correlations = []
        for other_user in evaluators:
            if other_user.id == user.id:
                continue
            other_scores = user_scores.get(other_user.id, {})
            other_vec = [other_scores.get(pid, 0) for pid in pair_list]

            common = [(v, o) for v, o in zip(vec, other_vec) if (v != 0 or o != 0)]
            if len(common) < 2:
                continue

            v_arr = np.array([c[0] for c in common], dtype=float)
            o_arr = np.array([c[1] for c in common], dtype=float)

            if np.std(v_arr) == 0 or np.std(o_arr) == 0:
                continue

            corr = np.corrcoef(v_arr, o_arr)[0, 1]
            if not np.isnan(corr):
                correlations.append(corr)

        avg_corr = float(np.mean(correlations)) if correlations else 0.0
        is_valid = avg_corr >= CORRELATION_THRESHOLD
        reason = "" if is_valid else f"平均相关性 {avg_corr:.3f} < 阈值 {CORRELATION_THRESHOLD}"

        user_consistency.append(UserConsistency(
            user_id=user.id, username=user.username,
            correlation=round(avg_corr, 4),
            is_valid=is_valid, reason=reason,
        ))

    # 步骤 2：组内一致性验证
    valid_users = [uc for uc in user_consistency if uc.is_valid]
    all_correlations = [uc.correlation for uc in valid_users if uc.correlation > 0]

    if all_correlations:
        mean_corr = np.mean(all_correlations)
        std_corr = np.std(all_correlations)
        discard_threshold = mean_corr - std_corr
        discard_threshold = min(discard_threshold, MAX_DISCARD_THRESHOLD)
    else:
        discard_threshold = MAX_DISCARD_THRESHOLD

    group_discarded = [
        uc for uc in valid_users if 0 < uc.correlation < discard_threshold
    ]
    for uc in group_discarded:
        uc.reason = f"组内相关性 {uc.correlation:.3f} < 舍弃门限 {discard_threshold:.3f}"
        uc.is_valid = False

    final_valid = [uc for uc in user_consistency if uc.is_valid]
    final_valid_ids = {uc.user_id for uc in final_valid}

    # 步骤 3：清洗后计算机型得分
    model_scores_map = {}

    for ev in db.query(Evaluation).filter(Evaluation.status == "submitted").all():
        if ev.user_id not in final_valid_ids:
            continue
        if scene_id:
            pair = db.query(ImagePair).filter(ImagePair.id == ev.pair_id).first()
            if pair and pair.scene_id != scene_id:
                continue

        pair = db.query(ImagePair).filter(ImagePair.id == ev.pair_id).first()
        if not pair:
            continue

        # 通过 Image 获取 model_id
        img_a = db.query(Image).filter(Image.id == pair.image_a_id).first()
        img_b = db.query(Image).filter(Image.id == pair.image_b_id).first()
        if not img_a or not img_b:
            continue

        model_scores_map.setdefault(img_a.model_id, []).append(ev.score_a)
        model_scores_map.setdefault(img_b.model_id, []).append(ev.score_b)

    # 步骤 4：排行榜
    ranking = []
    for model_id, scores in model_scores_map.items():
        m = db.query(DeviceModel).filter(DeviceModel.id == model_id).first()
        median = float(np.median(scores)) if scores else 0
        ranking.append(ModelScore(
            model_id=model_id,
            model_name=m.name if m else f"Model-{model_id}",
            median_score=round(median, 4),
            eval_count=len(scores),
        ))

    ranking.sort(key=lambda x: x.median_score, reverse=True)
    for i, r in enumerate(ranking, 1):
        r.rank = i

    return CleaningResult(
        user_consistency=user_consistency,
        group_discarded_users=group_discarded,
        final_valid_users=len(final_valid),
        model_ranking=ranking,
    )


@router.get("/ranking", response_model=list[ModelScore])
async def get_ranking(
    scene_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    model_scores_map = {}
    for ev in db.query(Evaluation).filter(Evaluation.status == "submitted").all():
        if scene_id:
            pair = db.query(ImagePair).filter(ImagePair.id == ev.pair_id).first()
            if pair and pair.scene_id != scene_id:
                continue
        pair = db.query(ImagePair).filter(ImagePair.id == ev.pair_id).first()
        if not pair:
            continue

        img_a = db.query(Image).filter(Image.id == pair.image_a_id).first()
        img_b = db.query(Image).filter(Image.id == pair.image_b_id).first()
        if not img_a or not img_b:
            continue

        model_scores_map.setdefault(img_a.model_id, []).append(ev.score_a)
        model_scores_map.setdefault(img_b.model_id, []).append(ev.score_b)

    ranking = []
    for model_id, scores in model_scores_map.items():
        m = db.query(DeviceModel).filter(DeviceModel.id == model_id).first()
        median = float(np.median(scores)) if scores else 0
        ranking.append(ModelScore(
            model_id=model_id,
            model_name=m.name if m else f"Model-{model_id}",
            median_score=round(median, 4),
            eval_count=len(scores),
        ))

    ranking.sort(key=lambda x: x.median_score, reverse=True)
    for i, r in enumerate(ranking, 1):
        r.rank = i
    return ranking
