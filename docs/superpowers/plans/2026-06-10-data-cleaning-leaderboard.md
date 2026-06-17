# 数据清洗与排行榜功能实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `clean_and_stats` 模块迁移到主后端，重写数据清洗功能，并新增设备排行榜功能

**Architecture:** 后端采用三层架构（API → Service → Model），清洗算法从 `clean_and_stats` 迁移并适配主库 ORM，排行榜数据持久化到 `leaderboard_ranking` 表。前端新增 DataCleaning 和 Leaderboard 两个页面，使用 ECharts 展示图表。

**Tech Stack:** FastAPI + SQLAlchemy + MySQL (后端), Vue 3 + Pinia + ECharts (前端)

**Note:** 实施过程中不进行 git 操作，所有任务完成后统一提交。

---

## 文件结构

### 后端新增/修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/leaderboard.py` | 新增 | leaderboard_ranking ORM 模型 |
| `backend/app/models/evaluation.py` | 修改 | 新增 is_valid, reject_type, reject_detail 字段 |
| `backend/app/schemas/cleaning.py` | 重写 | 清洗请求/响应模型 |
| `backend/app/schemas/leaderboard.py` | 新增 | 排行榜数据模型 |
| `backend/app/services/cleaning_service.py` | 重写 | 合并 cleaner.py + statistics.py |
| `backend/app/services/leaderboard_service.py` | 新增 | 排行榜计算 + 数据库存储 |
| `backend/app/api/cleaning.py` | 重写 | 数据清洗 API |
| `backend/app/api/leaderboard.py` | 新增 | 排行榜 API |
| `backend/app/core/config.py` | 修改 | 新增清洗参数默认值 |
| `backend/main.py` | 修改 | 注册新路由 |
| `backend/requirements.txt` | 修改 | 新增 scipy 依赖 |

### 前端新增/修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `frontend/src/views/admin/DataCleaning.vue` | 新增 | 数据清洗页面 |
| `frontend/src/views/admin/Leaderboard.vue` | 新增 | 排行榜页面（共享组件） |
| `frontend/src/views/admin/AdminOverview.vue` | 修改 | 新增入口卡片 |
| `frontend/src/views/admin/AdminLayout.vue` | 修改 | 侧边栏新增菜单项 |
| `frontend/src/router/index.js` | 修改 | 新增路由 |
| `frontend/src/api/index.js` | 修改 | 新增 API 函数 |
| `frontend/package.json` | 修改 | 新增 echarts, vue-echarts |

### 源文件迁移映射

| 源文件 (clean_and_stats) | 目标文件 (backend) | 说明 |
|--------------------------|-------------------|------|
| `app/service/cleaner.py` | `app/services/cleaning_service.py` | 完整迁移 |
| `app/service/statistics.py` | `app/services/cleaning_service.py` | 合并 |
| `app/core/config.py` | `app/core/config.py` | 合并清洗参数 |
| `app/models/schemas.py` | `app/schemas/cleaning.py` | 重写适配主库 |

---

## Task 1: 数据库模型 - evaluations 表新增字段

**Files:**
- Modify: `backend/app/models/evaluation.py`

- [ ] **Step 1: 修改 Evaluation 模型，新增清洗相关字段**

在 `Evaluation` 类中新增三个字段：

```python
# 在 Evaluation 类的 comment 字段之后添加
is_valid = Column(SmallInteger, default=1, comment="清洗后是否有效 1=有效 0=无效")
reject_type = Column(String(50), nullable=True, comment="拒绝类型: retest_reliability/group_consensus/insufficient_retest")
reject_detail = Column(JSON, nullable=True, comment="拒绝详情")
```

---

## Task 2: 数据库模型 - leaderboard_ranking 表

**Files:**
- Create: `backend/app/models/leaderboard.py`

- [ ] **Step 1: 创建 LeaderboardRanking ORM 模型**

```python
"""
排行榜排名 ORM 模型
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, UniqueConstraint, Index
from sqlalchemy.sql import func

from ..core.database import Base


class LeaderboardRanking(Base):
    __tablename__ = "leaderboard_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 筛选维度
    filter_type = Column(String(50), nullable=False, comment="筛选类型: overall/category/location/subcategory/scene/chip/sensor/focal_length/resolution")
    filter_value = Column(String(200), nullable=True, comment="筛选值")

    # 设备基础信息
    device_id = Column(Integer, nullable=False, index=True)
    device_name = Column(String(100))

    # 高频筛选字段
    main_chip = Column(String(100))
    sensor_model = Column(String(100))
    focal_length = Column(String(50))
    resolution = Column(String(50))

    # 扩展属性
    device_attrs = Column(JSON, comment="设备扩展属性")

    # 得分
    bt_score = Column(Float, comment="BT得分")
    mean_score = Column(Float, comment="评分均值")
    rank_position = Column(Integer, comment="排名")

    # 分场景得分
    scene_scores = Column(JSON, comment='分场景得分 {"场景名": {"bt_score": xx, "mean_score": xx, "eval_count": xx}, ...}')

    # 管理员详细数据
    detail_data = Column(JSON, comment="详细评测数据")

    # 元数据
    total_devices = Column(Integer, nullable=False, default=0, comment="参评设备数")
    cleaned_record_count = Column(Integer, nullable=False, default=0, comment="清洗时有效记录数")
    last_cleaned_at = Column(DateTime, nullable=False, comment="最后清洗时间")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("filter_type", "filter_value", "device_id", name="uk_filter_device"),
        Index("idx_rank", "filter_type", "filter_value", "rank_position"),
        Index("idx_lb_device", "device_id"),
    )
```

- [ ] **Step 2: 在 models/__init__.py 中导出新模型**

检查 `backend/app/models/__init__.py` 并添加 `LeaderboardRanking` 的导出。

---

## Task 3: 后端配置 - 清洗参数默认值

**Files:**
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: 在 config.py 中添加清洗参数默认值**

在文件末尾添加：

```python
# ==================== 数据清洗参数 ====================
# 单用户一致性 (加权 Agreement)
SINGLE_USER_CORRELATION_THRESHOLD = 0.70  # agreement_score >= 此值 → 通过
SINGLE_USER_HARD_REJECT_AGREEMENT = 0.55  # agreement_score < 此值 → 直接拒绝

# 用户组一致性
GROUP_MAX_THRESHOLD = 0.85  # 动态阈值上限
GROUP_MIN_THRESHOLD = 0.55  # 动态阈值下限

# 数据量下限
MIN_DEVICES_PER_SCENE = 2  # 场景内至少需要 2 个设备才能计算相关系数

# 复评比例要求
RETEST_RATIO = 0.10  # 复评对数占总对数的最低比例
```

---

## Task 4: 后端 Schema - 数据清洗模型

**Files:**
- Rewrite: `backend/app/schemas/cleaning.py`

- [ ] **Step 1: 重写 cleaning.py schema 文件**

```python
"""
数据清洗相关 Pydantic 模型
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── 枚举 ──────────────────────────────────────────────────────────────────────

class RejectType(str, Enum):
    """拒绝类型"""
    RETEST_RELIABILITY = "retest_reliability"
    GROUP_CONSENSUS = "group_consensus"
    INSUFFICIENT_RETEST = "insufficient_retest"


# ── 清洗参数 ──────────────────────────────────────────────────────────────────

class CleaningParams(BaseModel):
    """清洗参数配置"""
    retest_agreement_threshold: float = Field(0.70, ge=0.50, le=0.90, description="重测一致性阈值")
    retest_hard_reject_threshold: float = Field(0.55, ge=0.30, le=0.70, description="重测硬拒绝阈值")
    group_max_threshold: float = Field(0.85, ge=0.60, le=1.00, description="用户组最大阈值")
    retest_ratio: float = Field(0.10, ge=0.05, le=0.30, description="复评比例要求")
    min_devices_per_scene: int = Field(2, ge=2, le=10, description="最小设备数")


# ── 输入记录 ──────────────────────────────────────────────────────────────────

class EvalRecord(BaseModel):
    """单条盲评记录 — 清洗必需字段"""
    eval_id: int = Field(..., description="evaluations.id")
    user_id: int = Field(..., description="evaluations.user_id")
    pair_id: int = Field(..., description="evaluations.pair_id")
    session_id: Optional[int] = Field(None, description="evaluations.session_id")
    scene_id: int = Field(..., description="image_pairs.scene_id")
    device_a_id: int = Field(..., description="image_pairs.device_a_id (通过 image_a.device_id)")
    device_b_id: int = Field(..., description="image_pairs.device_b_id (通过 image_b.device_id)")
    score_a: float = Field(..., ge=0.0, le=2.0, description="设备 A 得分 0~2")
    score_b: float = Field(..., ge=0.0, le=2.0, description="设备 B 得分 0~2")


# ── 清洗详情 ──────────────────────────────────────────────────────────────────

class RetestSceneDetail(BaseModel):
    """单场景重测信度详情 — 字段名与设计文档一致"""
    scene_id: int
    scene_name: str = ""
    retest_agreement_score: float = Field(..., description="加权一致性得分 [0,1]")
    retest_agreement_threshold: float = Field(..., description="一致性阈值")
    retest_hard_reject_threshold: float = Field(0.55, description="硬拒绝阈值")
    rejected: bool
    retest_matched_pairs: int = Field(..., description="原始与复评匹配的图对数")


class UserGroupSceneDetail(BaseModel):
    """用户组一致性 - 单场景详情"""
    scene_id: int
    scene_name: str = ""
    total_user_scenes: int = 0
    passed: int = 0
    rejected: int = 0


# ── 请求体 ────────────────────────────────────────────────────────────────────

class CleaningExecuteRequest(BaseModel):
    """执行数据清洗请求"""
    params: CleaningParams = Field(default_factory=CleaningParams)


# ── 响应体 ────────────────────────────────────────────────────────────────────

class CleaningStatusResponse(BaseModel):
    """清洗状态响应"""
    has_cleaned: bool = False
    last_cleaned_at: Optional[str] = None
    cleaned_record_count: int = 0
    current_record_count: int = 0
    new_record_count: int = 0
    needs_refresh: bool = False


class CleaningExecuteResponse(BaseModel):
    """清洗执行结果"""
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    single_user_details: dict[str, Any] = Field(default_factory=dict)
    user_group_details: dict[str, Any] = Field(default_factory=dict)
    leaderboard_updated: bool = False


class ApiResponse(BaseModel):
    """统一响应包装"""
    code: int = 0
    message: str = "ok"
    data: Optional[Any] = None
```

---

## Task 5: 后端 Schema - 排行榜模型

**Files:**
- Create: `backend/app/schemas/leaderboard.py`

- [ ] **Step 1: 创建排行榜 schema 文件**

