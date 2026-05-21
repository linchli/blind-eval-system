"""
数据清洗路由：重测信度计算
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user
from ..models.user import User
from ..models.evaluation import EvalSession
from ..schemas.cleaning import RetestReliabilityRequest, RetestReliabilityResponse
from ..services.cleaning_service import calculate_retest_reliability

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

    # 计算重测信度
    result = calculate_retest_reliability(
        db=db,
        user_id=current_user.id,
        session_id=body.session_id,
    )

    return result
