@echo off
echo ============================================
echo   Blind Eval System v0.3 - Startup
echo ============================================
echo.

:: Init database
:: echo [1/2] Init database...
:: uv run python backend/init_db.py

:: Start backend service
echo [1/2] Starting backend...
start "" cmd /k "title Backend - Blind Eval && cd /d %~dp0 && uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait 1 second to avoid conflict
timeout /t 1 /nobreak >nul

:: Start frontend service
echo [2/2] Starting frontend...
start "" cmd /k "title Frontend - Blind Eval && cd /d %~dp0\frontend && npm run dev"

echo.
echo ============================================
echo   Started!
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   Account:  admin / admin123
echo.
echo   Two service windows are running.
echo   Close them to stop services.
echo   Closing this window won't affect services.
echo ============================================
echo.
pause
