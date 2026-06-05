"""
批量上传 API：逐场景上传图像
"""
import json
import re
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..core.config import IMAGE_DIR, THUMB_DIR
from ..models.user import User
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.scene import Scene
from ..models.device_model import DeviceModel
from ..models.image import Image
from ..schemas.batch_upload import BatchUploadResult
from ..services.image_service import save_image_file

router = APIRouter(prefix="/api/admin", tags=["批量上传"])

SCENE_NAME_PATTERN = re.compile(r'^(.+?)\((.+?)\)-(.+)$')

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}


def _generate_device_folder(name: str) -> str:
    folder = name.replace(" ", "_")
    folder = re.sub(r'[^a-zA-Z0-9_\-]', '', folder)
    return f"device_{folder}" if folder else "device_unknown"


def _parse_scene_name(folder_name: str, default_subcategory: str = ""):
    m = SCENE_NAME_PATTERN.match(folder_name)
    if m:
        return m.group(1), m.group(2), m.group(3)
    if default_subcategory:
        return folder_name, "", default_subcategory
    return None


def _find_or_create_category(db: Session, name: str, location: str):
    cat = db.query(SceneCategory).filter(
        SceneCategory.name == name,
        SceneCategory.location == location,
    ).first()
    if cat:
        return cat
    cat = SceneCategory(name=name, location=location)
    db.add(cat)
    db.flush()
    return cat


def _find_or_create_subcategory(db: Session, name: str):
    sub = db.query(SceneSubcategory).filter(SceneSubcategory.name == name).first()
    if sub:
        return sub
    sub = SceneSubcategory(name=name)
    db.add(sub)
    db.flush()
    return sub


def _find_or_create_scene(db: Session, category, subcategory):
    scene = db.query(Scene).filter(
        Scene.category_id == category.id,
        Scene.subcategory_id == subcategory.id,
    ).first()
    if scene:
        return scene
    scene = Scene(
        category_id=category.id,
        subcategory_id=subcategory.id,
        sort_order=0,
    )
    db.add(scene)
    db.flush()
    (IMAGE_DIR / scene.folder_name).mkdir(parents=True, exist_ok=True)
    (THUMB_DIR / scene.folder_name).mkdir(parents=True, exist_ok=True)
    return scene


def _build_device_map(db: Session, devices_config: list[dict], mode: str) -> dict:
    device_map = {}
    for item in devices_config:
        name = item.get("设备名", "").strip()
        if not name:
            continue
        existing = db.query(DeviceModel).filter(DeviceModel.name == name).first()
        if existing:
            device_map[name] = existing
            continue
        # 两种模式均自动创建不存在的设备
        folder_name = _generate_device_folder(name)
        device = DeviceModel(
            name=name,
            folder_name=folder_name,
            main_chip=item.get("主控型号", ""),
            lens_model=item.get("镜头型号", ""),
            sensor_model=item.get("Sensor型号", ""),
            aperture=item.get("光圈", ""),
            focal_length=item.get("焦距", ""),
            resolution=item.get("分辨率", ""),
            frame_rate=item.get("帧率", ""),
            white_led=item.get("白光灯珠料号", ""),
            ir_led=item.get("红外灯珠料号", ""),
            housing_info=item.get("壳体信息", ""),
            device_attrs={"固件版本": item.get("固件版本", "")} if item.get("固件版本") else {},
        )
        db.add(device)
        db.flush()
        device_map[name] = device
    return device_map


def _map_metadata(metadata: dict) -> tuple:
    note_attrs = metadata.get("基础采集信息", {})
    env_attrs = metadata.get("场景信息", {})
    shot_attrs = metadata.get("图像视频参数", {})
    isp_attrs = metadata.get("ISP参数", {})
    return shot_attrs, env_attrs, isp_attrs, note_attrs


@router.post("/batch-upload/", response_model=BatchUploadResult)
async def batch_upload(
    manifest: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    try:
        data = json.loads(manifest)
    except json.JSONDecodeError:
        return BatchUploadResult(scene_name="", errors=["manifest JSON 解析失败"])

    scene_folder_name = data.get("scene_folder_name", "")
    mode = data.get("mode", "loose")
    default_subcategory = data.get("default_subcategory", "")
    devices_config = data.get("devices", [])

    # 解析场景名
    parsed = _parse_scene_name(scene_folder_name, default_subcategory)
    if parsed is None:
        return BatchUploadResult(
            scene_name=scene_folder_name,
            errors=[f"文件夹名 '{scene_folder_name}' 无法解析为 '大类(地点)-子类' 格式"],
        )
    cat_name, loc_name, sub_name = parsed

    try:
        # 创建场景
        category = _find_or_create_category(db, cat_name, loc_name)
        subcategory = _find_or_create_subcategory(db, sub_name)
        scene = _find_or_create_scene(db, category, subcategory)

        # 构建设备映射
        device_map = _build_device_map(db, devices_config, mode)

        # 分离图像和元信息文件
        image_files = []
        metadata_map = {}
        for f in files:
            if not f.filename:
                continue
            ext = '.' + f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
            stem = f.filename.rsplit('.', 1)[0] if '.' in f.filename else f.filename
            if ext == '.json':
                content = await f.read()
                try:
                    metadata_map[stem] = json.loads(content.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            elif ext in IMAGE_EXTENSIONS:
                image_files.append((f, stem))

        # 逐图像处理
        uploaded = 0
        skipped = 0
        errors = []
        for img_file, device_name in image_files:
            device = device_map.get(device_name)
            if device is None:
                errors.append(f"{img_file.filename}: 设备 '{device_name}' 不存在")
                continue

            existing = db.query(Image).filter(
                Image.scene_id == scene.id,
                Image.device_id == device.id,
            ).first()
            if existing:
                skipped += 1
                continue

            content = await img_file.read()
            image_url, thumb_path = save_image_file(
                content, scene.folder_name, device.folder_name, img_file.filename,
            )

            metadata = metadata_map.get(device_name, {})
            shot_attrs, env_attrs, isp_attrs, note_attrs = _map_metadata(metadata)

            image = Image(
                scene_id=scene.id,
                device_id=device.id,
                image_path=image_url,
                thumb_path=thumb_path,
                shot_attrs=shot_attrs,
                env_attrs=env_attrs,
                isp_attrs=isp_attrs,
                note_attrs=note_attrs,
            )
            db.add(image)
            db.flush()
            uploaded += 1

        db.commit()
        return BatchUploadResult(
            scene_name=scene.name,
            scene_id=scene.id,
            uploaded=uploaded,
            skipped=skipped,
            errors=errors,
        )

    except Exception as e:
        db.rollback()
        return BatchUploadResult(
            scene_name=scene_folder_name,
            errors=[f"上传失败: {str(e)}"],
        )
