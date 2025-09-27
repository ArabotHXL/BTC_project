@echo off
REM User Management Module Startup Script for Windows
REM 用户管理模块Windows启动脚本

setlocal enabledelayedexpansion

REM 颜色定义 (Windows CMD不支持颜色，但我们可以用echo)
set "INFO=[INFO]"
set "WARN=[WARN]" 
set "ERROR=[ERROR]"
set "DEBUG=[DEBUG]"
set "HEADER=[USER-MGMT]"

echo %HEADER% Starting User Management Module deployment...

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
    if exist database_config.env.template (
        echo %WARN% .env file not found. Creating from template...
        copy database_config.env.template .env
        echo %WARN% Please edit .env file with your database and user management configuration before running again.
        echo %WARN% Important: Configure SMTP settings for email notifications and database credentials.
        pause
        exit /b 1
    ) else (
        echo %ERROR% No .env file or template found. Please create user management configuration file.
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

REM 检查数据库连接
echo %INFO% Checking database connection...
cd user_management_module
python -c "
import os
import sys
from sqlalchemy import create_engine, text
try:
    db_url = os.environ.get('DATABASE_URL', 'sqlite:///user_management.db')
    engine = create_engine(db_url)
    with engine.connect() as conn:
        if 'postgresql' in db_url:
            result = conn.execute(text('SELECT version()'))
            version = result.fetchone()[0]
            print(f'✓ PostgreSQL connected: {version.split()[1]}')
        elif 'sqlite' in db_url:
            result = conn.execute(text('SELECT sqlite_version()'))
            version = result.fetchone()[0]
            print(f'✓ SQLite connected: {version}')
        else:
            print('✓ Database connected')
    print('Database connection successful')
except Exception as e:
    print(f'Database connection failed: {e}')
    sys.exit(1)
" 2>nul
if %errorlevel% neq 0 (
    echo %ERROR% Database connection failed!
    cd ..
    pause
    exit /b 1
)
cd ..
echo %INFO% Database connection check completed

REM 初始化数据库
echo %INFO% Initializing database...
cd user_management_module
python -c "
from app import app, db
from models import User, Plan, Customer, CRMContact, CRMActivity
import os
with app.app_context():
    try:
        db.create_all()
        print('✓ Database tables created')
        admin_user = User.query.filter_by(username='admin').first()
        if not admin_user:
            from werkzeug.security import generate_password_hash
            admin = User(
                username='admin',
                email='admin@hashinsight.net',
                password_hash=generate_password_hash('admin123'),
                role='admin',
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print('✓ Default admin user created (admin/admin123)')
        else:
            print('✓ Admin user already exists')
        if Plan.query.count() == 0:
            basic_plan = Plan(
                name='Basic Plan',
                description='Basic mining hosting plan',
                price=99.99,
                features='Basic features included',
                is_active=True
            )
            pro_plan = Plan(
                name='Pro Plan', 
                description='Professional mining hosting plan',
                price=199.99,
                features='Advanced features included',
                is_active=True
            )
            db.session.add_all([basic_plan, pro_plan])
            db.session.commit()
            print('✓ Default plans created')
        else:
            print('✓ Plans already exist')
        print('Database initialization completed successfully')
    except Exception as e:
        print(f'Database initialization failed: {e}')
        exit(1)
" 2>nul
if %errorlevel% neq 0 (
    echo %ERROR% Database initialization failed!
    cd ..
    pause
    exit /b 1
)
cd ..
echo %INFO% Database initialized

REM 检查SMTP配置
if defined SMTP_SERVER (
    if defined SMTP_USERNAME (
        echo %INFO% SMTP configuration found
        cd user_management_module
        python -c "
import smtplib
import os
from email.mime.text import MimeText
try:
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    if all([smtp_server, smtp_username, smtp_password]):
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.quit()
        print('✓ SMTP connection successful')
    else:
        print('! SMTP not configured - email notifications disabled')
except Exception as e:
    print(f'! SMTP connection failed: {e}')
" 2>nul
        cd ..
    ) else (
        echo %WARN% SMTP not fully configured - email notifications will be disabled
    )
) else (
    echo %WARN% SMTP not configured - email notifications will be disabled
)

REM 设置默认值
if not defined FLASK_ENV set FLASK_ENV=production
if not defined PORT set PORT=5003
if not defined HOST set HOST=0.0.0.0

REM 启动应用
echo %HEADER% Starting User Management Module...
cd user_management_module

if "%FLASK_ENV%"=="development" (
    echo %INFO% Starting in development mode...
    echo %INFO% Admin Panel: http://%HOST%:%PORT%/admin
    echo %INFO% CRM Dashboard: http://%HOST%:%PORT%/crm
    echo %INFO% User Portal: http://%HOST%:%PORT%/
    python main.py
) else (
    echo %INFO% Starting in production mode with Gunicorn...
    echo %INFO% Admin Panel: http://%HOST%:%PORT%/admin
    echo %INFO% CRM Dashboard: http://%HOST%:%PORT%/crm
    echo %INFO% User API: http://%HOST%:%PORT%/api/v1
    gunicorn --bind %HOST%:%PORT% --workers 4 --timeout 120 main:app
)

cd ..
pause