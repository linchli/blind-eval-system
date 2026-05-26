"""
排行榜与清洗 API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from ..core.database import get_db
from ..core.dependencies import require_admin, get_current_user, get_optional_user
from ..models.user import User
from ..models.evaluation import Evaluation, EvalSession
from ..models.device_model import DeviceModel
from ..models.image_pair import ImagePair
from ..models.ranking import RankingResult
from ..models.image import Image
from ..models.scene import Scene
from ..schemas.cleaning import (
    DeviceRankingItem,
    RankingListResponse,
    CleaningReportResponse,
    CleaningReportItem,
    UserAgreementItem,
    PipelineRunResponse,
    SessionDetailResponse,
    SessionPairDetail,
    DeviceWinRateResponse,
    DeviceWinRate,
    SceneCompareResponse,
    SceneCompareItem,
)
from ..services.ranking_service import run_full_pipeline
from ..services.cleaning_service import run_layer1_cleaning, calculate_user_agreement
from ..core.config import CLEANING_AGREEMENT_THRESHOLD

router = APIRouter(prefix="/api/ranking", tags=["排行榜"])

DIRECTION_MAP = {
    "a_much": "A 胜", "a_slight": "A 胜",
    "same": "平局",
    "b_slight": "B 胜", "b_much": "B 胜",
}


@router.post("/clean-layer1", response_model=dict)
async def clean_layer1(
    session_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """对指定 session 执行第一层清洗（通常由 submit-round 自动调用）"""
    result = run_layer1_cleaning(db, current_user.id, session_id)
    return result


@router.post("/clean-layer2", response_model=PipelineRunResponse)
async def clean_layer2(
    scene_id: int = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """执行完整清洗 + 排名流程（第二层+第三层+第四层）"""
    result = run_full_pipeline(db, scene_id)
    return PipelineRunResponse(**result)


@router.get("/list", response_model=RankingListResponse)
async def get_ranking(
    scene_id: int = None,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """获取排行榜（无需登录）"""
    query = db.query(RankingResult)
    if scene_id:
        query = query.filter(RankingResult.scene_id == scene_id)
    else:
        query = query.filter(RankingResult.scene_id.is_(None))

    results = query.order_by(RankingResult.rank).all()

    items = []
    for r in results:
        device = db.query(DeviceModel).filter(DeviceModel.id == r.device_id).first()
        items.append(DeviceRankingItem(
            device_id=r.device_id,
            device_name=device.name if device else f"Device-{r.device_id}",
            main_chip=device.main_chip if device else "",
            sensor_model=device.sensor_model if device else "",
            score=r.score,
            rank=r.rank,
            confidence_min=r.confidence_min,
            confidence_max=r.confidence_max,
            eval_count=r.eval_count,
        ))

    return RankingListResponse(
        items=items,
        scene_id=scene_id,
        total_devices=len(items),
    )


@router.get("/device/{device_id}", response_model=list[DeviceRankingItem])
async def get_device_ranking(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单设备在各场景的排名"""
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    results = db.query(RankingResult).filter(
        RankingResult.device_id == device_id
    ).all()

    items = []
    for r in results:
        scene_name = ""
        if r.scene_id:
            scene = db.query(Scene).filter(Scene.id == r.scene_id).first()
            scene_name = scene.name if scene else ""
        items.append(DeviceRankingItem(
            device_id=r.device_id,
            device_name=device.name,
            main_chip=device.main_chip,
            sensor_model=device.sensor_model,
            score=r.score,
            rank=r.rank,
            confidence_min=r.confidence_min,
            confidence_max=r.confidence_max,
            eval_count=r.eval_count,
        ))

    return items