```python
"""
排行榜相关 Pydantic 模型
"""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class SceneScore(BaseModel):
    """分场景得分"""
    bt_score: float = 0.0
    mean_score: float = 0.0
    eval_count: int = 0


class RankingItem(BaseModel):
    """排行榜单项"""
    rank: int
    device_id: int
    device_name: str = ""
    main_chip: str = ""
    sensor_model: str = ""
    focal_length: str = ""
    resolution: str = ""
    bt_score: float = 0.0
    mean_score: float = 0.0
    bt_rank: int = 0
    mean_rank: int = 0
    rank_diff: int = 0
    scene_scores: dict[str, SceneScore] = Field(default_factory=dict)


class FilterInfo(BaseModel):
    """筛选信息"""
    type: str
    value: Optional[str] = None


class LeaderboardResponse(BaseModel):
    """排行榜响应"""
    ranking: list[RankingItem] = Field(default_factory=list)
    filter_info: FilterInfo = Field(default_factory=lambda: FilterInfo(type="overall"))
    total_devices: int = 0
    last_updated: Optional[str] = None


class FilterOptions(BaseModel):
    """筛选选项"""
    categories: list[dict[str, Any]] = Field(default_factory=list)
    subcategories: list[dict[str, Any]] = Field(default_factory=list)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    chips: list[str] = Field(default_factory=list)
    sensors: list[str] = Field(default_factory=list)
    focal_lengths: list[str] = Field(default_factory=list)
    resolutions: list[str] = Field(default_factory=list)


class DeviceRankingDetail(BaseModel):
    """设备排名详情"""
    rank: int
    device_id: int
    device_name: str = ""
    eval_count: int = 0
    mean_score: float = 0.0
    bt_strength: float = 0.0
    bt_rank: int = 0
    mean_rank: int = 0
    rank_diff: int = 0


class SceneDetailResponse(BaseModel):
    """场景详情响应"""
    view_type: str = "scene"
    scene: dict[str, Any] = Field(default_factory=dict)
    device_ranking: list[DeviceRankingDetail] = Field(default_factory=list)
    invalid_users_by_scene: list[dict[str, Any]] = Field(default_factory=list)


class UserDetailResponse(BaseModel):
    """用户详情响应"""
    view_type: str = "user"
    user: dict[str, Any] = Field(default_factory=dict)
    scene_details: list[dict[str, Any]] = Field(default_factory=list)


class DeviceDetailResponse(BaseModel):
    """设备详情响应"""
    view_type: str = "device"
    device: dict[str, Any] = Field(default_factory=dict)
    scenes: list[dict[str, Any]] = Field(default_factory=list)
```

---

## Task 6: 后端服务 - 数据清洗服务（迁移 clean_and_stats）

**Files:**
- Rewrite: `backend/app/services/cleaning_service.py`

- [ ] **Step 1: 重写 cleaning_service.py，迁移 clean_and_stats 的算法**

这是核心任务，需要将 `clean_and_stats/app/service/statistics.py` 和 `clean_and_stats/app/service/cleaner.py` 的逻辑合并到主后端。

关键迁移点：
1. `statistics.py` 中的 `bradley_terry`、`pearson_correlation`、`weighted_agreement_for_pair`、`scene_weighted_agreement` 等函数
2. `cleaner.py` 中的 `clean_single_user_consistency`、`clean_user_group_consistency` 等函数
3. 命名映射：`model_id` → `device_id`，`model_a_id` → `device_a_id`

