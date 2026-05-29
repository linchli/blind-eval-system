# Blind Eval System

用于图像质量对比评测系统，最终目标是根据用户评测结果输出各设备的排行榜

## 技术栈

- **后端**: FastAPI + SQLAlchemy + MySQL (PyMySQL)
- **前端**: Vue 3 + Pinia + Vue Router + Vite
- **包管理**: uv (Python), npm (Node.js)
- **认证**: JWT (python-jose) + bcrypt

## 数据库

- **数据库名**: blind_eval
- **字符集**: utf8mb4
- **连接**: MySQL 本地 (127.0.0.1:3306)

## 开发注意事项

1. **CORS**: 已配置 localhost:5173 (前端开发服务器)
2. **静态文件**: 图像通过 `/uploads/images` 和 `/uploads/thumbnails` 提供
3. **认证**: JWT Token 存储在 localStorage (`blind_eval_token`)
4. **路由**: 前端使用 Hash 模式 (`createWebHashHistory`)
5. **默认账号**: admin/admin123, evaluator1/eval123, evaluator2/eval123, guest/guest123
