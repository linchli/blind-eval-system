"""
数据清洗路由：重测信度计算
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..models.evaluation import Evaluation, EvalSession
from ..schemas.cleaning import RetestReliabilityRequest, RetestReliabilityResponse, RepeatPairResult
from ..services.cleaning_service import check_retest_reliability, get_score_direction

router = APIRouter(prefix="/api/cleaning", tags=["数据清洗"])


@router.post("/retest-reliability", response_model=RetestReliabilityResponse)
async def get_retest_reliability(
    body: RetestReliabilityRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    计算指定会话的重测信度

    重测信度通过比较同一图对的两次评测结果来衡量用户评分的一致性。
    """
    # 验证会话存在且属于当前用户
    session = db.query(EvalSession).filter(
        EvalSession.id == body.session_id,
        EvalSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="评测会话不存在")

    if session.status != "completed":
        raise HTTPException(status_code=400, detail="评测会话尚未完成，请先完成评测")

    # 获取该 session 的所有 submitted 评测
    evaluations = db.query(Evaluation).filter(
        Evaluation.user_id == current_user.id,
        Evaluation.session_id == body.session_id,
        Evaluation.status == "submitted"
    ).all()

    # 按 pair_id 分组
    pair_evaluations = {}
    for ev in evaluations:
        if ev.pair_id not in pair_evaluations:
            pair_evaluations[ev.pair_id] = []
        pair_evaluations[ev.pair_id].append(ev)

    # 找出有重复评测的图对
    repeat_pairs = []
    for pair_id, evals in pair_evaluations.items():
        if len(evals) >= 2:
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
    passed = reliability >= 0.6

    # 生成拒绝原因
    reject_reason = None
    if not passed:
        if total_repeat == 0:
            reject_reason = "无重复图对数据"
        else:
            reject_reason = f"重测信度不足（{reliability:.2f} < 0.6）"

    return RetestReliabilityResponse(
        session_id=body.session_id,
        user_id=current_user.id,
        repeat_pairs=repeat_pairs,
        total_repeat=total_repeat,
        consistent_count=consistent_count,
        reliability=reliability,
        passed=passed,
        reject_reason=reject_reason,
    )
