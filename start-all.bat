@echo off
setlocal

echo ========================================
echo 启动租房避坑局前后端服务
echo ========================================

cd /d "%~dp0"

echo.
echo [1/3] 启动后端服务（端口 8000）...
start "租房避坑局-后端" cmd /k "cd backend && python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo [2/3] 等待后端启动...
timeout /t 3 /nobreak >nul

echo.
echo [3/3] 启动前端服务（端口 3000）...
start "租房避坑局-前端" cmd /k "npm run dev"

echo.
echo ========================================
echo 服务启动完成
echo ========================================
echo.
echo 后端地址: http://localhost:8000
echo 前端地址: http://localhost:3000
echo API 文档: http://localhost:8000/docs
echo.
echo 按任意键关闭此窗口...
pause >nul
