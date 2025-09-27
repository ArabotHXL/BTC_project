@echo off
REM Web3 Integration Module Startup Script for Windows
REM Web3集成模块Windows启动脚本

setlocal enabledelayedexpansion

REM 颜色定义 (Windows CMD不支持颜色，但我们可以用echo)
set "INFO=[INFO]"
set "WARN=[WARN]"
set "ERROR=[ERROR]"
set "DEBUG=[DEBUG]"

echo %INFO% Starting Web3 Integration Module deployment...

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

REM 检查Node.js (可选)
node --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%i in ('node --version 2^>^&1') do set NODE_VERSION=%%i
    echo %INFO% Node.js !NODE_VERSION! detected
) else (
    echo %WARN% Node.js not found. Some smart contract features may not work.
)

REM 检查环境配置文件
if not exist .env (
    if exist blockchain_config.env.template (
        echo %WARN% .env file not found. Creating from template...
        copy blockchain_config.env.template .env
        echo %WARN% Please edit .env file with your blockchain configuration before running again.
        pause
        exit /b 1
    ) else (
        echo %ERROR% No .env file or template found. Please create blockchain configuration file.
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

REM 安装Python依赖
echo %INFO% Installing Python dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
) else (
    echo %ERROR% requirements.txt not found!
    pause
    exit /b 1
)
echo %INFO% Python dependencies installed

REM 安装Node.js依赖 (如果存在)
if exist package.json (
    where npm >nul 2>&1
    if !errorlevel! equ 0 (
        echo %INFO% Installing Node.js dependencies...
        npm install
        echo %INFO% Node.js dependencies installed
    )
)

REM 加载环境变量
if exist .env (
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a"=="REM" if not "%%a"=="#" (
            set "%%a=%%b"
        )
    )
)

REM 检查区块链连接
echo %INFO% Checking blockchain connection...
cd web3_integration_module
python -c "
import os
from web3 import Web3
try:
    if 'ETHEREUM_RPC_URL' in os.environ:
        w3 = Web3(Web3.HTTPProvider(os.environ['ETHEREUM_RPC_URL']))
        if w3.is_connected():
            print('✓ Ethereum connection successful')
            latest_block = w3.eth.block_number
            print(f'✓ Latest block: {latest_block}')
        else:
            print('✗ Ethereum connection failed')
    else:
        print('! Ethereum RPC URL not configured')
    print('Blockchain connection check completed')
except Exception as e:
    print(f'Connection check failed: {e}')
" 2>nul
cd ..
echo %INFO% Blockchain connection check completed

REM 编译智能合约 (如果需要)
if exist web3_integration_module\contracts (
    where npx >nul 2>&1
    if !errorlevel! equ 0 (
        echo %INFO% Compiling smart contracts...
        cd web3_integration_module\contracts
        if exist package.json (
            npx hardhat compile 2>nul || echo %WARN% Smart contract compilation failed (optional)
        )
        cd ..\..
        echo %INFO% Smart contract compilation completed
    )
)

REM 初始化数据库
echo %INFO% Initializing database...
cd web3_integration_module
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
if not defined PORT set PORT=5002
if not defined HOST set HOST=0.0.0.0

REM 启动应用
echo %INFO% Starting Web3 Integration Module...
cd web3_integration_module

if "%FLASK_ENV%"=="development" (
    echo %INFO% Starting in development mode...
    python main.py
) else (
    echo %INFO% Starting in production mode with Gunicorn...
    gunicorn --bind %HOST%:%PORT% --workers 4 --timeout 120 --worker-class eventlet main:app
)

cd ..
pause