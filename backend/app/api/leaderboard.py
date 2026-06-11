"""
排行榜 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user, require_admin, get_optional_user
from ..models.user import User
from ..schemas.cleaning import ApiResponse
from ..services.leaderboard_service import (
    get_leaderboard,
    get_filter_options,
    get_leaderboard_details,
    get_users_list,
    export_leaderboard,
)

router = APIRouter(prefix="/api/leaderboard", tags=["排行榜"])


@router.get("")
async def leaderboard(
    filter_type: str = Query("overall", description="筛选类型"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
    score_type: str = Query("bt", description="得分类型: bt/mean"),
    db: Session = Depends(get_db),
):
    """获取排行榜数据（无需登录）"""
    data = get_leaderboard(db, filter_type, filter_value, score_type)
    return ApiResponse(data=data)


@router.get("/filters")
async def filters(db: Session = Depends(get_db)):
    """获取可用的筛选选项（无需登录）"""
    data = get_filter_options(db)
    return ApiResponse(data=data)


@router.get("/users")
async def users_list(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取用户列表（管理员权限，用于详细数据按用户筛选）"""
    data = get_users_list(db)
    return ApiResponse(data=data)


@router.get("/details")
async def details(
    view_type: str = Query(..., description="视图类型: scene/user/device"),
    id: int = Query(..., description="具体 ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取详细评测数据（管理员权限）"""
    data = get_leaderboard_details(db, view_type, id)
    return ApiResponse(data=data)


@router.get("/export")
async def export_data(
    export_type: str = Query("ranking", description="导出类型: ranking/detail"),
    filter_type: str = Query("overall", description="筛选类型"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
    view_type: Optional[str] = Query(None, description="详细数据视图类型: scene/user/device，不传则导出全部"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """导出排行榜数据（管理员权限）"""
    content = export_leaderboard(db, export_type, filter_type, filter_value, view_type)
    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=leaderboard_export.txt"},
    )
