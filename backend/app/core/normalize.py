"""
数据标准化工具函数

确保所有设备参数、场景名称等字段在存储时格式统一，
避免大小写不一致、前后空格等问题导致的查询和去重异常。
"""
from __future__ import annotations


def normalize_upper(value: str | None) -> str:
    """标准化为大写：strip 去空格 + upper 转大写"""
    if not value:
        return ""
    return value.strip().upper()


def normalize_strip(value: str | None) -> str:
    """仅 strip 去空格（不转大小写）"""
    if not value:
        return ""
    return value.strip()


def normalize_device_fields(data: dict) -> dict:
    """标准化设备字段（就地修改并返回）

    - 主控型号、镜头型号、Sensor、焦距、分辨率：strip + upper
    - 设备名、光圈、帧率、灯珠、壳体：strip
    """
    # strip + upper 字段
    upper_fields = ["main_chip", "lens_model", "sensor_model", "focal_length", "resolution"]
    for field in upper_fields:
        if field in data and isinstance(data[field], str):
            data[field] = normalize_upper(data[field])

    # 仅 strip 字段
    strip_fields = ["name", "aperture", "frame_rate", "white_led", "ir_led", "housing_info"]
    for field in strip_fields:
        if field in data and isinstance(data[field], str):
            data[field] = normalize_strip(data[field])

    return data


def normalize_scene_category_fields(data: dict) -> dict:
    """标准化场景大类字段"""
    if "name" in data and isinstance(data["name"], str):
        data["name"] = normalize_strip(data["name"])
    if "location" in data and isinstance(data["location"], str):
        data["location"] = normalize_strip(data["location"])
    return data


def normalize_scene_subcategory_fields(data: dict) -> dict:
    """标准化场景子类字段"""
    if "name" in data and isinstance(data["name"], str):
        data["name"] = normalize_strip(data["name"])
    return data
