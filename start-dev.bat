@echo off
REM 一键启动：用户端 5173 + 管理台 5174 + 后端 8001
setlocal
cd /d "%~dp0backend"
start "时光迹 API" cmd /k .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
cd /d "%~dp0frontend\user"
start "时光迹用户端" cmd /k npm run dev
cd /d "%~dp0frontend\admin"
start "时光迹管理台" cmd /k npm run dev
echo.
echo 用户端:   http://localhost:5173
echo 管理台:   http://localhost:5174
echo 接口文档: http://127.0.0.1:8001/docs
endlocal