```python
"""
数据清洗服务 — 合并自 clean_and_stats 的 cleaner.py + statistics.py

包含：
1. 单用户一致性检验（重测信度）- 加权 Agreement
2. 用户组一致性检验 - log BT Pearson r
3. Bradley-Terry 模型计算
4. 统计工具函数
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from ..models.evaluation import Evaluation
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.scene import Scene
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.device_model import DeviceModel
from ..schemas.cleaning import (
    CleaningParams,
    EvalRecord,
    RetestSceneDetail,
    UserGroupSceneDetail,
    RejectType,
)
from ..core import config

# 尝试导入 scipy，如果不可用则使用纯 Python 实现
try:
    from scipy.stats import pearsonr as scipy_pearsonr
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ═══════════════════════════════════════════════════════════════════════════════
# 统计工具函数
# ═══════════════════════════════════════════════════════════════════════════════

def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))


def pearson_correlation(x: list[float], y: list[float], min_devices: int = 2) -> Optional[float]:
    """Pearson 相关系数。返回 None 表示数据不足或方差为零。"""
    if len(x) < min_devices or len(y) < min_devices:
        return None
    if len(x) != len(y):
        return None

    x_std = _std(x)
    y_std = _std(y)
    if x_std == 0.0 or y_std == 0.0:
        return None

    if HAS_SCIPY:
        r, _ = scipy_pearsonr(x, y)
        return float(r)
    else:
        # 纯 Python 实现
        n = len(x)
        mx, my = _mean(x), _mean(y)
        cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
        denom = (sum((v - mx) ** 2 for v in x) * sum((v - my) ** 2 for v in y)) ** 0.5
        if denom == 0:
            return None
        return cov / denom


def bradley_terry(
    records: list[EvalRecord],
    scene_id: int | None = None,
    max_iter: int = 1000,
    tol: float = 1e-6,
) -> dict[int, float]:
    """
    Bradley-Terry 模型强度估计 (MM 算法)。

    映射: score_a > score_b → A 胜; score_a < score_b → B 胜; 相等 → 平局 (各计 0.5 胜)。
    返回 {device_id: strength}, 几何均值归一化为 1。
    """
    recs = [r for r in records if scene_id is None or r.scene_id == scene_id]

    wins: dict[int, float] = defaultdict(float)
    pair_counts: dict[tuple[int, int], int] = defaultdict(int)

    for r in recs:
        a, b = r.device_a_id, r.device_b_id
        pair_counts[(min(a, b), max(a, b))] += 1

        if r.score_a > r.score_b:
            wins[a] += 1.0
        elif r.score_b > r.score_a:
            wins[b] += 1.0
        else:
            wins[a] += 0.5
            wins[b] += 0.5

    device_ids = sorted(set(
        d for r in recs for d in (r.device_a_id, r.device_b_id)
    ))
    n = len(device_ids)
    if n < 2:
        return {d: 1.0 for d in device_ids}

    theta = {d: 1.0 for d in device_ids}

    for _ in range(max_iter):
        new_theta = {}
        for i in device_ids:
            denominator = 0.0
            for j in device_ids:
                if i == j:
                    continue
                n_ij = pair_counts.get((min(i, j), max(i, j)), 0)
                if n_ij > 0:
                    denominator += n_ij / (theta[i] + theta[j])
            if denominator > 0:
                new_theta[i] = wins[i] / denominator
            else:
                new_theta[i] = 0.0

        log_sum = sum(math.log(max(t, 1e-12)) for t in new_theta.values() if t > 0)
        if log_sum == 0:
            break
        norm = math.exp(log_sum / n)
        for d in device_ids:
            new_theta[d] /= norm

        max_diff = max(abs(new_theta[d] - theta[d]) for d in device_ids)
        theta = new_theta
        if max_diff < tol:
            break

    return dict(theta)


# ── 加权 Agreement 相关 ──────────────────────────────────────────────────────

def _to_judgment_level(score_a: float, score_b: float) -> int:
    """将原始评分映射为 5 级判定方向"""
    if score_a == 2 and score_b == 0:
        return +2
    if score_a == 1 and score_b == 0:
        return +1
    if score_a == 0.5 and score_b == 0.5:
        return 0
    if score_a == 0 and score_b == 1:
        return -1
    if score_a == 0 and score_b == 2:
        return -2
    diff = score_a - score_b
    if diff > 0:
        return min(int(diff), 2)
    elif diff < 0:
        return max(int(diff), -2)
    return 0


_JUDGMENT_WEIGHTS = [
    # retest:  -2     -1      0     +1     +2
    [ 1.00,  0.70,  0.20, -0.30, -1.00],  # orig -2
    [ 0.70,  1.00,  0.50, -0.30, -0.60],  # orig -1
    [ 0.20,  0.50,  1.00,  0.50,  0.20],  # orig  0
    [-0.60, -0.30,  0.50,  1.00,  0.70],  # orig +1
    [-1.00, -0.60,  0.20,  0.70,  1.00],  # orig +2
]


def weighted_agreement_for_pair(
    score_a_orig: float, score_b_orig: float,
    score_a_retest: float, score_b_retest: float,
) -> float:
    """对单个复评对计算加权一致性得分, 范围 [-1, +1]"""
    d_orig = _to_judgment_level(score_a_orig, score_b_orig)
    d_retest = _to_judgment_level(score_a_retest, score_b_retest)
    return _JUDGMENT_WEIGHTS[d_orig + 2][d_retest + 2]


def scene_weighted_agreement(
    orig_records: list[EvalRecord],
    retest_records: list[EvalRecord],
) -> tuple[float, int]:
    """逐对匹配原始和复评记录, 计算场景级加权一致性得分。"""
    orig_by_pair = {r.pair_id: r for r in orig_records}
    retest_by_pair = {r.pair_id: r for r in retest_records}

    weights = []
    for pair_id, orig_r in orig_by_pair.items():
        retest_r = retest_by_pair.get(pair_id)
        if retest_r is None:
            continue
        w = weighted_agreement_for_pair(
            orig_r.score_a, orig_r.score_b,
            retest_r.score_a, retest_r.score_b,
        )
        weights.append(w)

    if not weights:
        return 0.0, 0

    mean_w = sum(weights) / len(weights)
    return (mean_w + 1.0) / 2.0, len(weights)


# ═══════════════════════════════════════════════════════════════════════════════
# 数据加载
# ═══════════════════════════════════════════════════════════════════════════════

def load_eval_records(db: Session) -> list[EvalRecord]:
    """从数据库加载所有 submitted 状态的评测记录，转换为 EvalRecord

    使用 JOIN 一次性获取所有数据，避免 N+1 查询问题。
    """
    # 创建 Image 表的别名用于 JOIN image_b
    from sqlalchemy.orm import aliased
    ImageA = aliased(Image, name="image_a")
    ImageB = aliased(Image, name="image_b")

    rows = (
        db.query(
            Evaluation.id.label("eval_id"),
            Evaluation.user_id,
            Evaluation.pair_id,
            Evaluation.session_id,
            Evaluation.score_a,
            Evaluation.score_b,
            Evaluation.is_repeat,
            ImagePair.scene_id,
            ImageA.device_id.label("device_a_id"),
            ImageB.device_id.label("device_b_id"),
        )
        .join(ImagePair, Evaluation.pair_id == ImagePair.id)
        .join(ImageA, ImagePair.image_a_id == ImageA.id)
        .join(ImageB, ImagePair.image_b_id == ImageB.id)
        .filter(Evaluation.status == "submitted")
        .all()
    )

    records = []
    for row in rows:
        records.append(EvalRecord(
            eval_id=row.eval_id,
            user_id=row.user_id,
            pair_id=row.pair_id,
            session_id=row.session_id,
            scene_id=row.scene_id,
            device_a_id=row.device_a_id,
            device_b_id=row.device_b_id,
            score_a=row.score_a,
            score_b=row.score_b,
        ))

    return records


# ═══════════════════════════════════════════════════════════════════════════════
# 单用户一致性检验（重测信度）
# ═══════════════════════════════════════════════════════════════════════════════

def split_retest_pairs(
    data: list[EvalRecord],
) -> tuple[list[EvalRecord], list[EvalRecord], int]:
    """分离原始评分和复评数据"""
    groups: dict[tuple[int, int], list[EvalRecord]] = defaultdict(list)
    for r in data:
        groups[(r.user_id, r.pair_id)].append(r)

    original: list[EvalRecord] = []
    retest: list[EvalRecord] = []
    retest_count = 0

    for (uid, pid), recs in groups.items():
        recs.sort(key=lambda r: r.eval_id)
        original.append(recs[0])
        if len(recs) >= 2:
            retest_count += 1
            retest.append(recs[1])
        for r in recs[2:]:
            retest.append(r)

    return original, retest, retest_count


def clean_single_user_consistency(
    data: list[EvalRecord],
    params: CleaningParams,
    scene_names: dict[int, str],
) -> dict:
    """
    重测信度检验 (单用户自评一致性) — 加权 Agreement。

    返回: {user_id: {scene_details: [...], rejected_eval_ids: [...]}}
    """
    result = {}
    user_groups: dict[int, list[EvalRecord]] = defaultdict(list)
    for r in data:
        user_groups[r.user_id].append(r)

    for user_id, user_data in user_groups.items():
        original, retest, retest_count = split_retest_pairs(user_data)
        total_pairs = len({(r.user_id, r.pair_id) for r in user_data})
        required_retest = int(total_pairs * params.retest_ratio)

        scene_details = []
        rejected_scenes = set()

        if retest_count < required_retest:
            # 复评数据不足 — 标记所有场景为拒绝，使用 insufficient_retest 类型
            result[user_id] = {
                "scene_details": [],
                "rejected_scenes": {r.scene_id for r in user_data},
                "insufficient_retest": True,
                "retest_info": {
                    "retest_count": retest_count,
                    "total_pairs": total_pairs,
                    "required_retest": required_retest,
                },
            }
            continue  # 跳过后续逐场景计算
        else:
            # 逐场景计算加权 Agreement
            original_by_scene: dict[int, list[EvalRecord]] = defaultdict(list)
            retest_by_scene: dict[int, list[EvalRecord]] = defaultdict(list)
            for r in original:
                original_by_scene[r.scene_id].append(r)
            for r in retest:
                retest_by_scene[r.scene_id].append(r)

            all_scenes = sorted(set(original_by_scene.keys()) | set(retest_by_scene.keys()))

            for scene_id in all_scenes:
                orig_recs = original_by_scene.get(scene_id, [])
                retest_recs = retest_by_scene.get(scene_id, [])
                agreement_score, matched_pairs = scene_weighted_agreement(orig_recs, retest_recs)

                if matched_pairs == 0:
                    rejected = True
                elif agreement_score >= params.retest_agreement_threshold:
                    rejected = False
                elif agreement_score < params.retest_hard_reject_threshold:
                    rejected = True
                else:
                    rejected = True  # 灰色地带

                scene_details.append(RetestSceneDetail(
                    scene_id=scene_id,
                    scene_name=scene_names.get(scene_id, f"场景{scene_id}"),
                    retest_agreement_score=round(agreement_score, 4),
                    retest_agreement_threshold=params.retest_agreement_threshold,
                    retest_hard_reject_threshold=params.retest_hard_reject_threshold,
                    rejected=rejected,
                    retest_matched_pairs=matched_pairs,
                ))

                if rejected:
                    rejected_scenes.add(scene_id)

        result[user_id] = {
            "scene_details": [d.model_dump() for d in scene_details],
            "rejected_scenes": rejected_scenes,
        }

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# 用户组一致性检验
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize_scores(data: list[EvalRecord]) -> list[EvalRecord]:
    """评分归一化: score > 1.0 → 1.0"""
    for r in data:
        if r.score_a > 1.0:
            r.score_a = 1.0
        if r.score_b > 1.0:
            r.score_b = 1.0
    return data


def clean_user_group_consistency(
    data: list[EvalRecord],
    params: CleaningParams,
    scene_names: dict[int, str],
) -> dict:
    """
    用户组一致性检验 (逐场景) — log B-T 强度 + Pearson r。

    返回: {scene_id: {details: [...], scene_stats: {...}}}
    """
    # 剔除复评数据
    groups: dict[tuple[int, int], list[EvalRecord]] = defaultdict(list)
    for r in data:
        groups[(r.user_id, r.pair_id)].append(r)

    original_data = []
    for recs in groups.values():
        recs.sort(key=lambda r: r.eval_id)
        original_data.append(recs[0])

    original_data = _normalize_scores(original_data)

    # 按 scene 分组
    all_by_scene: dict[int, list[EvalRecord]] = defaultdict(list)
    for r in original_data:
        all_by_scene[r.scene_id].append(r)

    user_scene_index: dict[tuple[int, int], list[EvalRecord]] = defaultdict(list)
    for r in original_data:
        user_scene_index[(r.user_id, r.scene_id)].append(r)

    user_scenes = set(user_scene_index.keys())

    # 计算所有 (user, scene) 的 log-B-T Pearson r
    r_results: dict[tuple[int, int], float] = {}

    for (user_id, scene_id) in sorted(user_scenes):
        user_recs = user_scene_index[(user_id, scene_id)]
        user_bt = bradley_terry(user_recs, scene_id=scene_id)
        group_recs = [r for r in all_by_scene.get(scene_id, []) if r.user_id != user_id]
        group_bt = bradley_terry(group_recs, scene_id=scene_id)

        common = sorted(set(user_bt) & set(group_bt))
        if len(common) < params.min_devices_per_scene:
            r_results[(user_id, scene_id)] = 0.0
            continue

        x = [math.log(max(user_bt[m], 1e-12)) for m in common]
        y = [math.log(max(group_bt[m], 1e-12)) for m in common]
        r_val = pearson_correlation(x, y, params.min_devices_per_scene)
        r_results[(user_id, scene_id)] = r_val if r_val is not None else 0.0

    # 动态阈值
    scene_r_list: dict[int, list[float]] = defaultdict(list)
    for (uid, sid), r_val in r_results.items():
        scene_r_list[sid].append(r_val)

    scene_thresholds: dict[int, float] = {}
    for sid, r_vals in scene_r_list.items():
        raw = _mean(r_vals) - _std(r_vals)
        scene_thresholds[sid] = min(raw, params.group_max_threshold)

    # 判定
    rejected_by_scene: dict[int, set[int]] = defaultdict(set)  # scene_id -> rejected user_ids
    scene_stats = {}

    for (user_id, scene_id) in sorted(user_scenes):
        r_val = r_results[(user_id, scene_id)]
        dyn_threshold = scene_thresholds.get(scene_id, params.group_max_threshold)
        rejected = (r_val < dyn_threshold)

        if rejected:
            rejected_by_scene[scene_id].add(user_id)

    # 统计
    for scene_id in all_by_scene:
        total = len(set(r.user_id for r in all_by_scene[scene_id]))
        rejected_count = len(rejected_by_scene.get(scene_id, set()))
        scene_stats[scene_id] = {
            "scene_name": scene_names.get(scene_id, f"场景{scene_id}"),
            "total_user_scenes": total,
            "passed": total - rejected_count,
            "rejected": rejected_count,
        }

    return {
        "rejected_by_scene": rejected_by_scene,
        "scene_stats": scene_stats,
        "r_results": r_results,  # 供 reject_detail 使用
        "scene_thresholds": scene_thresholds,  # 供 reject_detail 使用
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 主清洗流程
# ═══════════════════════════════════════════════════════════════════════════════

def execute_cleaning(db: Session, params: CleaningParams) -> dict:
    """
    执行完整的数据清洗流程。

    1. 加载数据
    2. 单用户一致性检验
    3. 用户组一致性检验
    4. 更新 evaluations 表
    5. 返回清洗结果
    """
    # 加载数据
    records = load_eval_records(db)
    scene_names = get_scene_names(db)

    if not records:
        return {
            "total_records": 0,
            "valid_records": 0,
            "invalid_records": 0,
            "single_user_details": {},
            "user_group_details": {},
            "leaderboard_updated": False,
        }

    total_records = len(records)

    # 第一步：单用户一致性检验
    single_user_result = clean_single_user_consistency(records, params, scene_names)

    # 收集被拒绝的 eval_id
    invalid_eval_ids = set()
    for user_id, user_result in single_user_result.items():
        for scene_id in user_result["rejected_scenes"]:
            for r in records:
                if r.user_id == user_id and r.scene_id == scene_id:
                    invalid_eval_ids.add(r.eval_id)

    # 第二步：用户组一致性检验（仅对通过单用户检验的数据）
    valid_for_group = [r for r in records if r.eval_id not in invalid_eval_ids]
    group_result = clean_user_group_consistency(valid_for_group, params, scene_names)

    # 收集用户组拒绝的 eval_id
    for scene_id, rejected_users in group_result["rejected_by_scene"].items():
        for r in valid_for_group:
            if r.user_id in rejected_users and r.scene_id == scene_id:
                invalid_eval_ids.add(r.eval_id)

    # 第三步：更新 evaluations 表
    _update_evaluations(db, records, invalid_eval_ids, single_user_result, group_result, scene_names)

    valid_records = total_records - len(invalid_eval_ids)

    # 格式化单用户详情
    single_user_details = {}
    for user_id, user_result in single_user_result.items():
        single_user_details[str(user_id)] = {
            "scene_details": user_result["scene_details"]
        }

    # 格式化用户组详情
    user_group_details = {}
    for scene_id, stats in group_result["scene_stats"].items():
        user_group_details[str(scene_id)] = stats

    return {
        "total_records": total_records,
        "valid_records": valid_records,
        "invalid_records": len(invalid_eval_ids),
        "single_user_details": single_user_details,
        "user_group_details": user_group_details,
        "leaderboard_updated": True,
    }


def get_scene_names(db: Session) -> dict[int, str]:
    """获取所有场景名称映射"""
    scenes = (
        db.query(
            Scene.id,
            SceneCategory.name.label("cat_name"),
            SceneCategory.location,
            SceneSubcategory.name.label("sub_name"),
        )
        .join(SceneCategory, Scene.category_id == SceneCategory.id)
        .join(SceneSubcategory, Scene.subcategory_id == SceneSubcategory.id)
        .all()
    )
    result = {}
    for s in scenes:
        cat_part = s.cat_name
        if s.location:
            cat_part = f"{cat_part}({s.location})"
        name = f"{cat_part}-{s.sub_name}" if s.sub_name else cat_part
        result[s.id] = name
    return result


def _update_evaluations(
    db: Session,
    records: list[EvalRecord],
    invalid_eval_ids: set[int],
    single_user_result: dict,
    group_result: dict,
    scene_names: dict[int, str],
) -> None:
    """更新 evaluations 表的清洗结果"""
    # 构建 reject_detail — 按设计文档格式
    user_scene_reject_info: dict[tuple[int, int], dict] = {}

    # 单用户拒绝信息 — 设计文档格式
    for user_id, user_result in single_user_result.items():
        # 复评数据不足 — 全局拒绝，使用 insufficient_retest 类型
        if user_result.get("insufficient_retest"):
            retest_info = user_result.get("retest_info", {})
            for sid in user_result["rejected_scenes"]:
                user_scene_reject_info[(user_id, sid)] = {
                    "type": RejectType.INSUFFICIENT_RETEST.value,
                    "detail": {
                        "retest_count": retest_info.get("retest_count", 0),
                        "total_pairs": retest_info.get("total_pairs", 0),
                        "required_retest": retest_info.get("required_retest", 0),
                    },
                }
        else:
            # 重测信度不通过 — 逐场景拒绝
            for scene_detail in user_result["scene_details"]:
                if scene_detail.get("rejected"):
                    sid = scene_detail["scene_id"]
                    user_scene_reject_info[(user_id, sid)] = {
                        "type": RejectType.RETEST_RELIABILITY.value,
                        "detail": {
                            "scene_id": sid,
                            "scene_name": scene_names.get(sid, f"场景{sid}"),
                            "retest_agreement_score": scene_detail.get("retest_agreement_score", 0),
                            "retest_agreement_threshold": scene_detail.get("retest_agreement_threshold", 0),
                            "retest_hard_reject_threshold": scene_detail.get("retest_hard_reject_threshold", 0.55),
                            "retest_matched_pairs": scene_detail.get("retest_matched_pairs", 0),
                        },
                    }

    # 用户组拒绝信息 — 设计文档格式（含 group_pearson_r 和 group_dynamic_threshold）
    for scene_id, rejected_users in group_result["rejected_by_scene"].items():
        for user_id in rejected_users:
            if (user_id, scene_id) not in user_scene_reject_info:
                r_val = group_result.get("r_results", {}).get((user_id, scene_id), 0.0)
                dyn_threshold = group_result.get("scene_thresholds", {}).get(scene_id, 0.0)
                user_scene_reject_info[(user_id, scene_id)] = {
                    "type": RejectType.GROUP_CONSENSUS.value,
                    "detail": {
                        "scene_id": scene_id,
                        "scene_name": scene_names.get(scene_id, f"场景{scene_id}"),
                        "group_pearson_r": round(r_val, 4),
                        "group_dynamic_threshold": round(dyn_threshold, 4),
                    },
                }

    # 批量更新
    for r in records:
        is_valid = 0 if r.eval_id in invalid_eval_ids else 1
        reject_type = None
        reject_detail = None

        if not is_valid:
            info = user_scene_reject_info.get((r.user_id, r.scene_id))
            if info:
                reject_type = info["type"]
                reject_detail = info["detail"]

        db.query(Evaluation).filter(Evaluation.id == r.eval_id).update({
            "is_valid": is_valid,
            "reject_type": reject_type,
            "reject_detail": reject_detail,
        })

    db.commit()


def get_cleaning_status(db: Session) -> dict:
    """获取清洗状态"""
    # 检查是否有已清洗的数据
    cleaned = db.query(Evaluation).filter(Evaluation.is_valid.isnot(None)).first()
    has_cleaned = cleaned is not None

    # 获取最后清洗时间
    last_cleaned_at = None
    cleaned_record_count = 0
    if has_cleaned:
        last_eval = (
            db.query(Evaluation)
            .filter(Evaluation.is_valid.isnot(None))
            .order_by(Evaluation.submitted_at.desc())
            .first()
        )
        if last_eval and last_eval.submitted_at:
            last_cleaned_at = last_eval.submitted_at.isoformat()
        cleaned_record_count = db.query(Evaluation).filter(Evaluation.is_valid.isnot(None)).count()

    # 当前记录数
    current_record_count = db.query(Evaluation).filter(Evaluation.status == "submitted").count()

    # 新记录数（未清洗的）
    new_record_count = db.query(Evaluation).filter(
        Evaluation.status == "submitted",
        Evaluation.is_valid.is_(None),
    ).count()

    return {
        "has_cleaned": has_cleaned,
        "last_cleaned_at": last_cleaned_at,
        "cleaned_record_count": cleaned_record_count,
        "current_record_count": current_record_count,
        "new_record_count": new_record_count,
        "needs_refresh": new_record_count > 0,
    }


def export_cleaning_report(db: Session) -> str:
    """导出清洗报告为文本"""
    # 获取所有无效记录
    invalid_records = (
        db.query(Evaluation)
        .filter(Evaluation.is_valid == 0)
        .all()
    )

    lines = [
        "=" * 60,
        "数据清洗报告",
        "=" * 60,
        "",
        f"无效记录总数: {len(invalid_records)}",
        "",
        "-" * 60,
        "无效记录详情:",
        "-" * 60,
    ]

    for rec in invalid_records:
        lines.append(
            f"评测ID: {rec.id} | 用户ID: {rec.user_id} | "
            f"拒绝类型: {rec.reject_type or 'N/A'} | "
            f"详情: {rec.reject_detail or 'N/A'}"
        )

    lines.extend(["", "=" * 60, "报告结束"])
    return "\n".join(lines)
```

