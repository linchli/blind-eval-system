## Context

将图像盲评系统打包为单个 exe 文件，双击即可启动服务并在浏览器中打开。后端 FastAPI + 前端 Vue3SPA，继续使用外部 MySQL

## 方案概述

使用 PyInstaller 将后端 FastAPI 应用打包为单个 exe，前端先 `npm run build` 生成 dist，将 dist
目录作为数据文件嵌入 exe。运行时 exe 启动 uvicorn 服务并自动打开浏览器。

## 实施步骤

### 1. 构建前端
- 在 `frontend/` 目录执行 `npm run build`，生成 `frontend/dist/`

### 2. 修改后端入口以支持 PyInstaller 打包
- 修改 `backend/main.py`：
- 修正 `IS_PRODUCTION` 检测逻辑，支持 PyInstaller 的 `_MEIPASS` 临时目录
- 添加命令行参数解析（`--port`、`--no-browser`）
- 启动时自动打开浏览器
- 移除 `reload=True`（打包后不需要）

### 3. 修改配置文件路径逻辑
- 修改 `backend/app/core/config.py`：
- `BASE_DIR` 在 PyInstaller 打包后需要正确指向 exe 所在目录（使用 `sys._MEIPASS` 或 `sys.executable`）
- uploads 目录应放在 exe 同级目录下（而非临时目录内）

### 4. 创建 PyInstaller spec 文件
- 创建 `blind_eval.spec`，配置：
- `onefile` 模式
- 入口为 `backend/main.py`
- `datas`: 前端 dist 目录
- `hiddenimports`: FastAPI/SQLAlchemy 等动态导入模块
- 排除不需要的模块减小体积

### 5. 创建打包脚本
- 创建 `build.bat`：一键执行前端构建 + PyInstaller 打包

### 6. 测试验证
- 运行生成的 exe，确认：
- 服务正常启动在 8000 端口
- 浏览器自动打开
- API 和前端页面均可访问
- 数据库连接正常

## 关键文件修改

| 文件 | 操作 |
|------|------|
| `backend/main.py` | 修改：支持 PyInstaller 路径、自动打开浏览器、端口参数 |
| `backend/app/core/config.py` | 修改：BASE_DIR 兼容 PyInstaller 打包路径 |
| `blind_eval.spec` | 新建：PyInstaller 配置 |
| `build.bat` | 新建：一键打包脚本 |

## 验证方法

1. 运行 `build.bat` 完成打包
2. 在 `dist/` 目录找到 `blind_eval.exe`
3. 双击运行，确认浏览器自动打开 `http://localhost:8000`
4. 测试登录、图片管理等核心功能
