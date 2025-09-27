@echo off
setlocal enabledelayedexpansion

REM HashInsight Complete Mining Platform Deployment Script for Windows
REM HashInsight完整挖矿平台Windows部署脚本

set "PLATFORM_VERSION=2.1.0"
set "BUILD_DATE=2025-09-27"

REM 颜色定义 (Windows CMD)
set "INFO=[INFO]"
set "WARN=[WARN]"
set "ERROR=[ERROR]"
set "STEP=[STEP]"
set "HEADER=[PLATFORM]"

REM 显示Logo
echo.
echo ================================================================================
echo     HASHINSIGHT COMPLETE MINING PLATFORM v2.1.0
echo     Professional Deployment Suite for Windows
echo     Build Date: %BUILD_DATE%
echo ================================================================================
echo.

REM 主要命令处理
if "%1"=="" goto install
if "%1"=="install" goto install
if "%1"=="start" goto start_services
if "%1"=="stop" goto stop_services
if "%1"=="restart" goto restart_services
if "%1"=="status" goto health_check
if "%1"=="health" goto health_check
if "%1"=="logs" goto show_logs
if "%1"=="help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="--help" goto show_help

echo Unknown command: %1
goto show_help

:install
echo %HEADER% Starting HashInsight Platform Installation...
echo.

REM 系统检查
echo %STEP% Checking system requirements...

REM 检查Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo %ERROR% Python is not installed or not in PATH. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo %INFO% Python %PYTHON_VERSION% detected

REM 检查Node.js (可选)
node --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo %INFO% Node.js !NODE_VERSION! detected
) else (
    echo %WARN% Node.js not found. Smart contract features may be limited.
)

REM 检查Docker (可选)
docker --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=3" %%i in ('docker --version 2^>^&1') do set DOCKER_VERSION=%%i
    echo %INFO% Docker !DOCKER_VERSION! detected
    set DOCKER_AVAILABLE=true
) else (
    echo %WARN% Docker not found. Container deployment unavailable.
    set DOCKER_AVAILABLE=false
)

REM 检查配置文件
echo.
echo %STEP% Checking module configurations...

set MODULES=mining_core_module web3_integration_module user_management_module
set CONFIG_FILES=config.env.template blockchain_config.env.template database_config.env.template

set /a index=0
for %%m in (%MODULES%) do (
    set /a index+=1
    set MODULE=%%m
    
    if !index!==1 set CONFIG=config.env.template
    if !index!==2 set CONFIG=blockchain_config.env.template
    if !index!==3 set CONFIG=database_config.env.template
    
    if not exist "!MODULE!" (
        echo %ERROR% Module directory !MODULE! not found!
        pause
        exit /b 1
    )
    
    if not exist "!CONFIG!" (
        echo %ERROR% Configuration template !CONFIG! not found!
        pause
        exit /b 1
    )
    
    set MODULE_ENV=!MODULE!\.env
    if not exist "!MODULE_ENV!" (
        echo %WARN% No .env file found for !MODULE!. Creating from template...
        if not exist "!MODULE!" mkdir "!MODULE!"
        copy "!CONFIG!" "!MODULE_ENV!" >nul
        echo %INFO% Created .env file for !MODULE!
    ) else (
        echo %INFO% !MODULE! configuration found
    )
)

REM 安装依赖
echo.
echo %STEP% Installing dependencies for all modules...

for %%m in (%MODULES%) do (
    echo.
    echo %INFO% Installing dependencies for %%m...
    
    cd %%m
    
    REM 创建虚拟环境
    if not exist venv (
        echo %INFO% Creating virtual environment for %%m...
        python -m venv venv
    )
    
    REM 激活虚拟环境
    call venv\Scripts\activate.bat
    
    REM 升级pip
    python -m pip install --upgrade pip >nul 2>&1
    
    REM 安装依赖
    if exist requirements.txt (
        pip install -r requirements.txt >nul 2>&1
        if %errorlevel% equ 0 (
            echo %INFO% %%m dependencies installed successfully
        ) else (
            echo %ERROR% Failed to install dependencies for %%m
            deactivate
            cd ..
            pause
            exit /b 1
        )
    ) else (
        echo %ERROR% requirements.txt not found in %%m!
        deactivate
        cd ..
        pause
        exit /b 1
    )
    
    REM 检验关键依赖
    if "%%m"=="mining_core_module" (
        python -c "import flask, psutil, schedule" 2>nul && echo %INFO% Core dependencies verified || echo %WARN% Some core dependencies missing
    )
    if "%%m"=="web3_integration_module" (
        python -c "import web3, eth_account, cryptography" 2>nul && echo %INFO% Web3 dependencies verified || echo %WARN% Some Web3 dependencies missing
    )
    if "%%m"=="user_management_module" (
        python -c "import flask_sqlalchemy, flask_login, celery" 2>nul && echo %INFO% User management dependencies verified || echo %WARN% Some user management dependencies missing
    )
    
    deactivate
    cd ..
)

REM 初始化数据库
echo.
echo %STEP% Initializing databases...

for %%m in (%MODULES%) do (
    echo %INFO% Initializing database for %%m...
    
    cd %%m
    call venv\Scripts\activate.bat
    
    REM 加载环境变量并初始化数据库
    python -c "
from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('Database initialized for %%m')
    except Exception as e:
        print(f'Database initialization failed for %%m: {e}')
" 2>nul || echo %WARN% Database initialization failed for %%m (manual setup may be required)
    
    deactivate
    cd ..
)

