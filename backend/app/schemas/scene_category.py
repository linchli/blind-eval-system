"""
大类 × 地点 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class CategoryCreate(BaseModel):
    name: str
    location: str = ""


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    location: str
    scene_count: int = 0

    model_config = ConfigDict(from_attributes=True)
