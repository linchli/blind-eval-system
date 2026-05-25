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