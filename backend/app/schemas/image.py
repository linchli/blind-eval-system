"""
图像相关 Pydantic 模型
"""
from pydantic import BaseModel
from typing import Optional


class ImageOut(BaseModel):
    id: int
    scene_id: int
    device_id: int
    scene_name: str = ""
    device_name: str = ""
    image_path: str
    thumb_path: str = ""
    shot_attrs: dict = {}
    env_attrs: dict = {}
    isp_attrs: dict = {}
    note_attrs: dict = {}


class ImageUploadRequest(BaseModel):
    """JSON 属性部分（文件单独上传）"""
    shot_attrs: dict = {}
    env_attrs: dict = {}
    isp_attrs: dict = {}
    note_attrs: dict = {}


class PairGenerateRequest(BaseModel):
    scene_id: int
    strategy: str = "full"  # full | baseline


class PairGeneratePreview(BaseModel):
    scene_name: str
    strategy: str
    current_image_count: int
    total_combinations: int
    existing_pair_count: int
    new_pair_count: int


class PairGenerateResult(BaseModel):
    scene_name: str
    strategy: str
    new_pairs: int = 0
    total_pairs: int = 0
    message: str = ""


class ImagePairOut(BaseModel):
    id: int
    scene_id: int
    scene_name: str = ""
    image_a_id: int
    image_b_id: int
    device_a_name: str = ""
    device_b_name: str = ""
    image_a_url: str = ""
    image_b_url: str = ""
    sort_order: int
    eval_count: int = 0


class ImagePairBrief(BaseModel):
    """盲评时返回（隐藏设备信息）"""
    pair_id: int
    image_a_url: str
    image_b_url: str
    scene_name: str = ""


class SessionPairInfo(BaseModel):
    """会话中的图对详情（含当前用户评分）"""
    pair_id: int
    scene_name: str = ""
    image_a_url: str
    image_b_url: str
    my_score: Optional[str] = None
