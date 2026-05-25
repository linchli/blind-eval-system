"""
统计服务
"""
import math
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.evaluation import Evaluation, EvalSession
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.scene import Scene
from ..models.device_model import DeviceModel
from ..models.user import User


def get_overview(db: Session) -> dict:
    """获取系统概览统计"""
    return {
        "scene_count": db.query(Scene).count(),
        "device_count": db.query(DeviceModel).count(),
        "image_count": db.query(Image).count(),
        "pair_count": db.query(ImagePair).count(),
        "eval_count": db.query(Evaluation).filter(Evaluation.status == "submitted").count(),
        "user_count": db.query(User).count(),
    }


def get_scene_stats(db: Session, scene_id: int) -> dict:
    """获取指定场景的统计信息"""
    image_count = db.query(Image).filter(Image.scene_id == scene_id).count()
    pair_count = db.query(ImagePair).filter(ImagePair.scene_id == scene_id).count()
    return {
        "image_count": image_count,
        "pair_count": pair_count,
    }
