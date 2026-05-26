# Blind Eval System

用于图像质量对比评测系统，最终目标是根据用户评测结果输出各设备的排行榜

## 技术栈

- **后端**: FastAPI + SQLAlchemy + MySQL (PyMySQL)
- **前端**: Vue 3 + Pinia + Vue Router + Vite
- **图像处理**: Pillow (生成演示图/缩略图)
- **包管理**: uv (Python), npm (Node.js)
- **认证**: JWT (python-jose) + bcrypt

## 项目结构

```
blind-eval-system/
├── backend/
│   ├── main.py              # FastAPI 入口，启动时建表+创建默认用户
│   ├── app/
│   │   ├── api/             # API 路由
│   │   │   ├── auth.py      # 认证相关 (登录/注册)
│   │   │   ├── admin.py     # 管理接口 (场景/设备/图对)
│   │   │   ├── eval.py      # 评测核心逻辑 (会话管理/评分)
│   │   │   ├── image.py     # 图像上传/管理
│   │   │   └── stats.py     # 统计分析
│   │   ├── core/
│   │   │   ├── config.py    # 配置 (MySQL/JWT/文件路径/评测参数)
│   │   │   ├── database.py  # SQLAlchemy 引擎和会话
│   │   │   ├── dependencies.py # 依赖注入 (get_current_user)
│   │   │   └── security.py  # 密码哈希/JWT 工具
│   │   ├── models/          # SQLAlchemy 模型
│   │   │   ├── user.py
│   │   │   ├── scene.py
│   │   │   ├── device_model.py
│   │   │   ├── image.py
│   │   │   ├── image_pair.py
│   │   │   └── evaluation.py
│   │   └── schemas/         # Pydantic 模型
│   └── init_db.py           # 数据库初始化脚本
├── frontend/
│   ├── src/
│   │   ├── api/index.js     # Axios 实例和 API 封装
│   │   ├── router/index.js  # 路由配置 (Hash 模式)
│   │   ├── stores/
│   │   │   ├── auth.js      # 认证状态管理
│   │   │   └── eval.js      # 评测状态管理
│   │   └── views/
│   │       ├── auth/        # 登录/注册页面
│   │       ├── evaluator/   # 评测页面/结果页面
│   │       └── admin/       # 管理后台 (场景/设备/图像/图对)
│   └── vite.config.js
├── uploads/                 # 文件上传目录
│   ├── images/              # 原始图像
│   └── thumbnails/          # 缩略图
├── pyproject.toml           # Python 项目配置
└── start.bat                # Windows 一键启动脚本
```

## 常用命令

```bash
# 启动后端 (开发模式)
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端
cd frontend && npm run dev

# Windows 一键启动
start.bat

# 初始化数据库 (如果需要)
python -m backend.init_db
```

## 数据库

- **数据库名**: blind_eval
- **字符集**: utf8mb4
- **连接**: MySQL 本地 (127.0.0.1:3306)

```sql
CREATE DATABASE blind_eval DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

主要表结构:
- `users` - 用户表 (admin/evaluator/guest 角色)
- `scenes` - 场景表
- `devices` - 设备表 (图像来源设备)
- `images` - 图像表
- `image_pairs` - 图像对表 (用于对比评测)
- `eval_sessions` - 评测会话表
- `evaluations` - 评分记录表

## API 端点

### 认证 `/api/auth`
- POST `/login` - 登录获取 JWT
- POST `/register` - 注册

### 评测 `/api/eval`
- GET `/status` - 获取评测状态
- POST `/start-session` - 开始新会话 (分配 N 对图对)
- POST `/resume-session` - 恢复会话
- POST `/submit` - 提交草稿评分
- POST `/submit-round` - 整轮提交锁定
- GET `/pair/{id}` - 获取图对详情

### 管理 `/api/admin`
- POST `/init-demo` - 初始化演示数据
- GET `/scenes` - 场景列表
- GET `/devices` - 设备列表
- GET `/pairs` - 图对列表

## 评测状态机

```
LOADING → NO_PAIRS | READY_TO_START | RESUMABLE
READY_TO_START → IN_SESSION
RESUMABLE → IN_SESSION
IN_SESSION → BATCH_COMPLETE → ALL_DONE
BATCH_COMPLETE → READY_TO_START (再来一轮)
```

## 配置项 (backend/app/core/config.py)

- **MySQL**: 环境变量或默认值 (root/123456)
- **JWT**: HS256, 24小时过期
- **评测参数**: DEFAULT_BATCH_SIZE=6, MAX_BATCH_SIZE=30, DAILY_LIMIT=60
- **评分映射**: 5级评分 (A更好/A稍好/一样好/B稍好/B更好)
- **缩略图**: 300x300

## 开发注意事项

1. **CORS**: 已配置 localhost:5173 (前端开发服务器)
2. **静态文件**: 图像通过 `/uploads/images` 和 `/uploads/thumbnails` 提供
3. **认证**: JWT Token 存储在 localStorage (`blind_eval_token`)
4. **路由**: 前端使用 Hash 模式 (`createWebHashHistory`)
5. **默认账号**: admin/admin123, evaluator1/eval123, evaluator2/eval123, guest/guest123
