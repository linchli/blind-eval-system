"""
管理路由：场景/机型 CRUD
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


# ==================== 机型管理 ====================

def _generate_model_folder(name: str) -> str:
    """从机型名称生成 folder_name"""
    import re
    folder = name.replace(" ", "_")
    folder = re.sub(r'[^a-zA-Z0-9_\-]', '', folder)
    return f"model_{folder}" if folder else "model_unknown"


@router.get("/models", response_model=list[DeviceModelOut])
async def get_models(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    models = db.query(DeviceModel).all()
    result = []
    for m in models:
        image_count = db.query(Image).filter(Image.model_id == m.id).count()
        result.append(DeviceModelOut(
            id=m.id, name=m.name, folder_name=m.folder_name,
            main_chip=m.main_chip or "", lens_model=m.lens_model or "",
            sensor_model=m.sensor_model or "", aperture=m.aperture or "",
            focal_length=m.focal_length or "", resolution=m.resolution or "",
            frame_rate=m.frame_rate or "", white_led=m.white_led or "",
            ir_led=m.ir_led or "", housing_info=m.housing_info or "",
            device_attrs=m.device_attrs or {}, features=m.features or "",
            image_count=image_count,
        ))
    return result


@router.post("/models", response_model=DeviceModelOut)
async def create_model(
    body: DeviceModelCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.query(DeviceModel).filter(DeviceModel.name == body.name).first():
        raise HTTPException(status_code=400, detail=f"机型 '{body.name}' 已存在")

    folder_name = _generate_model_folder(body.name)

    if db.query(DeviceModel).filter(DeviceModel.folder_name == folder_name).first():
        raise HTTPException(status_code=400, detail=f"目录名 '{folder_name}' 已存在")

    model = DeviceModel(
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
    db.add(model)
    db.commit()
    db.refresh(model)

    return DeviceModelOut(
        id=model.id, name=model.name, folder_name=model.folder_name,
        main_chip=model.main_chip or "", lens_model=model.lens_model or "",
        sensor_model=model.sensor_model or "", aperture=model.aperture or "",
        focal_length=model.focal_length or "", resolution=model.resolution or "",
        frame_rate=model.frame_rate or "", white_led=model.white_led or "",
        ir_led=model.ir_led or "", housing_info=model.housing_info or "",
        device_attrs=model.device_attrs or {}, features=model.features or "",
        image_count=0,
    )


@router.put("/models/{model_id}", response_model=DeviceModelOut)
async def update_model(
    model_id: int,
    body: DeviceModelUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    model = db.query(DeviceModel).filter(DeviceModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="机型不存在")

    if body.name is not None:
        existing = db.query(DeviceModel).filter(
            DeviceModel.name == body.name, DeviceModel.id != model_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"机型名 '{body.name}' 已被使用")
        model.name = body.name
        model.folder_name = _generate_model_folder(body.name)

    for field in ["main_chip", "lens_model", "sensor_model", "aperture", "focal_length",
                   "resolution", "frame_rate", "white_led", "ir_led", "housing_info", "features"]:
        val = getattr(body, field, None)
        if val is not None:
            setattr(model, field, val)

    if body.device_attrs is not None:
        model.device_attrs = body.device_attrs

    db.commit()
    db.refresh(model)

    image_count = db.query(Image).filter(Image.model_id == model.id).count()

    return DeviceModelOut(
        id=model.id, name=model.name, folder_name=model.folder_name,
        main_chip=model.main_chip or "", lens_model=model.lens_model or "",
        sensor_model=model.sensor_model or "", aperture=model.aperture or "",
        focal_length=model.focal_length or "", resolution=model.resolution or "",
        frame_rate=model.frame_rate or "", white_led=model.white_led or "",
        ir_led=model.ir_led or "", housing_info=model.housing_info or "",
        device_attrs=model.device_attrs or {}, features=model.features or "",
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