---

## Task 7: 后端服务 - 排行榜服务

**Files:**
- Create: `backend/app/services/leaderboard_service.py`

- [ ] **Step 1: 创建排行榜服务**

```python
"""
排行榜服务 — 计算 BT 得分、评分均值，生成筛选组合，写入数据库
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from ..models.evaluation import Evaluation
from ..models.image_pair import ImagePair
from ..models.image import Image
from ..models.scene import Scene
from ..models.scene_category import SceneCategory
from ..models.scene_subcategory import SceneSubcategory
from ..models.device_model import DeviceModel
from ..models.leaderboard import LeaderboardRanking
from ..services.cleaning_service import bradley_terry, EvalRecord, get_scene_names
from ..core import config


def load_valid_records(db: Session) -> list[EvalRecord]:
    """加载所有有效评测记录

    使用 JOIN 一次性获取所有数据，避免 N+1 查询问题。
    """
    from sqlalchemy.orm import aliased
    ImageA = aliased(Image, name="image_a")
    ImageB = aliased(Image, name="image_b")

    rows = (
        db.query(
            Evaluation.id.label("eval_id"),
            Evaluation.user_id,
            Evaluation.pair_id,
            Evaluation.session_id,
            Evaluation.score_a,
            Evaluation.score_b,
            ImagePair.scene_id,
            ImageA.device_id.label("device_a_id"),
            ImageB.device_id.label("device_b_id"),
        )
        .join(ImagePair, Evaluation.pair_id == ImagePair.id)
        .join(ImageA, ImagePair.image_a_id == ImageA.id)
        .join(ImageB, ImagePair.image_b_id == ImageB.id)
        .filter(Evaluation.status == "submitted")
        .filter(Evaluation.is_valid == 1)
        .all()
    )

    records = []
    for row in rows:
        records.append(EvalRecord(
            eval_id=row.eval_id,
            user_id=row.user_id,
            pair_id=row.pair_id,
            session_id=row.session_id,
            scene_id=row.scene_id,
            device_a_id=row.device_a_id,
            device_b_id=row.device_b_id,
            score_a=row.score_a,
            score_b=row.score_b,
        ))

    return records


def compute_leaderboard(db: Session) -> dict:
    """
    计算排行榜数据并写入数据库。

    1. 加载有效数据
    2. 计算 BT 得分（整体 + 分场景）
    3. 计算评分均值
    4. 生成筛选组合
    5. 写入 leaderboard_ranking 表
    """
    records = load_valid_records(db)
    if not records:
        return {"total_devices": 0, "records_written": 0}

    scene_names = get_scene_names(db)
    devices = _get_devices(db)

    # 整体 BT 得分
    overall_bt = bradley_terry(records)
    max_bt = max(overall_bt.values()) if overall_bt else 1.0

    # 分场景 BT 得分
    scene_ids = {r.scene_id for r in records}
    scene_bt_scores = {}
    for sid in scene_ids:
        scene_bt = bradley_terry(records, scene_id=sid)
        scene_bt_scores[sid] = scene_bt

    # 计算评分均值
    device_scores = _compute_mean_scores(records)

    # 分场景评分均值
    scene_mean_scores = {}
    for sid in scene_ids:
        scene_records = [r for r in records if r.scene_id == sid]
        scene_mean_scores[sid] = _compute_mean_scores(scene_records)

    # 分场景评测次数
    scene_eval_counts = defaultdict(lambda: defaultdict(int))
    for r in records:
        scene_eval_counts[r.scene_id][r.device_a_id] += 1
        scene_eval_counts[r.scene_id][r.device_b_id] += 1

    # 生成筛选组合并写入
    now = datetime.now()
    total_devices = len(devices)
    cleaned_record_count = len(records)

    # 清空旧数据
    db.query(LeaderboardRanking).delete()

    # 生成所有筛选组合
    filter_combinations = _generate_filter_combinations(db)

    records_written = 0
    for filter_type, filter_value, filtered_scene_ids in filter_combinations:
        # 根据筛选条件过滤记录
        if filtered_scene_ids is None:
            filtered_records = records
            filtered_scene_bt = overall_bt
        else:
            filtered_records = [r for r in records if r.scene_id in filtered_scene_ids]
            if not filtered_records:
                continue
            filtered_scene_bt = bradley_terry(filtered_records)

        if not filtered_scene_bt:
            continue

        max_filtered_bt = max(filtered_scene_bt.values()) if filtered_scene_bt else 1.0
        filtered_mean_scores = _compute_mean_scores(filtered_records)

        # 排名
        sorted_devices = sorted(
            filtered_scene_bt.keys(),
            key=lambda d: -filtered_scene_bt.get(d, 0)
        )

        for rank_pos, device_id in enumerate(sorted_devices, 1):
            device = devices.get(device_id)
            if not device:
                continue

            bt_score = (filtered_scene_bt.get(device_id, 0) / max_filtered_bt) * 100 if max_filtered_bt > 0 else 0
            mean_score = filtered_mean_scores.get(device_id, 0)

            # 分场景得分
            dev_scene_scores = {}
            for sid in scene_ids:
                if sid in scene_bt_scores and device_id in scene_bt_scores[sid]:
                    sid_bt = scene_bt_scores[sid]
                    max_sid_bt = max(sid_bt.values()) if sid_bt else 1.0
                    dev_scene_scores[scene_names.get(sid, f"场景{sid}")] = {
                        "bt_score": round((sid_bt.get(device_id, 0) / max_sid_bt) * 100, 1) if max_sid_bt > 0 else 0,
                        "mean_score": round(scene_mean_scores.get(sid, {}).get(device_id, 0), 1),
                        "eval_count": scene_eval_counts.get(sid, {}).get(device_id, 0),
                    }

            # 计算 BT 排名和均值排名
            bt_ranked = sorted(filtered_scene_bt.keys(), key=lambda d: -filtered_scene_bt.get(d, 0))
            mean_ranked = sorted(filtered_mean_scores.keys(), key=lambda d: -filtered_mean_scores.get(d, 0))

            bt_rank = bt_ranked.index(device_id) + 1 if device_id in bt_ranked else 0
            mean_rank = mean_ranked.index(device_id) + 1 if device_id in mean_ranked else 0

            ranking = LeaderboardRanking(
                filter_type=filter_type,
                filter_value=filter_value,
                device_id=device_id,
                device_name=device.name,
                main_chip=device.main_chip or "",
                sensor_model=device.sensor_model or "",
                focal_length=device.focal_length or "",
                resolution=device.resolution or "",
                device_attrs=device.device_attrs,
                bt_score=round(bt_score, 2),
                mean_score=round(mean_score, 2),
                rank_position=rank_pos,
                scene_scores=dev_scene_scores,
                total_devices=total_devices,
                cleaned_record_count=cleaned_record_count,
                last_cleaned_at=now,
            )
            db.add(ranking)
            records_written += 1

    db.commit()

    return {
        "total_devices": total_devices,
        "records_written": records_written,
    }


def _compute_mean_scores(records: list[EvalRecord]) -> dict[int, float]:
    """计算每个设备的评分均值"""
    scores = defaultdict(list)
    for r in records:
        scores[r.device_a_id].append(r.score_a)
        scores[r.device_b_id].append(r.score_b)
    return {d: sum(s) / len(s) for d, s in scores.items()}


def _get_devices(db: Session) -> dict[int, DeviceModel]:
    """获取所有设备"""
    devices = db.query(DeviceModel).all()
    return {d.id: d for d in devices}


def _generate_filter_combinations(db: Session) -> list[tuple[str, Optional[str], Optional[set[int]]]]:
    """
    生成所有筛选组合。

    返回: [(filter_type, filter_value, scene_ids_or_None), ...]
    scene_ids_or_None 为 None 表示使用所有场景
    """
    combinations = []

    # overall
    combinations.append(("overall", None, None))

    # category
    categories = db.query(SceneCategory).all()
    for cat in categories:
        scene_ids = {s.id for s in db.query(Scene).filter(Scene.category_id == cat.id).all()}
        if scene_ids:
            combinations.append(("category", cat.name, scene_ids))

    # location
    locations = {cat.location for cat in categories if cat.location}
    for loc in locations:
        scene_ids = {s.id for s in db.query(Scene).join(SceneCategory).filter(SceneCategory.location == loc).all()}
        if scene_ids:
            combinations.append(("location", loc, scene_ids))

    # subcategory
    subcategories = db.query(SceneSubcategory).all()
    for sub in subcategories:
        scene_ids = {s.id for s in db.query(Scene).filter(Scene.subcategory_id == sub.id).all()}
        if scene_ids:
            combinations.append(("subcategory", sub.name, scene_ids))

    # scene
    scenes = db.query(Scene).all()
    for scene in scenes:
        combinations.append(("scene", str(scene.id), {scene.id}))

    # chip
    chips = {d.main_chip for d in db.query(DeviceModel).all() if d.main_chip}
    for chip in chips:
        combinations.append(("chip", chip, None))

    # sensor
    sensors = {d.sensor_model for d in db.query(DeviceModel).all() if d.sensor_model}
    for sensor in sensors:
        combinations.append(("sensor", sensor, None))

    # focal_length
    focal_lengths = {d.focal_length for d in db.query(DeviceModel).all() if d.focal_length}
    for fl in focal_lengths:
        combinations.append(("focal_length", fl, None))

    # resolution
    resolutions = {d.resolution for d in db.query(DeviceModel).all() if d.resolution}
    for res in resolutions:
        combinations.append(("resolution", res, None))

    return combinations


def get_leaderboard(db: Session, filter_type: str, filter_value: Optional[str], score_type: str) -> dict:
    """获取排行榜数据"""
    query = db.query(LeaderboardRanking).filter(
        LeaderboardRanking.filter_type == filter_type,
    )

    if filter_value is not None:
        query = query.filter(LeaderboardRanking.filter_value == filter_value)
    else:
        query = query.filter(LeaderboardRanking.filter_value.is_(None))

    if score_type == "mean":
        query = query.order_by(LeaderboardRanking.mean_score.desc())
    else:
        query = query.order_by(LeaderboardRanking.rank_position.asc())

    rankings = query.all()

    ranking_list = []

    # 计算 BT 排名和均值排名（分别排序）
    bt_ranked_ids = [r.device_id for r in sorted(rankings, key=lambda x: -(x.bt_score or 0))]
    mean_ranked_ids = [r.device_id for r in sorted(rankings, key=lambda x: -(x.mean_score or 0))]

    for r in rankings:
        bt_rank = bt_ranked_ids.index(r.device_id) + 1 if r.device_id in bt_ranked_ids else 0
        mean_rank = mean_ranked_ids.index(r.device_id) + 1 if r.device_id in mean_ranked_ids else 0

        ranking_list.append({
            "rank": r.rank_position,
            "device_id": r.device_id,
            "device_name": r.device_name or "",
            "main_chip": r.main_chip or "",
            "sensor_model": r.sensor_model or "",
            "focal_length": r.focal_length or "",
            "resolution": r.resolution or "",
            "bt_score": r.bt_score or 0,
            "mean_score": r.mean_score or 0,
            "bt_rank": bt_rank,
            "mean_rank": mean_rank,
            "rank_diff": bt_rank - mean_rank,
            "scene_scores": r.scene_scores or {},
        })

    # 获取最后更新时间
    last_updated = None
    if rankings:
        last_updated = rankings[0].last_cleaned_at.isoformat() if rankings[0].last_cleaned_at else None

    return {
        "ranking": ranking_list,
        "filter_info": {"type": filter_type, "value": filter_value},
        "total_devices": rankings[0].total_devices if rankings else 0,
        "last_updated": last_updated,
    }


def get_filter_options(db: Session) -> dict:
    """获取可用的筛选选项"""
    categories = db.query(SceneCategory).all()
    subcategories = db.query(SceneSubcategory).all()
    scenes = db.query(Scene).all()

    # 提取唯一的地点列表
    locations = sorted({c.location for c in categories if c.location})

    chips = sorted({d.main_chip for d in db.query(DeviceModel).all() if d.main_chip})
    sensors = sorted({d.sensor_model for d in db.query(DeviceModel).all() if d.sensor_model})
    focal_lengths = sorted({d.focal_length for d in db.query(DeviceModel).all() if d.focal_length})
    resolutions = sorted({d.resolution for d in db.query(DeviceModel).all() if d.resolution})

    # 构建场景名称映射
    scene_names = get_scene_names(db)

    return {
        "categories": [{"id": c.id, "name": c.name, "location": c.location} for c in categories],
        "subcategories": [{"id": s.id, "name": s.name} for s in subcategories],
        "scenes": [{"id": s.id, "name": scene_names.get(s.id, f"场景{s.id}")} for s in scenes],
        "locations": locations,
        "chips": chips,
        "sensors": sensors,
        "focal_lengths": focal_lengths,
        "resolutions": resolutions,
    }


def get_leaderboard_details(db: Session, view_type: str, id: int) -> dict:
    """获取详细评测数据（管理员权限）"""
    scene_names = get_scene_names(db)

    if view_type == "scene":
        return _get_scene_details(db, id, scene_names)
    elif view_type == "user":
        return _get_user_details(db, id, scene_names)
    elif view_type == "device":
        return _get_device_details(db, id, scene_names)
    else:
        return {"view_type": view_type, "error": "不支持的视图类型"}


def _get_scene_details(db: Session, scene_id: int, scene_names: dict) -> dict:
    """获取场景详情"""
    # 场景统计
    total = db.query(Evaluation).join(ImagePair).filter(ImagePair.scene_id == scene_id).count()
    valid = db.query(Evaluation).join(ImagePair).filter(
        ImagePair.scene_id == scene_id, Evaluation.is_valid == 1
    ).count()
    invalid = db.query(Evaluation).join(ImagePair).filter(
        ImagePair.scene_id == scene_id, Evaluation.is_valid == 0
    ).count()

    # 无效用户
    invalid_users = (
        db.query(Evaluation.user_id)
        .join(ImagePair)
        .filter(ImagePair.scene_id == scene_id, Evaluation.is_valid == 0)
        .distinct()
        .all()
    )
    invalid_user_ids = [u[0] for u in invalid_users]

    # 设备排名（从排行榜表获取）
    rankings = (
        db.query(LeaderboardRanking)
        .filter(LeaderboardRanking.filter_type == "scene")
        .filter(LeaderboardRanking.filter_value == str(scene_id))
        .order_by(LeaderboardRanking.rank_position.asc())
        .all()
    )

    device_ranking = []
    for r in rankings:
        device_ranking.append({
            "rank": r.rank_position,
            "device_id": r.device_id,
            "device_name": r.device_name or "",
            "eval_count": r.cleaned_record_count,
            "mean_score": r.mean_score or 0,
            "bt_strength": r.bt_score or 0,
            "bt_rank": r.rank_position,
            "mean_rank": r.rank_position,
            "rank_diff": 0,
        })

    return {
        "view_type": "scene",
        "scene": {
            "id": scene_id,
            "name": scene_names.get(scene_id, f"场景{scene_id}"),
            "total_records": total,
            "valid_records": valid,
            "invalid_records": invalid,
            "invalid_users": invalid_user_ids,
        },
        "device_ranking": device_ranking,
        "invalid_users_by_scene": [],
    }


def _get_user_details(db: Session, user_id: int, scene_names: dict) -> dict:
    """获取用户详情"""
    # 用户统计
    total_evals = db.query(Evaluation).filter(Evaluation.user_id == user_id).count()
    first_evals = db.query(Evaluation).filter(
        Evaluation.user_id == user_id, Evaluation.is_repeat == 0
    ).count()
    retest_evals = db.query(Evaluation).filter(
        Evaluation.user_id == user_id, Evaluation.is_repeat == 1
    ).count()

    # 各场景一致性 - 从 evaluations 表查询实际清洗结果
    scene_details = []
    scenes = db.query(Scene).all()

    # 统计通过和拒绝的场景数
    passed_scenes = 0
    rejected_scenes = 0

    for scene in scenes:
        eval_count = (
            db.query(Evaluation)
            .join(ImagePair)
            .filter(Evaluation.user_id == user_id, ImagePair.scene_id == scene.id)
            .count()
        )
        if eval_count > 0:
            # 查询该用户在该场景的拒绝记录
            rejected_eval = (
                db.query(Evaluation)
                .join(ImagePair)
                .filter(
                    Evaluation.user_id == user_id,
                    ImagePair.scene_id == scene.id,
                    Evaluation.is_valid == 0,
                )
                .first()
            )

            is_passed = rejected_eval is None
            if is_passed:
                passed_scenes += 1
            else:
                rejected_scenes += 1

            # 从 reject_detail 中提取清洗指标
            retest_agreement_score = 0.0
            retest_agreement_threshold = 0.70
            if rejected_eval and rejected_eval.reject_detail:
                detail = rejected_eval.reject_detail
                retest_agreement_score = detail.get("retest_agreement_score", 0.0)
                retest_agreement_threshold = detail.get("retest_agreement_threshold", 0.70)

            scene_details.append({
                "scene_id": scene.id,
                "scene_name": scene_names.get(scene.id, f"场景{scene.id}"),
                "eval_count": eval_count,
                "retest_agreement_score": retest_agreement_score,
                "retest_agreement_threshold": retest_agreement_threshold,
                "passed": is_passed,
            })

    return {
        "view_type": "user",
        "user": {
            "id": user_id,
            "total_evals": total_evals,
            "first_evals": first_evals,
            "retest_evals": retest_evals,
            "retest_rate": retest_evals / total_evals if total_evals > 0 else 0,
            "passed_scenes": passed_scenes,
            "rejected_scenes": rejected_scenes,
            "pass_rate": passed_scenes / (passed_scenes + rejected_scenes) if (passed_scenes + rejected_scenes) > 0 else 1.0,
        },
        "scene_details": scene_details,
    }


def _get_device_details(db: Session, device_id: int, scene_names: dict) -> dict:
    """获取设备详情"""
    device = db.query(DeviceModel).filter(DeviceModel.id == device_id).first()
    if not device:
        return {"view_type": "device", "device": {}, "scenes": []}

    # 分场景得分
    rankings = (
        db.query(LeaderboardRanking)
        .filter(LeaderboardRanking.filter_type == "scene")
        .filter(LeaderboardRanking.device_id == device_id)
        .all()
    )

    scenes = []
    for r in rankings:
        scenes.append({
            "scene_id": int(r.filter_value) if r.filter_value else 0,
            "scene_name": scene_names.get(int(r.filter_value), f"场景{r.filter_value}") if r.filter_value else "",
            "bt_score": r.bt_score or 0,
            "mean_score": r.mean_score or 0,
            "eval_count": r.cleaned_record_count,
        })

    return {
        "view_type": "device",
        "device": {
            "id": device.id,
            "name": device.name,
        },
        "scenes": scenes,
    }


def export_leaderboard(db: Session, export_type: str, filter_type: str, filter_value: Optional[str]) -> str:
    """导出排行榜数据"""
    if export_type == "ranking":
        data = get_leaderboard(db, filter_type, filter_value, "bt")
        lines = [
            "=" * 60,
            f"排行榜数据 - 筛选: {filter_type}={filter_value or '全部'}",
            "=" * 60,
            "",
            f"{'排名':<6}{'设备名':<20}{'主芯片':<15}{'Sensor':<10}{'BT得分':<10}{'均值':<10}",
            "-" * 70,
        ]
        for item in data["ranking"]:
            lines.append(
                f"{item['rank']:<6}{item['device_name']:<20}{item['main_chip']:<15}"
                f"{item['sensor_model']:<10}{item['bt_score']:<10}{item['mean_score']:<10}"
            )
        return "\n".join(lines)
    elif export_type == "detail":
        # 导出详细数据
        scene_names = get_scene_names(db)
        lines = [
            "=" * 60,
            "详细评测数据",
            "=" * 60,
            "",
        ]

        # 按场景导出
        scenes = db.query(Scene).all()
        for scene in scenes:
            scene_name = scene_names.get(scene.id, f"场景{scene.id}")
            lines.append(f"场景: {scene_name}")
            lines.append("-" * 40)

            # 获取该场景的设备排名
            rankings = (
                db.query(LeaderboardRanking)
                .filter(LeaderboardRanking.filter_type == "scene")
                .filter(LeaderboardRanking.filter_value == str(scene.id))
                .order_by(LeaderboardRanking.rank_position.asc())
                .all()
            )

            if rankings:
                lines.append(f"{'排名':<6}{'设备名':<20}{'评测次数':<10}{'评分均值':<10}{'BT强度':<10}")
                lines.append("-" * 56)
                for r in rankings:
                    lines.append(
                        f"{r.rank_position:<6}{r.device_name or '':<20}"
                        f"{r.cleaned_record_count:<10}{r.mean_score or 0:<10.1f}{r.bt_score or 0:<10.2f}"
                    )
            else:
                lines.append("暂无数据")

            lines.append("")

        return "\n".join(lines)
    else:
        return "暂不支持此导出类型"
```

