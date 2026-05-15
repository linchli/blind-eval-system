"""
场景相关 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class SceneCreate(BaseModel):
    category: str
    subcategory: str
    sort_order: int = 100


class SceneUpdate(BaseModel):
    category: Optional[str] = None
    subcategory: Optional[str] = None
    sort_order: Optional[int] = None


class SceneOut(BaseModel):
    id: int
    category: str
    subcategory: str
    name: str
    folder_name: str
    sort_order: int
    image_count: int = 0
    pair_count: int = 0
