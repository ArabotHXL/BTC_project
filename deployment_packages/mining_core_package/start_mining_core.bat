@echo off
REM Mining Core Module Startup Script for Windows
REM 挖矿核心模块Windows启动脚本

setlocal enabledelayedexpansion

REM 颜色定义 (Windows CMD不支持颜色，但我们可以用echo)
set "INFO=[INFO]"
set "WARN=[WARN]"
set "ERROR=[ERROR]"

REM 检查Python是否安装
echo %INFO% Checking Python installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Python is not installed or not in PATH. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM 获取Python版本
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %INFO% Python %PYTHON_VERSION% detected

REM 检查环境配置文件
if not exist .env (
    if exist config.env.template (
        echo %WARN% .env file not found. Creating from template...
        copy config.env.template .env
        echo %WARN% Please edit .env file with your configuration before running again.
        pause
        exit /b 1
    ) else (
        echo %ERROR% No .env file or template found. Please create configuration file.
        pause
        exit /b 1
    )
)
echo %INFO% Environment configuration found

REM 创建虚拟环境
if not exist venv (
    echo %INFO% Creating virtual environment...
    python -m venv venv
)

REM 激活虚拟环境
echo %INFO% Activating virtual environment...
call venv\Scripts\activate.bat

REM 升级pip
echo %INFO% Upgrading pip...
python -m pip install --upgrade pip

REM 安装依赖
echo %INFO% Installing dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo %ERROR% requirements.txt not found!
    pause
    exit /b 1
)
echo %INFO% Dependencies installed

REM 加载环境变量
if exist .env (
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a"=="REM" if not "%%a"=="#" (
            set "%%a=%%b"
        )
    )
)

REM 初始化数据库
echo %INFO% Initializing database...
cd mining_core_module
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized successfully')" 2>nul
if %errorlevel% neq 0 (
    echo %ERROR% Database initialization failed!
    cd ..
    pause
    exit /b 1
)
cd ..
echo %INFO% Database initialized

REM 设置默认值
if not defined FLASK_ENV set FLASK_ENV=production
if not defined PORT set PORT=5001
if not defined HOST set HOST=0.0.0.0

REM 启动应用
echo %INFO% Starting Mining Core Module...
cd mining_core_module

if "%FLASK_ENV%"=="development" (
    echo %INFO% Starting in development mode...
    python main.py
) else (
    echo %INFO% Starting in production mode with Gunicorn...
    gunicorn --bind %HOST%:%PORT% --workers 4 --timeout 120 main:app
)

cd ..
pause