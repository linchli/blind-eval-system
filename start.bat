@echo off
chcp 65001 >nul
echo ============================================
echo   图像盲评系统 v0.2 - 启动脚本
echo ============================================
echo.

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查依赖
echo [1/3] 检查后端依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [安装] 安装后端依赖...
    pip install fastapi uvicorn sqlalchemy pymysql python-jose passlib bcrypt pydantic python-multipart pillow
)

echo [2/3] 初始化数据库...
python -m backend.init_db

echo [3/3] 启动后端服务...
echo.
echo 启动完成！
echo 后端地址: http://localhost:8000
echo 默认账号: admin / admin123
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
