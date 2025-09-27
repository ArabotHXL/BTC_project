#!/bin/bash

# User Management Module Start Script
# 用户管理模块启动脚本

# 设置脚本错误时退出
set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "用户管理模块启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  start     启动应用 (默认)"
    echo "  dev       开发模式启动"
    echo "  prod      生产模式启动"
    echo "  install   安装依赖"
    echo "  init-db   初始化数据库"
    echo "  test      运行测试"
    echo "  stop      停止应用"
    echo "  restart   重启应用"
    echo "  status    查看应用状态"
    echo "  help      显示此帮助信息"
    echo ""
}

# 检查环境变量
check_env() {
    log_info "检查环境变量..."
    
    if [ -z "$SESSION_SECRET" ]; then
        log_warning "SESSION_SECRET 未设置，使用默认开发密钥"
        export SESSION_SECRET="dev-user-management-module-stable-key-2025"
    fi
    
    if [ -z "$DATABASE_URL" ]; then
        log_warning "DATABASE_URL 未设置，使用默认SQLite数据库"
        export DATABASE_URL="sqlite:///user_management.db"
    fi
    
    if [ -z "$FLASK_ENV" ]; then
        export FLASK_ENV="development"
    fi
    
    log_success "环境变量检查完成"
}

# 安装依赖
install_deps() {
    log_info "安装Python依赖..."
    
    if [ -f "requirements.txt" ]; then
        if command -v pip &> /dev/null; then
            pip install -r requirements.txt
            log_success "依赖安装完成"
        else
            log_error "pip 未找到，请先安装Python和pip"
            exit 1
        fi
    else
        log_error "requirements.txt 文件未找到"
        exit 1
    fi
}

# 初始化数据库
init_database() {
    log_info "初始化数据库..."
    
    python -c "
from app import create_app
from database import create_tables

app = create_app()
with app.app_context():
    create_tables(app)
    print('数据库初始化完成')
"
    
    log_success "数据库初始化完成"
}

# 检查应用状态
check_status() {
    if pgrep -f "python.*main.py" > /dev/null || pgrep -f "gunicorn.*main" > /dev/null; then
        log_success "应用正在运行"
        return 0
    else
        log_warning "应用未运行"
        return 1
    fi
}

# 停止应用
stop_app() {
    log_info "停止应用..."
    
    # 停止Python进程
    pkill -f "python.*main.py" 2>/dev/null || true
    pkill -f "gunicorn.*main" 2>/dev/null || true
    
    sleep 2
    
    if ! check_status > /dev/null 2>&1; then
        log_success "应用已停止"
    else
        log_error "应用停止失败"
        exit 1
    fi
}

# 开发模式启动
start_dev() {
    log_info "启动开发模式..."
    check_env
    
    export FLASK_ENV="development"
    export FLASK_DEBUG=1
    
    log_info "在端口5003启动开发服务器..."
    python main.py
}

# 生产模式启动
start_prod() {
    log_info "启动生产模式..."
    check_env
    
    export FLASK_ENV="production"
    export FLASK_DEBUG=0
    
    log_info "在端口5003启动生产服务器..."
    gunicorn --bind 0.0.0.0:5003 --workers 1 --timeout 120 --preload main:app
}

# 运行测试
run_tests() {
    log_info "运行测试..."
    
    if [ -f "test_app.py" ]; then
        python test_app.py
    else
        log_warning "测试文件未找到，跳过测试"
    fi
}

# 重启应用
restart_app() {
    log_info "重启应用..."
    stop_app
    sleep 2
    start_dev
}

# 主逻辑
main() {
    case "${1:-start}" in
        "start" | "dev")
            start_dev
            ;;
        "prod" | "production")
            start_prod
            ;;
        "install")
            install_deps
            ;;
        "init-db")
            init_database
            ;;
        "test")
            run_tests
            ;;
        "stop")
            stop_app
            ;;
        "restart")
            restart_app
            ;;
        "status")
            check_status
            ;;
        "help" | "-h" | "--help")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"