@router.get("/report", response_model=CleaningReportResponse)
async def get_cleaning_report(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取清洗报告"""
    sessions = db.query(EvalSession).all()

    valid_count = sum(1 for s in sessions if s.cleaning_status == "valid")
    invalid_count = sum(1 for s in sessions if s.cleaning_status == "invalid")
    pending_count = sum(1 for s in sessions if s.cleaning_status == "pending")

    details = []
    for s in sessions:
        user = db.query(User).filter(User.id == s.user_id).first()
        details.append(CleaningReportItem(
            user_id=s.user_id,
            username=user.username if user else "",
            session_id=s.id,
            session_status=s.cleaning_status,
            retest_weight=s.retest_weight,
            entropy_weight=s.entropy_weight,
            reject_reason=s.reject_reason,
        ))

    # 计算第二层清洗结果（用户一致率）
    user_agreements = []
    valid_sessions = [s for s in sessions if s.cleaning_status == "valid"]
    if valid_sessions:
        user_ids = list(set(s.user_id for s in valid_sessions))

        # 收集所有 valid session 的 submitted 评测
        valid_session_ids = [s.id for s in valid_sessions]
        all_evaluations = db.query(Evaluation).filter(
            Evaluation.session_id.in_(valid_session_ids),
            Evaluation.status == "submitted",
            Evaluation.is_repeat == 0,
        ).all()

        # 按 pair_id 构建评测矩阵
        pair_evaluations: dict[int, list[tuple[int, str]]] = {}
        for ev in all_evaluations:
            pair_evaluations.setdefault(ev.pair_id, []).append((ev.user_id, ev.score))

        # 计算每个用户的一致率
        for uid in user_ids:
            user = db.query(User).filter(User.id == uid).first()
            agreement = calculate_user_agreement(uid, pair_evaluations)
            status = "valid" if agreement >= CLEANING_AGREEMENT_THRESHOLD else "invalid"
            user_agreements.append(UserAgreementItem(
                user_id=uid,
                username=user.username if user else "",
                agreement=round(agreement, 4),
                status=status,
            ))

    return CleaningReportResponse(
        total_sessions=len(sessions),
        valid_sessions=valid_count,
        invalid_sessions=invalid_count,
        pending_sessions=pending_count,
        details=details,
        user_agreements=user_agreements,
    )


@router.get("/session/{session_id}/pairs", response_model=SessionDetailResponse)
async def get_session_pairs(
    session_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取 Session 的 Pair 评测详情"""
    session = db.query(EvalSession).filter(EvalSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session 不存在")

    user = db.query(User).filter(User.id == session.user_id).first()
    evaluations = db.query(Evaluation).filter(
        Evaluation.session_id == session_id,
        Evaluation.status == "submitted",
    ).options(
        joinedload(Evaluation.pair)
        .joinedload(ImagePair.image_a)
        .joinedload(Image.device),
        joinedload(Evaluation.pair)
        .joinedload(ImagePair.image_b)
        .joinedload(Image.device),
    ).all()

    pairs = []
    for ev in evaluations:
        if not ev.pair:
            continue

        device_a = ev.pair.image_a.device if ev.pair.image_a else None
        device_b = ev.pair.image_b.device if ev.pair.image_b else None

        pairs.append(SessionPairDetail(
            pair_id=ev.pair_id,
            device_a_name=device_a.name if device_a else "未知",
            device_b_name=device_b.name if device_b else "未知",
            score=ev.score,
            direction=DIRECTION_MAP.get(ev.score, "未知"),
        ))

    return SessionDetailResponse(
        session_id=session.id,
        user_id=session.user_id,
        username=user.username if user else "",
        cleaning_status=session.cleaning_status,
        retest_weight=session.retest_weight,
        entropy_weight=session.entropy_weight,
        reject_reason=session.reject_reason or "",
        pairs=pairs,
    )


@router.get("/device/{device_id}/winrate", response_model=DeviceWinRateResponse)
async def get_device_winrate(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取设备胜率详情"""
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 单次查询获取所有包含该设备的图对（带 eager loading）
    device_image_ids = db.query(Image.id).filter(Image.device_id == device_id).subquery()

    pairs = db.query(ImagePair).filter(
        or_(
            ImagePair.image_a_id.in_(device_image_ids),
            ImagePair.image_b_id.in_(device_image_ids),
        )
    ).options(
        joinedload(ImagePair.image_a).joinedload(Image.device),
        joinedload(ImagePair.image_b).joinedload(Image.device),
    ).all()

    # 在 Python 中分类
    pairs_as_a = []
    pairs_as_b = []
    for pair in pairs:
        if pair.image_a and pair.image_a.device_id == device_id:
            pairs_as_a.append(pair)
        if pair.image_b and pair.image_b.device_id == device_id:
            pairs_as_b.append(pair)

    # 批量查询所有相关评测（单次查询替代 N+1）
    all_pair_ids = [p.id for p in pairs_as_a] + [p.id for p in pairs_as_b]
    all_evals = db.query(Evaluation).filter(
        Evaluation.pair_id.in_(all_pair_ids),
        Evaluation.cleaning_status == "valid",
        Evaluation.status == "submitted",
    ).all()

    evals_by_pair: dict[int, list] = {}
    for ev in all_evals:
        evals_by_pair.setdefault(ev.pair_id, []).append(ev)

    # 统计胜率
    win_stats: dict[int, dict] = {}  # opponent_id -> {win, lose}

    for pair in pairs_as_a:
        opponent = pair.image_b.device if pair.image_b else None
        opponent_id = opponent.id if opponent else None
        if opponent_id is None:
            continue
        if opponent_id not in win_stats:
            win_stats[opponent_id] = {"win": 0, "lose": 0}
        for ev in evals_by_pair.get(pair.id, []):
            if ev.score in ("a_much", "a_slight"):
                win_stats[opponent_id]["win"] += 1
            elif ev.score in ("b_much", "b_slight"):
                win_stats[opponent_id]["lose"] += 1

    for pair in pairs_as_b:
        opponent = pair.image_a.device if pair.image_a else None
        opponent_id = opponent.id if opponent else None
        if opponent_id is None:
            continue
        if opponent_id not in win_stats:
            win_stats[opponent_id] = {"win": 0, "lose": 0}
        for ev in evals_by_pair.get(pair.id, []):
            if ev.score in ("b_much", "b_slight"):
                win_stats[opponent_id]["win"] += 1
            elif ev.score in ("a_much", "a_slight"):
                win_stats[opponent_id]["lose"] += 1

    # 批量查询对手设备信息（单次查询替代 N+1）
    all_opponent_ids = list(win_stats.keys())
    opponents = {d.id: d for d in db.query(DeviceModel).filter(DeviceModel.id.in_(all_opponent_ids)).all()}

    win_rates = []
    for opponent_id, stats in win_stats.items():
        opponent = opponents.get(opponent_id)
        total = stats["win"] + stats["lose"]
        win_rates.append(DeviceWinRate(
            opponent_id=opponent_id,
            opponent_name=opponent.name if opponent else f"Device-{opponent_id}",
            win_count=stats["win"],
            lose_count=stats["lose"],
            win_rate=stats["win"] / total if total > 0 else 0.0,
        ))

    # 获取各场景排名
    rankings = db.query(RankingResult).filter(RankingResult.device_id == device_id).all()
    scene_rankings = []
    for r in rankings:
        scene_name = ""
        if r.scene_id:
            scene = db.query(Scene).filter(Scene.id == r.scene_id).first()
            scene_name = scene.name if scene else ""
        scene_rankings.append({
            "scene_name": scene_name or "综合",
            "rank": r.rank,
            "score": r.score,
        })

    return DeviceWinRateResponse(
        device_id=device_id,
        device_name=device.name,
        win_rates=win_rates,
        scene_rankings=scene_rankings,
    )


@router.get("/compare", response_model=SceneCompareResponse)
async def get_scene_compare(
    scene_ids: str = Query(..., description="逗号分隔的场景ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取多场景对比数据"""
    ids = [int(x.strip()) for x in scene_ids.split(",") if x.strip()]
    if len(ids) == 0:
        raise HTTPException(status_code=400, detail="至少需要一个场景ID")
    if len(ids) > 3:
        raise HTTPException(status_code=400, detail="最多对比 3 个场景")
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="场景ID不能重复")

    # 单次查询场景（替代 N 次循环查询）
    scenes_db = db.query(Scene).filter(Scene.id.in_(ids)).all()
    if len(scenes_db) != len(ids):
        found_ids = {s.id for s in scenes_db}
        missing = [sid for sid in ids if sid not in found_ids]
        raise HTTPException(status_code=404, detail=f"场景不存在: {missing}")
    scenes = [s.name for s in scenes_db]

    # 单次批量查询所有排名（替代 N+1 循环查询）
    rankings = db.query(RankingResult).filter(
        RankingResult.scene_id.in_(ids)
    ).all()

    ranking_map = {}
    for r in rankings:
        ranking_map[(r.device_id, r.scene_id)] = r

    # 只查询有排名数据的设备
    device_ids_with_rankings = {r.device_id for r in rankings}
    devices = db.query(DeviceModel).filter(DeviceModel.id.in_(device_ids_with_rankings)).all()

    items = []
    for device in devices:
        scores = {}
        for sid, scene_name in zip(ids, scenes):
            r = ranking_map.get((device.id, sid))
            scores[scene_name] = r.score if r else 0.0

        avg_score = sum(scores.values()) / len(scores) if scores else 0.0

        items.append(SceneCompareItem(
            device_id=device.id,
            device_name=device.name,
            scores=scores,
            average_score=avg_score,
        ))

    # 按平均分排序
    items.sort(key=lambda x: x.average_score, reverse=True)

    return SceneCompareResponse(
        scenes=scenes,
        items=items,
    )
