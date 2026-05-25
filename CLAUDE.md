# Blind Eval System

用于图像质量对比评测系统，最终目标是根据用户评测结果输出各设备的排行榜

## 技术栈

- **后端**: FastAPI + SQLAlchemy + MySQL (PyMySQL)
- **前端**: Vue 3 + Pinia + Vue Router + Vite
- **图像处理**: Pillow (生成演示图/缩略图)
- **包管理**: uv (Python), npm (Node.js)
- **认证**: JWT (python-jose) + bcrypt

## 常用命令

```bash
# 启动后端 (开发模式)
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端
cd frontend && npm run dev

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
- **评分映射**: 5级评分 (A更好/A稍好/一样好/B稍好/B更好)
- **缩略图**: 300x300

## 开发注意事项

1. **CORS**: 已配置 localhost:5173 (前端开发服务器)
2. **静态文件**: 图像通过 `/uploads/images` 和 `/uploads/thumbnails` 提供
3. **认证**: JWT Token 存储在 localStorage (`blind_eval_token`)
4. **路由**: 前端使用 Hash 模式 (`createWebHashHistory`)
5. **默认账号**: admin/admin123, evaluator1/eval123
