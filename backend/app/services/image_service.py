"""
图像服务：上传、缩略图生成、配对生成
"""
import os
from pathlib import Path
from PIL import Image as PILImage
from sqlalchemy.orm import Session
from itertools import combinations

from ..core.config import BASE_DIR, IMAGE_DIR, THUMB_DIR, THUMB_SIZE
from ..models.image import Image
from ..models.image_pair import ImagePair
from ..models.scene import Scene
from ..models.device_model import DeviceModel


def save_image_file(file_content: bytes, scene_folder: str, device_folder: str, filename: str) -> str:
    """保存图像文件并生成缩略图，返回相对路径"""
    # 确保目录存在
    dest_dir = IMAGE_DIR / scene_folder / device_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 保存原图
    file_path = dest_dir / filename
    with open(file_path, "wb") as f:
        f.write(file_content)

    # 生成缩略图
    thumb_path = ""
    try:
        thumb_dir = THUMB_DIR / scene_folder / device_folder
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_file = thumb_dir / filename

        img = PILImage.open(file_path)
        img.thumbnail(THUMB_SIZE, PILImage.Resampling.LANCZOS)
        img.save(thumb_file, quality=85)
        thumb_path = f"/uploads/thumbnails/{scene_folder}/{device_folder}/{filename}"
    except Exception:
        pass  # 缩略图失败不影响上传

    image_url = f"/uploads/images/{scene_folder}/{device_folder}/{filename}"
    return image_url, thumb_path


def delete_image_files(image_path: str, thumb_path: str):
    """删除图像文件和缩略图"""
    for rel_path in [image_path, thumb_path]:
        if not rel_path:
            continue
        # rel_path 格式: /uploads/images/scene/device/file.jpg
        physical = BASE_DIR / rel_path.lstrip("/")
        if physical.is_file():
            physical.unlink()


def generate_pairs_for_scene(db: Session, scene_id: int) -> dict:
    """为指定场景增量生成配对，返回统计信息"""
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return {"error": "场景不存在"}

    # 查询该场景下所有图像
    images = db.query(Image).filter(Image.scene_id == scene_id).all()
    if len(images) < 2:
        return {"error": "该场景下图像不足2张，无法生成配对"}

    # 查询已有配对
    existing_pairs = db.query(ImagePair).filter(ImagePair.scene_id == scene_id).all()
    existing_set = {(p.image_a_id, p.image_b_id) for p in existing_pairs}

    # 计算全组合
    new_pairs = []
    for img_a, img_b in combinations(images, 2):
        pair_key = (min(img_a.id, img_b.id), max(img_a.id, img_b.id))
        if pair_key not in existing_set:
            new_pairs.append((img_a, img_b))

    if not new_pairs:
        return {
            "scene_name": scene.name,
            "current_image_count": len(images),
            "total_combinations": len(images) * (len(images) - 1) // 2,
            "existing_pair_count": len(existing_pairs),
            "new_pair_count": 0,
            "message": "无新配对生成",
        }

    # 批量插入
    max_sort = max((p.sort_order for p in existing_pairs), default=0)
    for i, (img_a, img_b) in enumerate(new_pairs):
        a_id, b_id = min(img_a.id, img_b.id), max(img_a.id, img_b.id)
        db.add(ImagePair(
            scene_id=scene_id,
            image_a_id=a_id,
            image_b_id=b_id,
            sort_order=max_sort + i + 1,
        ))

    db.flush()

    return {
        "scene_name": scene.name,
        "current_image_count": len(images),
        "total_combinations": len(images) * (len(images) - 1) // 2,
        "existing_pair_count": len(existing_pairs),
        "new_pair_count": len(new_pairs),
        "message": f"成功生成 {len(new_pairs)} 对新配对",
    }


def preview_pair_generation(db: Session, scene_id: int) -> dict:
    """预览配对生成结果（不实际写入）"""
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        return {"error": "场景不存在"}

    images = db.query(Image).filter(Image.scene_id == scene_id).all()
    existing_pairs = db.query(ImagePair).filter(ImagePair.scene_id == scene_id).all()
    existing_set = {(p.image_a_id, p.image_b_id) for p in existing_pairs}

    new_count = 0
    for img_a, img_b in combinations(images, 2):
        pair_key = (min(img_a.id, img_b.id), max(img_a.id, img_b.id))
        if pair_key not in existing_set:
            new_count += 1

    return {
        "scene_name": scene.name,
        "current_image_count": len(images),
        "total_combinations": len(images) * (len(images) - 1) // 2,
        "existing_pair_count": len(existing_pairs),
        "new_pair_count": new_count,
    }