REM 创建必要目录
echo.
echo %STEP% Creating necessary directories...
if not exist logs mkdir logs
if not exist nginx mkdir nginx
if not exist ssl mkdir ssl
if not exist backups mkdir backups

echo.
echo %HEADER% Installation Complete!
echo.
echo Next steps:
echo 1. Review and update .env files in each module directory
echo 2. Configure your database connections
echo 3. Run: %0 start
echo 4. Access platform services on their respective ports
echo.
echo Platform Access:
echo   Mining Core Module:     http://localhost:5001
echo   Web3 Integration:       http://localhost:5002  
echo   User Management:        http://localhost:5003
echo.
pause
goto :EOF

:start_services
echo %HEADER% Starting Platform Services...
echo.

REM 创建必要目录
if not exist logs mkdir logs

REM 启动各模块服务
set MODULES=mining_core_module web3_integration_module user_management_module
set PORTS=5001 5002 5003
set /a port_index=0

for %%m in (%MODULES%) do (
    set /a port_index+=1
    
    if !port_index!==1 set PORT=5001
    if !port_index!==2 set PORT=5002
    if !port_index!==3 set PORT=5003
    
    echo %STEP% Starting %%m on port !PORT!...
    
    cd %%m
    call venv\Scripts\activate.bat
    
    REM 加载环境变量
    if exist .env (
        for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
            if not "%%a"=="" if not "%%a"=="REM" if not "%%a"=="#" (
                set "%%a=%%b"
            )
        )
    )
    
    REM 设置端口和主机
    set PORT=!PORT!
    set HOST=0.0.0.0
    
    REM 启动服务 (后台运行)
    start /B "%%m" cmd /c "gunicorn --bind 0.0.0.0:!PORT! --workers 2 --timeout 120 main:app > ..\logs\%%m.log 2>&1"
    
    echo %INFO% %%m started on port !PORT!
    
    deactivate
    cd ..
    
    REM 等待服务启动
    timeout /t 3 >nul
)

echo.
echo %HEADER% All services started successfully!
echo.
echo Platform Access URLs:
echo   Mining Core Module:     http://localhost:5001
echo   Web3 Integration:       http://localhost:5002
echo   User Management:        http://localhost:5003
echo.
echo %INFO% Services are running in background.
echo %INFO% Check logs in the 'logs' directory for any issues.
echo.
pause
goto :EOF

:stop_services
echo %HEADER% Stopping Platform Services...
echo.

REM 停止Gunicorn进程
taskkill /F /IM "gunicorn.exe" >nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq mining_core_module*" >nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq web3_integration_module*" >nul 2>&1
taskkill /F /IM "python.exe" /FI "WINDOWTITLE eq user_management_module*" >nul 2>&1

echo %INFO% All platform services stopped
echo.
pause
goto :EOF

:restart_services
echo %HEADER% Restarting Platform Services...
call :stop_services
timeout /t 3 >nul
call :start_services
goto :EOF

:health_check
echo %HEADER% Platform Health Check...
echo.

set SERVICES=http://localhost:5001/health http://localhost:5002/health http://localhost:5003/health
set SERVICE_NAMES=Mining-Core Web3-Integration User-Management

set /a service_index=0
for %%s in (%SERVICES%) do (
    set /a service_index+=1
    
    if !service_index!==1 set SERVICE_NAME=Mining-Core
    if !service_index!==2 set SERVICE_NAME=Web3-Integration  
    if !service_index!==3 set SERVICE_NAME=User-Management
    
    echo %STEP% Checking !SERVICE_NAME!...
    
    curl -f -s "%%s" >nul 2>&1
    if %errorlevel% equ 0 (
        echo %INFO% !SERVICE_NAME! is healthy
    ) else (
        echo %WARN% !SERVICE_NAME! is not responding
    )
)

echo.
pause
goto :EOF

:show_logs
if "%2"=="" (
    echo Available logs:
    if exist logs\*.log (
        dir /b logs\*.log
    ) else (
        echo No logs found
    )
) else (
    if exist logs\%2.log (
        type logs\%2.log
    ) else (
        echo Log file not found: logs\%2.log
    )
)
pause
goto :EOF

:show_help
echo.
echo HashInsight Complete Mining Platform Deployment Script v%PLATFORM_VERSION%
echo.
echo Usage: %0 [COMMAND] [OPTIONS]
echo.
echo Commands:
echo     install         Install and configure all modules
echo     start           Start all platform services
echo     stop            Stop all platform services
echo     restart         Restart all platform services
echo     status          Check platform status
echo     health          Perform health check
echo     logs [module]   Show service logs
echo     help            Show this help message
echo.
echo Options:
echo     --dev           Run in development mode
echo     --prod          Run in production mode (default)
echo.
echo Examples:
echo     %0 install              # Install complete platform
echo     %0 start                # Start all services
echo     %0 health               # Check all services
echo     %0 logs mining_core     # Show mining core logs
echo.
echo Services:
echo     Mining Core Module      http://localhost:5001
echo     Web3 Integration        http://localhost:5002
echo     User Management         http://localhost:5003
echo.
echo For detailed documentation, see COMPLETE_DEPLOYMENT_GUIDE.md
echo.
pause
goto :EOF

:EOF