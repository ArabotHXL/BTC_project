#!/bin/bash

# User Management Module Startup Script
# 用户管理模块启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}[USER-MGMT]${NC} $1"
}

# 检查Python版本
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    REQUIRED_VERSION="3.8"
    
    if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
        log_error "Python $PYTHON_VERSION is installed, but Python $REQUIRED_VERSION or higher is required."
        exit 1
    fi
    
    log_info "Python $PYTHON_VERSION detected ✓"
}

# 检查环境配置文件
check_env_config() {
    if [ ! -f .env ]; then
        if [ -f database_config.env.template ]; then
            log_warn ".env file not found. Creating from template..."
            cp database_config.env.template .env
            log_warn "Please edit .env file with your database and user management configuration before running again."
            log_warn "Important: Configure SMTP settings for email notifications and database credentials."
            exit 1
        else
            log_error "No .env file or template found. Please create user management configuration file."
            exit 1
        fi
    fi
    log_info "Environment configuration found ✓"
}

# 创建虚拟环境
setup_virtualenv() {
    if [ ! -d "venv" ]; then
        log_info "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    log_info "Activating virtual environment..."
    source venv/bin/activate
    
    log_info "Upgrading pip..."
    pip install --upgrade pip
}

# 安装依赖
install_dependencies() {
    log_info "Installing dependencies..."
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    else
        log_error "requirements.txt not found!"
        exit 1
    fi
    log_info "Dependencies installed ✓"
}

# 检查数据库连接
check_database_connection() {
    log_info "Checking database connection..."
    source .env
    
    cd user_management_module
    
    python3 -c "
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
"
    cd ..
    log_info "Database connection check completed ✓"
}

# 初始化数据库
init_database() {
    log_info "Initializing database..."
    source .env
    
    cd user_management_module
    
    python3 -c "
from app import app, db
from models import User, Plan, Customer, CRMContact, CRMActivity
import os

with app.app_context():
    try:
        # 创建所有表
        db.create_all()
        print('✓ Database tables created')
        
        # 检查是否需要创建管理员用户
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
            
        # 检查是否需要创建默认计划
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
        import traceback
        traceback.print_exc()
        exit(1)
"
    cd ..
    log_info "Database initialized ✓"
}

# 检查SMTP配置（用于邮件通知）
check_smtp_config() {
    source .env
    
    if [ -n "$SMTP_SERVER" ] && [ -n "$SMTP_USERNAME" ]; then
        log_info "SMTP configuration found ✓"
        
        cd user_management_module
        python3 -c "
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
" 2>/dev/null
        cd ..
    else
        log_warn "SMTP not configured - email notifications will be disabled"
    fi
}

# 启动应用
start_application() {
    log_header "Starting User Management Module..."
    source .env
    
    # 设置默认值
    export FLASK_ENV=${FLASK_ENV:-production}
    export PORT=${PORT:-5003}
    export HOST=${HOST:-0.0.0.0}
    
    cd user_management_module
    
    if [ "$FLASK_ENV" = "development" ]; then
        log_info "Starting in development mode..."
        log_info "Admin Panel: http://$HOST:$PORT/admin"
        log_info "CRM Dashboard: http://$HOST:$PORT/crm"
        log_info "User Portal: http://$HOST:$PORT/"
        python3 main.py
    else
        log_info "Starting in production mode with Gunicorn..."
        log_info "Admin Panel: http://$HOST:$PORT/admin"
        log_info "CRM Dashboard: http://$HOST:$PORT/crm"
        log_info "User API: http://$HOST:$PORT/api/v1"
        gunicorn --bind $HOST:$PORT --workers 4 --timeout 120 main:app
    fi
}

# 主函数
main() {
    log_header "Starting User Management Module deployment..."
    
    # 检查系统要求
    check_python
    
    # 检查配置
    check_env_config
    
    # 设置虚拟环境
    setup_virtualenv
    
    # 安装依赖
    install_dependencies
    
    # 检查数据库连接
    check_database_connection
    
    # 初始化数据库
    init_database
    
    # 检查SMTP配置
    check_smtp_config
    
    # 启动应用
    start_application
}

# 信号处理
trap 'log_info "Shutting down gracefully..."; exit 0' SIGTERM SIGINT

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "User Management Module Startup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  --dev               Run in development mode"
    echo "  --prod              Run in production mode"
    echo "  --init-db-only      Only initialize database"
    echo "  --create-admin      Create admin user"
    echo "  --check-config      Only check configuration"
    echo ""
    echo "Environment variables:"
    echo "  PORT                Port to run on (default: 5003)"
    echo "  HOST                Host to bind to (default: 0.0.0.0)"
    echo "  DATABASE_URL        Database connection string"
    echo "  FLASK_ENV           Flask environment (development/production)"
    echo "  SMTP_SERVER         SMTP server for email notifications"
    echo "  SMTP_USERNAME       SMTP username"
    echo "  SMTP_PASSWORD       SMTP password"
    echo ""
    echo "Default login:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo "  (Please change after first login)"
    echo ""
    exit 0
fi

# 处理命令行参数
if [ "$1" = "--dev" ]; then
    export FLASK_ENV=development
elif [ "$1" = "--prod" ]; then
    export FLASK_ENV=production
elif [ "$1" = "--init-db-only" ]; then
    check_env_config
    setup_virtualenv
    install_dependencies
    check_database_connection
    init_database
    log_info "Database initialization completed. Exiting."
    exit 0
elif [ "$1" = "--create-admin" ]; then
    check_env_config
    setup_virtualenv
    install_dependencies
    cd user_management_module
    python3 -c "
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    username = input('Enter admin username: ')
    email = input('Enter admin email: ')
    password = input('Enter admin password: ')
    
    if User.query.filter_by(username=username).first():
        print('User already exists')
    else:
        admin = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
            role='admin',
            is_active=True
        )
        db.session.add(admin)
        db.session.commit()
        print(f'Admin user {username} created successfully')
"
    exit 0
elif [ "$1" = "--check-config" ]; then
    check_env_config
    check_database_connection
    check_smtp_config
    log_info "Configuration check completed."
    exit 0
fi

# 运行主函数
main