"""
评测路由：会话式盲评核心逻辑
"""
import random
import csv
import io
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..core.config import SCORE_MAP, DEFAULT_BATCH_SIZE, MAX_BATCH_SIZE, DAILY_LIMIT, REST_AFTER_BATCHES, REPEAT_RATIO
from ..models.user import User
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.evaluation import Evaluation, EvalSession
from ..schemas.eval import (
    EvaluationSubmitRequest, SubmitRoundRequest,
    EvalStatusResponse, ActiveSessionInfo,
    StartSessionResponse, ResumeSessionResponse,
    EvaluationSubmitResponse, SubmitRoundResponse, PairDetailResponse,
    ProgressOut, EvaluationOut,
)
from ..schemas.image import ImagePairBrief, SessionPairInfo
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/api/eval", tags=["盲评"])


def _get_image_url(pair: ImagePair, side: str) -> str:
    """获取图像对中指定侧的图像 URL"""
    if side == "a":
        return pair.image_a.image_path if pair.image_a else ""
    return pair.image_b.image_path if pair.image_b else ""


def _get_device_id(pair: ImagePair, side: str) -> int | None:
    """获取图像对中指定侧的设备 ID"""
    if side == "a":
        return pair.image_a.device_id if pair.image_a else None
    return pair.image_b.device_id if pair.image_b else None


def _build_pair_info(pair: ImagePair, my_score: str | None = None) -> SessionPairInfo:
    """构建会话中的图对信息（隐藏设备信息）"""
    return SessionPairInfo(
        pair_id=pair.id,
        scene_name=pair.scene.name if pair.scene else "",
        image_a_url=_get_image_url(pair, "a"),
        image_b_url=_get_image_url(pair, "b"),
        my_score=my_score,
    )


# ==================== 辅助函数 ====================

def get_user_last_submit_time(db: Session, user_id: int) -> datetime | None:
    ev = db.query(Evaluation).filter(
        Evaluation.user_id == user_id,
        Evaluation.status == "submitted",
        Evaluation.submitted_at.isnot(None)
    ).order_by(Evaluation.submitted_at.desc()).first()
    return ev.submitted_at if ev else None


def get_daily_evaluated_count(db: Session, user_id: int) -> int:
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return db.query(Evaluation).filter(
        Evaluation.user_id == user_id,
        Evaluation.status == "submitted",
        Evaluation.submitted_at >= today_start
    ).count()


def get_new_pairs_count(db: Session, user_id: int) -> int:
    last_submit = get_user_last_submit_time(db, user_id)
    if not last_submit:
        return db.query(ImagePair).count()
    return db.query(ImagePair).filter(ImagePair.created_at > last_submit).count()


def check_suggest_rest(db: Session, user_id: int) -> bool:
    recent_sessions = db.query(EvalSession).filter(
        EvalSession.user_id == user_id,
        EvalSession.status == "completed",
        EvalSession.completed_at.isnot(None)
    ).order_by(EvalSession.completed_at.desc()).limit(REST_AFTER_BATCHES).all()

    if len(recent_sessions) < REST_AFTER_BATCHES:
        return False

    last_complete = recent_sessions[-1].completed_at
    if last_complete and (datetime.now() - last_complete) < timedelta(hours=24):
        return True
    return False


# ==================== API 端点 ====================