---

## Task 8: 后端 API - 数据清洗路由

**Files:**
- Rewrite: `backend/app/api/cleaning.py`

- [ ] **Step 1: 重写清洗 API 路由**

```python
"""
数据清洗 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import require_admin
from ..models.user import User
from ..schemas.cleaning import (
    CleaningExecuteRequest,
    CleaningExecuteResponse,
    CleaningStatusResponse,
    CleaningParams,
    ApiResponse,
)
from ..services.cleaning_service import execute_cleaning, get_cleaning_status, export_cleaning_report
from ..services.leaderboard_service import compute_leaderboard

router = APIRouter(prefix="/api/cleaning", tags=["数据清洗"])


@router.get("/defaults")
async def get_cleaning_defaults():
    """获取清洗参数默认值"""
    params = CleaningParams()
    return ApiResponse(data=params.model_dump())


@router.get("/status")
async def get_status(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取当前清洗状态"""
    status = get_cleaning_status(db)
    return ApiResponse(data=status)


@router.post("/execute")
async def execute(
    body: CleaningExecuteRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """执行数据清洗"""
    try:
        result = execute_cleaning(db, body.params)

        # 清洗完成后自动计算排行榜
        if result["total_records"] > 0:
            lb_result = compute_leaderboard(db)
            result["leaderboard_updated"] = True

        return ApiResponse(data=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清洗失败: {str(e)}")


@router.get("/export")
async def export_report(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """导出清洗报告"""
    report = export_cleaning_report(db)
    return PlainTextResponse(
        content=report,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=cleaning_report.txt"},
    )
```

