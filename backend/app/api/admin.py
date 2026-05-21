"""
管理路由：场景/设备 CRUD
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..core.config import IMAGE_DIR
from ..models.user import User
from ..models.scene import Scene
from ..models.device_model import DeviceModel
from ..models.image import Image
from ..models.image_pair import ImagePair
from ..schemas.scene import SceneCreate, SceneUpdate, SceneOut
from ..schemas.device_model import DeviceModelCreate, DeviceModelUpdate, DeviceModelOut
from ..schemas.common import ApiResponse

router = APIRouter(prefix="/api/admin", tags=["管理"])


# ==================== 场景管理 ====================

@router.get("/scenes", response_model=list[SceneOut])
async def get_scenes(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    scenes = db.query(Scene).order_by(Scene.sort_order).all()
    result = []
    for s in scenes:
        image_count = db.query(Image).filter(Image.scene_id == s.id).count()
        pair_count = db.query(ImagePair).filter(ImagePair.scene_id == s.id).count()
        result.append(SceneOut(
            id=s.id, category=s.category, subcategory=s.subcategory,
            name=s.name, folder_name=s.folder_name, sort_order=s.sort_order,
            image_count=image_count, pair_count=pair_count,
        ))
    return result

@router.post("/scenes", response_model=SceneOut)
async def create_scene(
    body: SceneCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    name = f"{body.category}-{body.subcategory}"

    if db.query(Scene).filter(Scene.name == name).first():
        raise HTTPException(status_code=400, detail=f"场景 '{name}' 已存在")

    folder_name = body.folder_name or f"scene_{body.category,}_{body.subcategory}"

    if db.query(Scene).filter(Scene.folder_name == folder_name).first():
        raise HTTPException(status_code=400, detail=f"目录名 '{folder_name}' 已存在")

    # 创建文件目录
    scene_dir = IMAGE_DIR / folder_name
    scene_dir.mkdir(parents=True, exist_ok=True)

    scene = Scene(
        category=body.category,
        subcategory=body.subcategory,
        name=name,
        folder_name=folder_name,
        sort_order=body.sort_order,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)

    return SceneOut(
        id=scene.id, category=scene.category, subcategory=scene.subcategory,
        name=scene.name, folder_name=scene.folder_name, sort_order=scene.sort_order,
        image_count=0, pair_count=0,
    )


@router.put("/scenes/{scene_id}", response_model=SceneOut)
async def update_scene(
    scene_id: int,
    body: SceneUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    scene = db.query(Scene).filter(Scene.id == scene_id).first()
    if not scene:
        raise HTTPException(status_code=404, detail="场景不存在")

    if body.category is not None:
        scene.category = body.category
    if body.subcategory is not None:
        scene.subcategory = body.subcategory
    if body.sort_order is not None:
        scene.sort_order = body.sort_order

    # 重新拼接 name
    scene.name = f"{scene.category}-{scene.subcategory}"

    # 检查 name 唯一性（排除自身）
    existing = db.query(Scene).filter(Scene.name == scene.name, Scene.id != scene_id).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"场景名 '{scene.name}' 已被其他场景使用")

    db.commit()
    db.refresh(scene)

    image_count = db.query(Image).filter(Image.scene_id == scene.id).count()
    pair_count = db.query(ImagePair).filter(ImagePair.scene_id == scene.id).count()

    return SceneOut(
        id=scene.id, category=scene.category, subcategory=scene.subcategory,
        name=scene.name, folder_name=scene.folder_name, sort_order=scene.sort_order,
        image_count=image_count, pair_count=pair_count,
    )


# ==================== 设备管理 ====================

def _generate_device_folder(name: str) -> str:
    """从设备名称生成 folder_name"""
    import re
    folder = name.replace(" ", "_")
    folder = re.sub(r'[^a-zA-Z0-9_\-]', '', folder)
    return f"device_{folder}" if folder else "device_unknown"


@router.get("/devices", response_model=list[DeviceModelOut])
async def get_devices(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    devices = db.query(DeviceModel).all()
    result = []
    for d in devices:
        image_count = db.query(Image).filter(Image.device_id == d.id).count()
        result.append(DeviceModelOut(
            id=d.id, name=d.name, folder_name=d.folder_name,
            main_chip=d.main_chip or "", lens_model=d.lens_model or "",
            sensor_model=d.sensor_model or "", aperture=d.aperture or "",
            focal_length=d.focal_length or "", resolution=d.resolution or "",
            frame_rate=d.frame_rate or "", white_led=d.white_led or "",
            ir_led=d.ir_led or "", housing_info=d.housing_info or "",
            device_attrs=d.device_attrs or {}, features=d.features or "",
            image_count=image_count,
        ))
    return result


@router.post("/devices", response_model=DeviceModelOut)
async def create_device(
    body: DeviceModelCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(DeviceModel).filter(DeviceModel.name == body.name).first():
        raise HTTPException(status_code=400, detail=f"设备 '{body.name}' 已存在")

    folder_name = _generate_device_folder(body.name)

    if db.query(DeviceModel).filter(DeviceModel.folder_name == folder_name).first():
        raise HTTPException(status_code=400, detail=f"目录名 '{folder_name}' 已存在")

    device = DeviceModel(
        name=body.name,
        folder_name=folder_name,
        main_chip=body.main_chip,
        lens_model=body.lens_model,
        sensor_model=body.sensor_model,
        aperture=body.aperture,
        focal_length=body.focal_length,
        resolution=body.resolution,
        frame_rate=body.frame_rate,
        white_led=body.white_led,
        ir_led=body.ir_led,
        housing_info=body.housing_info,
        device_attrs=body.device_attrs or {},
        features=body.features or "",
    )
    db.add(device)
    db.commit()
    db.refresh(device)

    return DeviceModelOut(
        id=device.id, name=device.name, folder_name=device.folder_name,
        main_chip=device.main_chip or "", lens_model=device.lens_model or "",
        sensor_model=device.sensor_model or "", aperture=device.aperture or "",
        focal_length=device.focal_length or "", resolution=device.resolution or "",
        frame_rate=device.frame_rate or "", white_led=device.white_led or "",
        ir_led=device.ir_led or "", housing_info=device.housing_info or "",
        device_attrs=device.device_attrs or {}, features=device.features or "",
        image_count=0,
    )


@router.put("/devices/{device_id}", response_model=DeviceModelOut)
async def update_device(
    device_id: int,
    body: DeviceModelUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    if body.name is not None:
        existing = db.query(DeviceModel).filter(
            DeviceModel.name == body.name, DeviceModel.id != device_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"设备名 '{body.name}' 已被使用")
        device.name = body.name
        device.folder_name = _generate_device_folder(body.name)

    for field in ["main_chip", "lens_model", "sensor_model", "aperture", "focal_length",
                   "resolution", "frame_rate", "white_led", "ir_led", "housing_info", "features"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(device, field, val)

    if body.device_attrs is not None:
        device.device_attrs = body.device_attrs

    db.commit()
    db.refresh(device)

    image_count = db.query(Image).filter(Image.device_id == device.id).count()

    return DeviceModelOut(
        id=device.id, name=device.name, folder_name=device.folder_name,
        main_chip=device.main_chip or "", lens_model=device.lens_model or "",
        sensor_model=device.sensor_model or "", aperture=device.aperture or "",
        focal_length=device.focal_length or "", resolution=device.resolution or "",
        frame_rate=device.frame_rate or "", white_led=device.white_led or "",
        ir_led=device.ir_led or "", housing_info=device.housing_info or "",
        device_attrs=device.device_attrs or {}, features=device.features or "",
        image_count=image_count,
    )


# ==================== 概览统计 ====================

@router.get("/overview")
async def get_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    from ..services.stats_service import get_overview as _get_overview
    return _get_overview(db)
