"""
机型相关 Pydantic 模型
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional


class DeviceModelCreate(BaseModel):
    name: str
    main_chip: str = ""
    lens_model: str = ""
    sensor_model: str = ""
    aperture: str = ""
    focal_length: str = ""
    resolution: str = ""
    frame_rate: str = ""
    white_led: str = ""
    ir_led: str = ""
    housing_info: str = ""
    device_attrs: dict = {}
    features: str = ""


class DeviceModelUpdate(BaseModel):
    name: Optional[str] = None
    main_chip: Optional[str] = None
    lens_model: Optional[str] = None
    sensor_model: Optional[str] = None
    aperture: Optional[str] = None
    focal_length: Optional[str] = None
    resolution: Optional[str] = None
    frame_rate: Optional[str] = None
    white_led: Optional[str] = None
    ir_led: Optional[str] = None
    housing_info: Optional[str] = None
    device_attrs: Optional[dict] = None
    features: Optional[str] = None


class DeviceModelOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    id: int
    name: str
    folder_name: str
    main_chip: str = ""
    lens_model: str = ""
    sensor_model: str = ""
    aperture: str = ""
    focal_length: str = ""
    resolution: str = ""
    frame_rate: str = ""
    white_led: str = ""
    ir_led: str = ""
    housing_info: str = ""
    device_attrs: dict = {}
    features: str = ""
    image_count: int = 0
