"""
数据清洗 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..models.user import User
from ..schemas.cleaning import (
    CleaningExecuteRequest,
    CleaningExecuteResponse,
    CleaningStatusResponse,
    CleaningParams,
    ApiResponse,
)
from ..services.cleaning_service import execute_cleaning, get_cleaning_status, export_cleaning_report
from ..services.leaderboard_service import compute_leaderboard

router = APIRouter(prefix="/api/cleaning", tags=["数据清洗"])


@router.get("/defaults")
async def get_cleaning_defaults():
    """获取清洗参数默认值"""
    params = CleaningParams()
    return ApiResponse(data=params.model_dump())


@router.get("/status")
async def get_status(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取当前清洗状态"""
    status = get_cleaning_status(db)
    return ApiResponse(data=status)


@router.post("/execute")
async def execute(
    body: CleaningExecuteRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """执行数据清洗"""
    try:
        result = execute_cleaning(db, body.params)

        # 清洗完成后自动计算排行榜
        if result["total_records"] > 0:
            lb_result = compute_leaderboard(db)
            result["leaderboard_updated"] = True

        return ApiResponse(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清洗失败: {str(e)}")


@router.get("/export")
async def export_report(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """导出清洗报告"""
    report = export_cleaning_report(db)
    return PlainTextResponse(
        content=report,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=cleaning_report.txt"},
    )