@router.get("/status", response_model=EvalStatusResponse)
async def get_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_pairs = db.query(ImagePair).count()
    if total_pairs == 0:
        return EvalStatusResponse(
            total_pairs=0, evaluated_count=0, remaining_count=0,
            status="no_pairs", active_session=None,
            new_pairs_count=0, daily_evaluated=0, suggest_rest=False,
        )

    # 统计唯一 pair_id 数量（排除重复图对）
    evaluated_count = db.query(Evaluation.pair_id).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.status == "submitted",
        Evaluation.is_repeat == 0
    ).distinct().count()
    remaining_count = total_pairs - evaluated_count

    if remaining_count == 0:
        return EvalStatusResponse(
            total_pairs=total_pairs, evaluated_count=evaluated_count,
            remaining_count=0, status="all_done", active_session=None,
            new_pairs_count=0,
            daily_evaluated=get_daily_evaluated_count(db, current_user.id),
            suggest_rest=False,
        )

    active_session = db.query(EvalSession).filter(
        EvalSession.user_id == current_user.id,
        EvalSession.status == "active"
    ).first()

    if active_session:
        draft_in_session = db.query(Evaluation).filter(
            Evaluation.user_id == current_user.id,
            Evaluation.session_id == active_session.id,
            Evaluation.status == "draft"
        ).count()
        remaining_in_session = active_session.batch_size - draft_in_session

        return EvalStatusResponse(
            total_pairs=total_pairs, evaluated_count=evaluated_count,
            remaining_count=remaining_count, status="resumable",
            active_session=ActiveSessionInfo(
                session_id=active_session.id,
                batch_size=active_session.batch_size,
                evaluated_in_session=draft_in_session,
                remaining_in_session=remaining_in_session,
            ),
            new_pairs_count=get_new_pairs_count(db, current_user.id),
            daily_evaluated=get_daily_evaluated_count(db, current_user.id),
            suggest_rest=False,
        )

    return EvalStatusResponse(
        total_pairs=total_pairs, evaluated_count=evaluated_count,
        remaining_count=remaining_count, status="ready", active_session=None,
        new_pairs_count=get_new_pairs_count(db, current_user.id),
        daily_evaluated=get_daily_evaluated_count(db, current_user.id),
        suggest_rest=check_suggest_rest(db, current_user.id),
    )


@router.post("/start-session", response_model=StartSessionResponse)
async def start_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(EvalSession).filter(
        EvalSession.user_id == current_user.id,
        EvalSession.status == "active"
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="您已有进行中的评测会话，请先继续完成")

    evaluated_pairs = db.query(Evaluation.pair_id).filter(
        Evaluation.user_id == current_user.id
    ).subquery()

    remaining_pairs = db.query(ImagePair).filter(
        ~ImagePair.id.in_(evaluated_pairs)
    ).all()

    if not remaining_pairs:
        raise HTTPException(status_code=400, detail="所有图像对已评价完毕")

    # 计算本轮图对数量
    new_pair_count = min(DEFAULT_BATCH_SIZE, len(remaining_pairs))
    repeat_count = max(0, int(new_pair_count * REPEAT_RATIO))
    batch_size = new_pair_count + repeat_count

    # 选取新图对并排序
    sorted_pairs = sorted(remaining_pairs, key=lambda p: (p.scene_id, p.sort_order))
    selected_pairs = sorted_pairs[:new_pair_count]

    # 从新图对中随机选取重复图对
    repeat_pairs = random.sample(selected_pairs, repeat_count)

    # 构建 pair_ids：新图对 + 重复图对
    pair_ids = [p.id for p in selected_pairs] + [p.id for p in repeat_pairs]

    session = EvalSession(
        user_id=current_user.id,
        status="active",
        pair_ids=pair_ids,
        batch_size=batch_size,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    current_user.last_active_at = datetime.now()
    db.commit()

    # 构建图对信息：重复图对标记为 is_repeat=1
    pairs_info = []
    for p in selected_pairs:
        pairs_info.append(_build_pair_info(p, None))
    for p in repeat_pairs:
        pairs_info.append(_build_pair_info(p, None))

    return StartSessionResponse(
        session_id=session.id,
        batch_size=batch_size,
        pairs=pairs_info,
    )


@router.post("/resume-session", response_model=ResumeSessionResponse)
async def resume_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(EvalSession).filter(
        EvalSession.user_id == current_user.id,
        EvalSession.status == "active"
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="没有找到进行中的评测会话")

    pair_ids = session.pair_ids if isinstance(session.pair_ids, list) else []
    pairs = db.query(ImagePair).filter(ImagePair.id.in_(pair_ids)).all()
    pair_map = {p.id: p for p in pairs}

    # 获取所有草稿评测，包括重复图对
    drafts = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.session_id == session.id,
        Evaluation.status == "draft"
    ).all()

    # 构建草稿映射：(pair_id, is_repeat) -> score
    draft_map = {}
    for d in drafts:
        draft_map[(d.pair_id, d.is_repeat)] = d.score

    # 构建图对信息，处理重复图对
    pairs_info = []
    pair_occurrence_count = {}  # 记录每个 pair_id 已出现的次数

    for pid in pair_ids:
        if pid in pair_map:
            # 计算当前是第几次出现
            occurrence = pair_occurrence_count.get(pid, 0)
            pair_occurrence_count[pid] = occurrence + 1

            # 获取对应的草稿评分
            is_repeat = 1 if occurrence > 0 else 0
            my_score = draft_map.get((pid, is_repeat))

            pairs_info.append(_build_pair_info(pair_map[pid], my_score))

    next_cursor = 0
    for i, info in enumerate(pairs_info):
        if info.my_score is None:
            next_cursor = i
            break

    current_user.last_active_at = datetime.now()
    db.commit()

    return ResumeSessionResponse(
        session_id=session.id,
        batch_size=session.batch_size,
        pairs=pairs_info,
        next_cursor=next_cursor,
    )