---

## Task 9: 后端 API - 排行榜路由

**Files:**
- Create: `backend/app/api/leaderboard.py`

- [ ] **Step 1: 创建排行榜 API 路由**

```python
"""
排行榜 API 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..core.dependencies import get_current_user, require_admin, get_optional_user
from ..models.user import User
from ..schemas.leaderboard import (
    LeaderboardResponse,
    FilterOptions,
    SceneDetailResponse,
    UserDetailResponse,
    DeviceDetailResponse,
)
from ..schemas.cleaning import ApiResponse
from ..services.leaderboard_service import (
    get_leaderboard,
    get_filter_options,
    get_leaderboard_details,
    export_leaderboard,
)

router = APIRouter(prefix="/api/leaderboard", tags=["排行榜"])


@router.get("")
async def leaderboard(
    filter_type: str = Query("overall", description="筛选类型"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
    score_type: str = Query("bt", description="得分类型: bt/mean"),
    db: Session = Depends(get_db),
):
    """获取排行榜数据（无需登录）"""
    data = get_leaderboard(db, filter_type, filter_value, score_type)
    return ApiResponse(data=data)


@router.get("/filters")
async def filters(db: Session = Depends(get_db)):
    """获取可用的筛选选项（无需登录）"""
    data = get_filter_options(db)
    return ApiResponse(data=data)


@router.get("/details")
async def details(
    view_type: str = Query(..., description="视图类型: scene/user/device"),
    id: int = Query(..., description="具体 ID"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取详细评测数据（管理员权限）"""
    data = get_leaderboard_details(db, view_type, id)
    return ApiResponse(data=data)


@router.get("/export")
async def export_data(
    export_type: str = Query("ranking", description="导出类型: ranking/detail"),
    filter_type: str = Query("overall", description="筛选类型"),
    filter_value: Optional[str] = Query(None, description="筛选值"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """导出排行榜数据（管理员权限）"""
    content = export_leaderboard(db, export_type, filter_type, filter_value)
    return PlainTextResponse(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=leaderboard_export.txt"},
    )
```

---

## Task 10: 后端集成 - 注册路由和依赖

**Files:**
- Modify: `backend/main.py`
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 在 main.py 中注册新路由**

在 `app.include_router(batch_upload.router)` 之后添加：

```python
from app.api import cleaning, leaderboard

app.include_router(cleaning.router)
app.include_router(leaderboard.router)
```

- [ ] **Step 2: 确保 requirements.txt 包含 scipy**

检查 `backend/requirements.txt`，确保包含 `scipy` 依赖。如果没有，添加：

```
scipy>=1.10.0
```

---

## Task 11: 前端 - 安装 ECharts

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: 安装 ECharts 依赖**

```bash
cd frontend && npm install echarts vue-echarts
```

---

## Task 12: 前端 - API 函数

**Files:**
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: 添加数据清洗和排行榜 API 函数**

在文件末尾添加：

```javascript
// ==================== 数据清洗 ====================
export const apiGetCleaningDefaults = () => request('/api/cleaning/defaults')
export const apiGetCleaningStatus = () => request('/api/cleaning/status')
export const apiExecuteCleaning = (params) => request('/api/cleaning/execute', {
  method: 'POST',
  body: JSON.stringify({ params }),
})
export const apiExportCleaningReport = async () => {
  const token = localStorage.getItem('blind_eval_token')
  const resp = await fetch('/api/cleaning/export', {
    headers: { 'Authorization': `Bearer ${token}` },
  })
  if (!resp.ok) throw new Error('导出失败')
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'cleaning_report.txt'
  a.click()
  URL.revokeObjectURL(url)
}

// ==================== 排行榜 ====================
export const apiGetLeaderboard = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return request(`/api/leaderboard${query ? '?' + query : ''}`)
}
export const apiGetLeaderboardFilters = () => request('/api/leaderboard/filters')
export const apiGetLeaderboardDetails = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  return request(`/api/leaderboard/details?${query}`)
}
export const apiExportLeaderboard = (params = {}) => {
  const query = new URLSearchParams(params).toString()
  window.open(`/api/leaderboard/export?${query}`, '_blank')
}
```

---

## Task 13: 前端 - 路由配置

**Files:**
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: 添加新路由和公开页面配置**

```javascript
import DataCleaning from '../views/admin/DataCleaning.vue'
import Leaderboard from '../views/admin/Leaderboard.vue'

const routes = [
  // ... 现有路由 ...
  { path: '/ranking', name: 'Leaderboard', component: Leaderboard, meta: { public: true } },
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      // ... 现有子路由 ...
      { path: 'cleaning', name: 'DataCleaning', component: DataCleaning },
      { path: 'leaderboard', name: 'AdminLeaderboard', component: Leaderboard },
    ],
  },
]

// 修改路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('blind_eval_token')
  const publicPages = ['Login', 'Register', 'ResetPassword', 'Leaderboard']
  if (!publicPages.includes(to.name) && !token) {
    next({ name: 'Login' })
  } else {
    next()
  }
})
```

---

## Task 14: 前端 - 数据清洗页面

**Files:**
- Create: `frontend/src/views/admin/DataCleaning.vue`

- [ ] **Step 1: 创建数据清洗页面组件**

严格按照设计文档 6.7 节布局实现：

```vue
<template>
  <div class="data-cleaning-page">
    <h1 class="page-title">🧹 数据清洗</h1>

    <!-- 参数配置 + 状态面板 -->
    <div class="config-status-row">
      <!-- 清洗参数配置 -->
      <div class="config-panel">
        <h3 class="panel-title">清洗参数配置</h3>
        <div class="param-item">
          <label>重测一致性阈值：</label>
          <input type="range" v-model.number="params.retest_agreement_threshold" min="0.50" max="0.90" step="0.01" />
          <span class="param-value">{{ params.retest_agreement_threshold.toFixed(2) }}</span>
        </div>
        <div class="param-item">
          <label>重测硬拒绝阈值：</label>
          <input type="range" v-model.number="params.retest_hard_reject_threshold" min="0.30" max="0.70" step="0.01" />
          <span class="param-value">{{ params.retest_hard_reject_threshold.toFixed(2) }}</span>
        </div>
        <div class="param-item">
          <label>用户组最大阈值：</label>
          <input type="range" v-model.number="params.group_max_threshold" min="0.60" max="1.00" step="0.01" />
          <span class="param-value">{{ params.group_max_threshold.toFixed(2) }}</span>
        </div>
        <div class="param-item">
          <label>复评比例要求：</label>
          <input type="range" v-model.number="retestRatioPercent" min="5" max="30" step="1" />
          <span class="param-value">{{ retestRatioPercent }}%</span>
        </div>
        <div class="param-item">
          <label>最小设备数：</label>
          <input type="range" v-model.number="params.min_devices_per_scene" min="2" max="10" step="1" />
          <span class="param-value">{{ params.min_devices_per_scene }}</span>
        </div>
        <button class="btn-text" @click="resetDefaults">恢复默认值</button>
      </div>

      <!-- 清洗状态 -->
      <div class="status-panel">
        <h3 class="panel-title">清洗状态</h3>
        <div v-if="status.has_cleaned" class="status-info">
          <p>最后清洗时间：{{ formatTime(status.last_cleaned_at) }}</p>
          <p>清洗时记录数：{{ status.cleaned_record_count }}</p>
          <p>当前记录数：{{ status.current_record_count }}</p>
          <p v-if="status.needs_refresh" class="warning">⚠️ 有 {{ status.new_record_count }} 条新记录</p>
        </div>
        <div v-else class="status-info">
          <p>尚未执行过清洗</p>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <button class="btn-primary" @click="executeCleaning" :disabled="cleaning">
        {{ cleaning ? '清洗中...' : '执行数据清洗' }}
      </button>
      <button class="btn-outline" @click="exportReport" :disabled="!status.has_cleaned">
        导出清洗报告
      </button>
    </div>

    <!-- 清洗结果 -->
    <div v-if="result" class="result-section">
      <!-- 结果概要 -->
      <div class="result-summary">
        <span>总记录数：{{ result.total_records }}</span>
        <span>有效记录：{{ result.valid_records }}</span>
        <span>无效记录：{{ result.invalid_records }}</span>
      </div>

      <!-- 单用户一致性检验（重测信度） -->
      <div class="result-table-section">
        <h3>单用户一致性检验（重测信度）</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>用户</th>
              <th>场景</th>
              <th>一致性得分</th>
              <th>阈值</th>
              <th>状态</th>
              <th>重测对数</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(userData, userId) in result.single_user_details" :key="userId">
              <tr v-for="(detail, idx) in userData.scene_details" :key="`${userId}-${idx}`">
                <td>{{ userId }}</td>
                <td>{{ detail.scene_name }}</td>
                <td>{{ detail.retest_agreement_score?.toFixed(2) }}</td>
                <td>{{ detail.retest_agreement_threshold?.toFixed(2) }}</td>
                <td>
                  <span :class="detail.rejected ? 'status-reject' : 'status-pass'">
                    {{ detail.rejected ? '✗' : '✓' }}
                  </span>
                </td>
                <td>{{ detail.retest_matched_pairs }}</td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- 用户组一致性检验 -->
      <div class="result-table-section">
        <h3>用户组一致性检验</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>场景</th>
              <th>总用户场景</th>
              <th>通过</th>
              <th>拒绝</th>
              <th>通过率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(stats, sceneId) in result.user_group_details" :key="sceneId">
              <td>{{ stats.scene_name }}</td>
              <td>{{ stats.total_user_scenes }}</td>
              <td>{{ stats.passed }}</td>
              <td>{{ stats.rejected }}</td>
              <td>{{ stats.total_user_scenes > 0 ? ((stats.passed / stats.total_user_scenes) * 100).toFixed(1) + '%' : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { apiGetCleaningDefaults, apiGetCleaningStatus, apiExecuteCleaning, apiExportCleaningReport } from '../../api/index.js'

const defaultParams = {
  retest_agreement_threshold: 0.70,
  retest_hard_reject_threshold: 0.55,
  group_max_threshold: 0.85,
  retest_ratio: 0.10,
  min_devices_per_scene: 2,
}

const params = ref({ ...defaultParams })
const status = ref({})
const result = ref(null)
const cleaning = ref(false)

const retestRatioPercent = computed({
  get: () => Math.round(params.value.retest_ratio * 100),
  set: (v) => { params.value.retest_ratio = v / 100 },
})

function resetDefaults() {
  params.value = { ...defaultParams }
}

function formatTime(iso) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function fetchStatus() {
  try {
    const resp = await apiGetCleaningStatus()
    status.value = resp.data || {}
  } catch (e) {
    console.error('获取清洗状态失败:', e)
  }
}

async function fetchDefaults() {
  try {
    const resp = await apiGetCleaningDefaults()
    if (resp.data) {
      params.value = { ...defaultParams, ...resp.data }
    }
  } catch (e) {
    console.error('获取默认参数失败:', e)
  }
}

async function executeCleaning() {
  if (!confirm('确定要执行数据清洗吗？')) return
  cleaning.value = true
  try {
    const resp = await apiExecuteCleaning(params.value)
    result.value = resp.data
    window.showAdminToast?.('数据清洗完成', 'success')
    await fetchStatus()
  } catch (e) {
    window.showAdminToast?.('清洗失败: ' + e.message, 'error')
  } finally {
    cleaning.value = false
  }
}

function exportReport() {
  apiExportCleaningReport()
}

onMounted(() => {
  fetchDefaults()
  fetchStatus()
})
</script>

<style scoped>
.data-cleaning-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.config-status-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.config-panel, .status-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.param-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.param-item label {
  min-width: 140px;
  font-size: 14px;
  color: #475569;
}

.param-item input[type="range"] {
  flex: 1;
}

.param-value {
  min-width: 50px;
  text-align: right;
  font-weight: 600;
  color: #1e40af;
}

.btn-text {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  font-size: 13px;
  padding: 4px 0;
}

.btn-text:hover {
  text-decoration: underline;
}

.status-info p {
  margin: 8px 0;
  font-size: 14px;
  color: #475569;
}

.status-info .warning {
  color: #d97706;
  font-weight: 500;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.btn-primary {
  padding: 12px 24px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-outline {
  padding: 12px 24px;
  background: white;
  color: #3b82f6;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover:not(:disabled) {
  background: #eff6ff;
}

.btn-outline:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.result-summary {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: white;
  border-radius: 12px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.result-summary span {
  font-size: 14px;
  color: #475569;
}

.result-table-section {
  background: white;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.result-table-section h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.data-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #374151;
}

.data-table td {
  color: #475569;
}

.status-pass {
  color: #16a34a;
  font-weight: 600;
}

.status-reject {
  color: #dc2626;
  font-weight: 600;
}

@media (max-width: 768px) {
  .config-status-row {
    grid-template-columns: 1fr;
  }
  .action-bar {
    flex-direction: column;
  }
}
</style>
```

