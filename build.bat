@echo off
echo ============================================
echo   Blind Eval System - Build EXE
echo ============================================
echo.

:: Check frontend dist
if not exist "frontend\dist\index.html" (
    echo [1/3] Building frontend...
    cd frontend
    call npm run build
    cd ..
    if not exist "frontend\dist\index.html" (
        echo ERROR: Frontend build failed!
        pause
        exit /b 1
    )
) else (
    echo [1/3] Frontend dist already exists, skipping build.
)

:: Install PyInstaller via uv
echo [2/3] Installing PyInstaller...
uv add pyinstaller

:: Build exe
echo [3/3] Building exe with PyInstaller...
uv run pyinstaller blind_eval.spec --noconfirm

echo.
if exist "dist\blind_eval.exe" (
    echo ============================================
    echo   Build successful!
    echo   Output: dist\blind_eval.exe
    echo.
    echo   Usage: blind_eval.exe [--port PORT] [--no-browser]
    echo   Default: http://localhost:8000
    echo ============================================
) else (
    echo ERROR: Build failed!
)
echo.
pause