@router.post("/submit", response_model=EvaluationSubmitResponse)
async def submit_evaluation(
    body: EvaluationSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.score not in SCORE_MAP:
        raise HTTPException(status_code=400, detail=f"无效评分: {body.score}")

    session = db.query(EvalSession).filter(
        EvalSession.id == body.session_id,
        EvalSession.user_id == current_user.id,
        EvalSession.status == "active"
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="评测会话不存在或已结束")

    if body.pair_id not in session.pair_ids:
        raise HTTPException(status_code=400, detail="该图对不在当前会话中")

    pair = db.query(ImagePair).filter(ImagePair.id == body.pair_id).first()
    if not pair:
        raise HTTPException(status_code=404, detail="图像对不存在")

    # 先查找该 pair_id 是否已有草稿记录（无论 is_repeat 值）
    existing_draft = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.pair_id == body.pair_id,
        Evaluation.session_id == body.session_id,
        Evaluation.status == "draft"
    ).first()

    if existing_draft:
        # 已有草稿记录，直接更新，保留原始 is_repeat 值
        score_info = SCORE_MAP[body.score]
        existing_draft.score = body.score
        existing_draft.score_label = body.score_label
        existing_draft.score_a = score_info["score_a"]
        existing_draft.score_b = score_info["score_b"]
        db.commit()
        db.refresh(existing_draft)
        return EvaluationSubmitResponse(
            evaluation_id=existing_draft.id,
            status="draft",
            score=existing_draft.score,
        )

    # 没有草稿记录，检查是否已提交（不可修改）
    existing_submitted = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.pair_id == body.pair_id,
        Evaluation.session_id == body.session_id,
        Evaluation.status == "submitted"
    ).first()
    if existing_submitted:
        raise HTTPException(status_code=409, detail="该图对已提交，不可修改")

    # 通过 session.pair_ids 判断是否为重复图对
    pair_ids = session.pair_ids if isinstance(session.pair_ids, list) else []
    pair_occurrence_count = pair_ids.count(body.pair_id)
    # 如果 pair_id 在列表中出现多次，则本次为重复评测（第2次）
    has_first_eval = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.pair_id == body.pair_id,
        Evaluation.session_id == body.session_id,
    ).first()
    is_repeat = 1 if (pair_occurrence_count > 1 and has_first_eval) else 0

    score_info = SCORE_MAP[body.score]
    draft = Evaluation(
        user_id=current_user.id,
        pair_id=body.pair_id,
        session_id=body.session_id,
        score=body.score,
        score_label=body.score_label,
        score_a=score_info["score_a"],
        score_b=score_info["score_b"],
        is_repeat=is_repeat,
        status="draft",
    )
    db.add(draft)

    db.commit()
    db.refresh(draft)

    return EvaluationSubmitResponse(
        evaluation_id=draft.id,
        status="draft",
        score=draft.score,
    )