---

## Task 15: 前端 - 排行榜页面

**Files:**
- Create: `frontend/src/views/admin/Leaderboard.vue`

- [ ] **Step 1: 创建排行榜页面组件**

严格按照设计文档 6.8 节布局实现：

```vue
<template>
  <div class="leaderboard-page">
    <h1 class="page-title">🏆 设备排行榜</h1>

    <!-- 标签页（管理员可见两个 tab） -->
    <div class="tabs">
      <button :class="{ active: activeTab === 'ranking' }" @click="activeTab = 'ranking'">
        排行榜
      </button>
      <button v-if="authStore.isAdmin" :class="{ active: activeTab === 'detail' }" @click="activeTab = 'detail'">
        详细数据
      </button>
    </div>

    <!-- Tab 1: 排行榜 -->
    <div v-if="activeTab === 'ranking'">
      <!-- 筛选条件 -->
      <div class="filter-panel">
        <div class="filter-row">
          <div class="filter-item">
            <label>得分类型：</label>
            <select v-model="filters.score_type" @change="fetchLeaderboard">
              <option value="bt">BT得分</option>
              <option value="mean">评分均值</option>
            </select>
          </div>
          <div class="filter-item">
            <label>场景：</label>
            <select v-model="filters.scene" @change="onSceneChange">
              <option value="">全部场景</option>
              <option v-for="scene in filterOptions.scenes" :key="scene.id" :value="'scene:'+scene.id">
                {{ scene.name }}
              </option>
            </select>
          </div>
          <div class="filter-item">
            <label>大类：</label>
            <select v-model="filters.category" @change="onCategoryChange">
              <option value="">全部</option>
              <option v-for="cat in filterOptions.categories" :key="cat.id" :value="cat.name">
                {{ cat.name }}
              </option>
            </select>
          </div>
          <div class="filter-item">
            <label>地点：</label>
            <select v-model="filters.location" @change="onLocationChange">
              <option value="">全部</option>
              <option v-for="loc in filterOptions.locations" :key="loc" :value="loc">{{ loc }}</option>
            </select>
          </div>
          <div class="filter-item">
            <label>子类：</label>
            <select v-model="filters.subcategory" @change="onSubcategoryChange">
              <option value="">全部</option>
              <option v-for="sub in filterOptions.subcategories" :key="sub.id" :value="sub.name">
                {{ sub.name }}
              </option>
            </select>
          </div>
        </div>
        <div class="filter-row">
          <div class="filter-item">
            <label>主芯片：</label>
            <select v-model="filters.chip" @change="onChipChange">
              <option value="">全部</option>
              <option v-for="chip in filterOptions.chips" :key="chip" :value="chip">{{ chip }}</option>
            </select>
          </div>
          <div class="filter-item">
            <label>Sensor：</label>
            <select v-model="filters.sensor" @change="onSensorChange">
              <option value="">全部</option>
              <option v-for="s in filterOptions.sensors" :key="s" :value="s">{{ s }}</option>
            </select>
          </div>
          <div class="filter-item">
            <label>焦距：</label>
            <select v-model="filters.focal_length" @change="onFocalLengthChange">
              <option value="">全部</option>
              <option v-for="fl in filterOptions.focal_lengths" :key="fl" :value="fl">{{ fl }}</option>
            </select>
          </div>
          <div class="filter-item">
            <label>分辨率：</label>
            <select v-model="filters.resolution" @change="onResolutionChange">
              <option value="">全部</option>
              <option v-for="r in filterOptions.resolutions" :key="r" :value="r">{{ r }}</option>
            </select>
          </div>
        </div>
        <button class="btn-text" @click="resetFilters">重置筛选</button>
      </div>

      <!-- 排行榜图表 -->
      <div class="chart-panel">
        <div ref="barChartRef" class="chart-container"></div>
      </div>

      <!-- 排行榜表格 -->
      <div class="table-panel">
        <table class="data-table">
          <thead>
            <tr>
              <th>排名</th>
              <th>设备名</th>
              <th>主芯片</th>
              <th>Sensor</th>
              <th>焦距</th>
              <th>分辨率</th>
              <th>综合得分</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in leaderboard" :key="item.device_id">
              <td>{{ item.rank }}</td>
              <td>{{ item.device_name }}</td>
              <td>{{ item.main_chip }}</td>
              <td>{{ item.sensor_model }}</td>
              <td>{{ item.focal_length }}</td>
              <td>{{ item.resolution }}</td>
              <td class="score-cell">
                <div class="score-bar" :style="{ width: (item.bt_score / maxScore * 100) + '%' }"></div>
                <span>{{ filters.score_type === 'mean' ? item.mean_score?.toFixed(1) : item.bt_score?.toFixed(1) }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 雷达图（分场景得分对比） -->
      <div class="chart-panel">
        <h3>分场景得分对比</h3>
        <div ref="radarChartRef" class="chart-container"></div>
      </div>
    </div>

    <!-- Tab 2: 详细数据（管理员可见） -->
    <div v-if="activeTab === 'detail' && authStore.isAdmin">
      <!-- 导出按钮 -->
      <div class="action-bar">
        <button class="btn-outline" @click="exportRanking">导出排行榜结果</button>
        <button class="btn-outline" @click="exportDetail">导出详细数据</button>
      </div>

      <!-- 维度选择 -->
      <div class="detail-tabs">
        <button :class="{ active: detailView === 'scene' }" @click="detailView = 'scene'">按场景</button>
        <button :class="{ active: detailView === 'user' }" @click="detailView = 'user'">按用户</button>
        <button :class="{ active: detailView === 'device' }" @click="detailView = 'device'">按设备</button>
      </div>

      <!-- 按场景查看 -->
      <div v-if="detailView === 'scene'" class="detail-panel">
        <div class="detail-selector">
          <label>场景：</label>
          <select v-model="selectedSceneId" @change="fetchSceneDetail">
            <option value="">请选择场景</option>
            <option v-for="scene in filterOptions.scenes" :key="scene.id" :value="scene.id">
              {{ scene.name }}
            </option>
          </select>
        </div>

        <div v-if="sceneDetail" class="detail-content">
          <!-- 场景统计 -->
          <div class="stats-card">
            <h4>场景统计</h4>
            <p>总评测记录数：{{ sceneDetail.scene?.total_records }}</p>
            <p>有效记录数：{{ sceneDetail.scene?.valid_records }}</p>
            <p>剔除记录数：{{ sceneDetail.scene?.invalid_records }}</p>
            <p>剔除用户数：{{ sceneDetail.scene?.invalid_users?.length }}</p>
            <p>剔除用户列表：{{ sceneDetail.scene?.invalid_users?.join(', ') || '-' }}</p>
          </div>

          <!-- 设备排行 -->
          <table class="data-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>设备名</th>
                <th>评测次数</th>
                <th>评分均值</th>
                <th>BT强度</th>
                <th>BT排名</th>
                <th>均值排名</th>
                <th>排名差</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in sceneDetail.device_ranking" :key="item.device_id">
                <td>{{ item.rank }}</td>
                <td>{{ item.device_name }}</td>
                <td>{{ item.eval_count }}</td>
                <td>{{ item.mean_score?.toFixed(1) }}</td>
                <td>{{ item.bt_strength?.toFixed(2) }}</td>
                <td>{{ item.bt_rank }}</td>
                <td>{{ item.mean_rank }}</td>
                <td>{{ item.rank_diff > 0 ? '+' : '' }}{{ item.rank_diff }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 按用户查看 -->
      <div v-if="detailView === 'user'" class="detail-panel">
        <div class="detail-selector">
          <label>用户ID：</label>
          <input v-model.number="selectedUserId" type="number" placeholder="输入用户ID" />
          <button class="btn-sm" @click="fetchUserDetail">查询</button>
        </div>

        <div v-if="userDetail" class="detail-content">
          <div class="stats-card">
            <h4>用户统计</h4>
            <p>总评测数：{{ userDetail.user?.total_evals }}</p>
            <p>首次评测数：{{ userDetail.user?.first_evals }}</p>
            <p>重测数：{{ userDetail.user?.retest_evals }}</p>
            <p>重测率：{{ (userDetail.user?.retest_rate * 100)?.toFixed(0) }}%</p>
            <p>通过场景数：{{ userDetail.user?.passed_scenes }}</p>
            <p>拒绝场景数：{{ userDetail.user?.rejected_scenes }}</p>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>场景</th>
                <th>评测对数</th>
                <th>一致性得分</th>
                <th>阈值</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="detail in userDetail.scene_details" :key="detail.scene_id">
                <td>{{ detail.scene_name }}</td>
                <td>{{ detail.eval_count }}</td>
                <td>{{ detail.retest_agreement_score?.toFixed(2) }}</td>
                <td>{{ detail.retest_agreement_threshold?.toFixed(2) }}</td>
                <td>
                  <span :class="detail.passed ? 'status-pass' : 'status-reject'">
                    {{ detail.passed ? '✓' : '✗' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 按设备查看 -->
      <div v-if="detailView === 'device'" class="detail-panel">
        <div class="detail-selector">
          <label>设备：</label>
          <select v-model="selectedDeviceId" @change="fetchDeviceDetail">
            <option value="">请选择设备</option>
            <option v-for="item in leaderboard" :key="item.device_id" :value="item.device_id">
              {{ item.device_name }}
            </option>
          </select>
        </div>

        <div v-if="deviceDetail" class="detail-content">
          <table class="data-table">
            <thead>
              <tr>
                <th>场景</th>
                <th>BT得分</th>
                <th>评分均值</th>
                <th>评测次数</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="scene in deviceDetail.scenes" :key="scene.scene_id">
                <td>{{ scene.scene_name }}</td>
                <td>{{ scene.bt_score?.toFixed(1) }}</td>
                <td>{{ scene.mean_score?.toFixed(1) }}</td>
                <td>{{ scene.eval_count }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { apiGetLeaderboard, apiGetLeaderboardFilters, apiGetLeaderboardDetails, apiExportLeaderboard } from '../../api/index.js'
import * as echarts from 'echarts'

const authStore = useAuthStore()

const activeTab = ref('ranking')
const detailView = ref('scene')
const leaderboard = ref([])
const filterOptions = ref({ categories: [], subcategories: [], scenes: [], locations: [], chips: [], sensors: [], focal_lengths: [], resolutions: [] })
const lastUpdated = ref(null)

const filters = ref({
  score_type: 'bt',
  scene: '',
  category: '',
  location: '',
  subcategory: '',
  chip: '',
  sensor: '',
  focal_length: '',
  resolution: '',
})

const selectedSceneId = ref(null)
const selectedUserId = ref(null)
const selectedDeviceId = ref(null)
const sceneDetail = ref(null)
const userDetail = ref(null)
const deviceDetail = ref(null)

const barChartRef = ref(null)
const radarChartRef = ref(null)
let barChart = null
let radarChart = null

const maxScore = computed(() => {
  if (!leaderboard.value.length) return 100
  return Math.max(...leaderboard.value.map(i => i.bt_score || 0))
})

function resetFilters() {
  filters.value = {
    score_type: 'bt',
    scene: '',
    category: '',
    location: '',
    subcategory: '',
    chip: '',
    sensor: '',
    focal_length: '',
    resolution: '',
  }
  fetchLeaderboard()
}

function getFilterParams() {
  const f = filters.value
  if (f.scene) {
    const [type, value] = f.scene.split(':')
    return { filter_type: type, filter_value: value, score_type: f.score_type }
  }
  if (f.category) return { filter_type: 'category', filter_value: f.category, score_type: f.score_type }
  if (f.location) return { filter_type: 'location', filter_value: f.location, score_type: f.score_type }
  if (f.subcategory) return { filter_type: 'subcategory', filter_value: f.subcategory, score_type: f.score_type }
  if (f.chip) return { filter_type: 'chip', filter_value: f.chip, score_type: f.score_type }
  if (f.sensor) return { filter_type: 'sensor', filter_value: f.sensor, score_type: f.score_type }
  if (f.focal_length) return { filter_type: 'focal_length', filter_value: f.focal_length, score_type: f.score_type }
  if (f.resolution) return { filter_type: 'resolution', filter_value: f.resolution, score_type: f.score_type }
  return { filter_type: 'overall', score_type: f.score_type }
}

async function fetchLeaderboard() {
  try {
    const params = getFilterParams()
    const resp = await apiGetLeaderboard(params)
    leaderboard.value = resp.data?.ranking || []
    lastUpdated.value = resp.data?.last_updated
    await nextTick()
    renderBarChart()
    renderRadarChart()
  } catch (e) {
    console.error('获取排行榜失败:', e)
  }
}

async function fetchFilters() {
  try {
    const resp = await apiGetLeaderboardFilters()
    filterOptions.value = resp.data || {}
  } catch (e) {
    console.error('获取筛选选项失败:', e)
  }
}

function onSceneChange() { filters.value.category = ''; filters.value.location = ''; filters.value.subcategory = ''; fetchLeaderboard() }
function onCategoryChange() { filters.value.scene = ''; filters.value.location = ''; filters.value.subcategory = ''; fetchLeaderboard() }
function onLocationChange() { filters.value.scene = ''; filters.value.category = ''; filters.value.subcategory = ''; fetchLeaderboard() }
function onSubcategoryChange() { filters.value.scene = ''; filters.value.category = ''; filters.value.location = ''; fetchLeaderboard() }
function onChipChange() { fetchLeaderboard() }
function onSensorChange() { fetchLeaderboard() }
function onFocalLengthChange() { fetchLeaderboard() }
function onResolutionChange() { fetchLeaderboard() }

async function fetchSceneDetail() {
  if (!selectedSceneId.value) return
  try {
    const resp = await apiGetLeaderboardDetails({ view_type: 'scene', id: selectedSceneId.value })
    sceneDetail.value = resp.data
  } catch (e) {
    console.error('获取场景详情失败:', e)
  }
}

async function fetchUserDetail() {
  if (!selectedUserId.value) return
  try {
    const resp = await apiGetLeaderboardDetails({ view_type: 'user', id: selectedUserId.value })
    userDetail.value = resp.data
  } catch (e) {
    console.error('获取用户详情失败:', e)
  }
}

async function fetchDeviceDetail() {
  if (!selectedDeviceId.value) return
  try {
    const resp = await apiGetLeaderboardDetails({ view_type: 'device', id: selectedDeviceId.value })
    deviceDetail.value = resp.data
  } catch (e) {
    console.error('获取设备详情失败:', e)
  }
}

function exportRanking() {
  const params = getFilterParams()
  apiExportLeaderboard({ export_type: 'ranking', ...params })
}

function exportDetail() {
  const params = getFilterParams()
  apiExportLeaderboard({ export_type: 'detail', ...params })
}

function renderBarChart() {
  if (!barChartRef.value || !leaderboard.value.length) return
  if (!barChart) barChart = echarts.init(barChartRef.value)

  const top10 = leaderboard.value.slice(0, 10).reverse()
  barChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value' },
    yAxis: {
      type: 'category',
      data: top10.map(i => i.device_name),
    },
    series: [{
      type: 'bar',
      data: top10.map(i => ({
        value: filters.value.score_type === 'mean' ? i.mean_score : i.bt_score,
        itemStyle: { color: '#3b82f6' },
      })),
      label: { show: true, position: 'right', formatter: '{c}' },
    }],
  })
}

function renderRadarChart() {
  if (!radarChartRef.value || !leaderboard.value.length) return
  if (!radarChart) radarChart = echarts.init(radarChartRef.value)

  const top3 = leaderboard.value.slice(0, 3)
  const sceneNames = new Set()
  top3.forEach(item => {
    Object.keys(item.scene_scores || {}).forEach(name => sceneNames.add(name))
  })
  const indicators = [...sceneNames].map(name => ({ name, max: 100 }))

  radarChart.setOption({
    tooltip: {},
    legend: { data: top3.map(i => i.device_name) },
    radar: { indicator: indicators },
    series: [{
      type: 'radar',
      data: top3.map(item => ({
        name: item.device_name,
        value: [...sceneNames].map(name => item.scene_scores?.[name]?.bt_score || 0),
      })),
    }],
  })
}

watch(activeTab, (tab) => {
  if (tab === 'ranking') {
    nextTick(() => {
      barChart?.resize()
      radarChart?.resize()
    })
  }
})

onMounted(() => {
  fetchFilters()
  fetchLeaderboard()

  window.addEventListener('resize', () => {
    barChart?.resize()
    radarChart?.resize()
  })
})
</script>

<style scoped>
.leaderboard-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #1e40af;
  margin-bottom: 24px;
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.tabs button {
  padding: 10px 24px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #475569;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
}

.tabs button.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.filter-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-item label {
  font-size: 13px;
  color: #475569;
  white-space: nowrap;
}

.filter-item select {
  padding: 6px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  min-width: 120px;
}

.btn-text {
  background: none;
  border: none;
  color: #3b82f6;
  cursor: pointer;
  font-size: 13px;
}

.chart-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.chart-panel h3 {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 16px 0;
}

.chart-container {
  width: 100%;
  height: 400px;
}

.table-panel {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  font-size: 14px;
}

.data-table th {
  background: #f8fafc;
  font-weight: 600;
  color: #374151;
}

.data-table td {
  color: #475569;
}

.score-cell {
  position: relative;
  min-width: 120px;
}

.score-bar {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 8px;
  background: #3b82f6;
  border-radius: 4px;
  opacity: 0.3;
}

.score-cell span {
  position: relative;
  font-weight: 600;
  color: #1e40af;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.btn-outline {
  padding: 10px 20px;
  background: white;
  color: #3b82f6;
  border: 2px solid #3b82f6;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-outline:hover {
  background: #eff6ff;
}

.detail-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.detail-tabs button {
  padding: 8px 20px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s;
}

.detail-tabs button.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #3b82f6;
}

.detail-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.detail-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.detail-selector label {
  font-size: 14px;
  color: #475569;
}

.detail-selector select, .detail-selector input {
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
}

.btn-sm {
  padding: 8px 16px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.stats-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.stats-card h4 {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin: 0 0 12px 0;
}

.stats-card p {
  margin: 6px 0;
  font-size: 13px;
  color: #475569;
}

.status-pass {
  color: #16a34a;
  font-weight: 600;
}

.status-reject {
  color: #dc2626;
  font-weight: 600;
}

@media (max-width: 768px) {
  .filter-row {
    flex-direction: column;
  }
  .chart-container {
    height: 300px;
  }
}
</style>
```

