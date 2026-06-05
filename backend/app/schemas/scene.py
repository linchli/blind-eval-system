"""
场景 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class SceneCreate(BaseModel):
    category_id: int
    subcategory_id: int
    sort_order: int = 100


class SceneUpdate(BaseModel):
    sort_order: Optional[int] = None


class SceneOut(BaseModel):
    id: int
    category_id: int
    category_name: str = ""
    location: str = ""
    subcategory_id: int
    subcategory_name: str = ""
    name: str = ""
    folder_name: str = ""
    sort_order: int
    image_count: int = 0
    pair_count: int = 0

    model_config = ConfigDict(from_attributes=True)
