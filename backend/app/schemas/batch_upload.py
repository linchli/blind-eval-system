"""
批量上传相关 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class BatchUploadManifest(BaseModel):
    scene_folder_name: str
    mode: str = "loose"
    default_subcategory: str = ""
    devices: list[dict] = []


class BatchUploadResult(BaseModel):
    scene_name: str
    scene_id: Optional[int] = None
    uploaded: int = 0
    skipped: int = 0
    errors: list[str] = []
