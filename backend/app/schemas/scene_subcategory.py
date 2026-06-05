"""
子类/时段 Pydantic 模型（全局共享）
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class SubcategoryCreate(BaseModel):
    name: str


class SubcategoryUpdate(BaseModel):
    name: Optional[str] = None


class SubcategoryOut(BaseModel):
    id: int
    name: str
    scene_count: int = 0

    model_config = ConfigDict(from_attributes=True)