@router.post("/submit-round", response_model=SubmitRoundResponse)
async def submit_round(
    body: SubmitRoundRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(EvalSession).filter(
        EvalSession.id == body.session_id,
        EvalSession.user_id == current_user.id,
        EvalSession.status == "active"
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="评测会话不存在或已结束")

    pair_ids = session.pair_ids if isinstance(session.pair_ids, list) else []

    drafts = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.session_id == session.id,
        Evaluation.status == "draft"
    ).all()

    draft_pair_ids = {d.pair_id for d in drafts}
    missing = [pid for pid in pair_ids if pid not in draft_pair_ids]

    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"还有 {len(missing)} 对图对未评分，请先完成所有评测"
        )

    now = datetime.now()
    for draft in drafts:
        draft.status = "submitted"
        draft.submitted_at = now

    session.status = "completed"
    session.completed_at = now

    current_user.last_active_at = now
    db.commit()

    score_distribution = {"a_much": 0, "a_slight": 0, "same": 0, "b_slight": 0, "b_much": 0}
    for d in drafts:
        if d.score in score_distribution:
            score_distribution[d.score] += 1

    total_pairs = db.query(ImagePair).count()
    # 统计唯一 pair_id 数量（排除重复图对）
    evaluated_count = db.query(Evaluation.pair_id).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.status == "submitted",
        Evaluation.is_repeat == 0
    ).distinct().count()
    remaining_count = total_pairs - evaluated_count

    return SubmitRoundResponse(
        session_id=session.id,
        total_evaluated=len(drafts),
        remaining_count=remaining_count,
        score_distribution=score_distribution,
    )


@router.get("/pair/{pair_id}", response_model=PairDetailResponse)
async def get_pair_detail(
    pair_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pair = db.query(ImagePair).filter(ImagePair.id == pair_id).first()
    if not pair:
        raise HTTPException(status_code=404, detail="图像对不存在")

    eval_record = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.pair_id == pair_id
    ).first()

    my_score = eval_record.score if eval_record else None

    return PairDetailResponse(
        pair_id=pair.id,
        scene_name=pair.scene.name if pair.scene else "",
        image_a_url=_get_image_url(pair, "a"),
        image_b_url=_get_image_url(pair, "b"),
        my_score=my_score,
    )


# ==================== 兼容旧 API ====================

@router.get("/progress", response_model=ProgressOut)
async def get_progress(
    scene_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(ImagePair)
    if scene_id:
        q = q.filter(ImagePair.scene_id == scene_id)
    total = q.count()

    evaluated = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.status == "submitted"
    )
    if scene_id:
        evaluated = evaluated.join(ImagePair, Evaluation.pair_id == ImagePair.id).filter(
            ImagePair.scene_id == scene_id
        )
    evaluated = evaluated.count()

    remaining = total - evaluated
    pct = round((evaluated / total * 100)) if total > 0 else 0

    return ProgressOut(
        total_pairs=total,
        evaluated_count=evaluated,
        remaining_count=remaining,
        progress_percent=pct,
    )


@router.get("/my", response_model=list[EvaluationOut])
async def get_my_evaluations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evals = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id
    ).order_by(Evaluation.id).all()

    return [
        EvaluationOut(
            id=e.id, pair_id=e.pair_id, score=e.score,
            score_label=e.score_label, score_a=e.score_a, score_b=e.score_b,
            created_at=str(e.created_at) if e.created_at else None,
        )
        for e in evals
    ]


@router.get("/export/csv")
async def export_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    evals = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.status == "submitted"
    ).order_by(Evaluation.id).all()

    output = io.StringIO()
    output.write("﻿")
    writer = csv.writer(output)
    writer.writerow(["序号", "图像对ID", "评分", "评分说明", "A得分", "B得分", "提交时间"])

    for i, e in enumerate(evals, 1):
        writer.writerow([
            i, e.pair_id, e.score, e.score_label,
            e.score_a, e.score_b,
            str(e.submitted_at) if e.submitted_at else str(e.created_at),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=eval_results.csv"},
    )