---

## Task 16: 前端 - 修改 AdminOverview

**Files:**
- Modify: `frontend/src/views/admin/AdminOverview.vue`

- [ ] **Step 1: 在快速入口区域新增两个卡片**

在 `link-grid` 中添加：

```html
<button class="link-card" @click="$router.push('/admin/cleaning')">
  <span class="link-icon">🧹</span>
  <span class="link-label">数据清洗</span>
</button>
<button class="link-card" @click="$router.push('/admin/leaderboard')">
  <span class="link-icon">🏆</span>
  <span class="link-label">排行榜</span>
</button>
```

---

## Task 17: 前端 - 修改 AdminLayout

**Files:**
- Modify: `frontend/src/views/admin/AdminLayout.vue`

- [ ] **Step 1: 在侧边栏底部新增分隔线和菜单项**

在 `UserManage` 导航项之后添加：

```html
<div class="nav-divider"></div>
<div class="nav-item" :class="{ active: $route.name === 'DataCleaning' }" @click="$router.push('/admin/cleaning')">
  <span class="nav-icon">🧹</span>
  <span class="nav-label">数据清洗</span>
</div>
<div class="nav-item" :class="{ active: $route.name === 'AdminLeaderboard' }" @click="$router.push('/admin/leaderboard')">
  <span class="nav-icon">🏆</span>
  <span class="nav-label">排行榜</span>
</div>
```

---

## 验证检查清单

完成所有任务后，按以下顺序验证：

- [ ] 后端启动无错误
- [ ] 前端启动无错误
- [ ] 管理员可以访问数据清洗页面
- [ ] 管理员可以执行数据清洗
- [ ] 清洗结果正确写入 evaluations 表
- [ ] 排行榜数据正确计算并写入 leaderboard_rankings 表
- [ ] 排行榜页面正确显示（登录页 /ranking）
- [ ] 管理员可以访问排行榜详细数据
- [ ] 筛选功能正常工作
- [ ] 导出功能正常工作
- [ ] 侧边栏和概览页入口正确

---

## 统一提交

所有任务完成并验证通过后，执行统一的 git 提交：

```bash
git add -A
git commit -m "feat: 实现数据清洗和排行榜功能

- 迁移 clean_and_stats 模块到主后端
- 重写数据清洗服务（单用户一致性 + 用户组一致性）
- 新增排行榜服务（BT 得分 + 评分均值）
- 新增 leaderboard_ranking 表
- 新增数据清洗和排行榜 API
- 新增前端数据清洗页面
- 新增前端排行榜页面（含 ECharts 图表）
- 修改管理概览和侧边栏添加入口
- 新增公开排行榜路由 /ranking"
```
