"""
通用 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class ApiResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[dict] = None
