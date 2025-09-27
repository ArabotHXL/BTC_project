#!/bin/bash

# Web3 Integration Module Startup Script
# Web3集成模块启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 检查Node.js (用于智能合约编译)
check_nodejs() {
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_info "Node.js $NODE_VERSION detected ✓"
    else
        log_warn "Node.js not found. Some smart contract features may not work."
    fi
}

# 检查环境配置文件
check_env_config() {
    if [ ! -f .env ]; then
        if [ -f blockchain_config.env.template ]; then
            log_warn ".env file not found. Creating from template..."
            cp blockchain_config.env.template .env
            log_warn "Please edit .env file with your blockchain configuration before running again."
            exit 1
        else
            log_error "No .env file or template found. Please create blockchain configuration file."
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
    log_info "Installing Python dependencies..."
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt
    else
        log_error "requirements.txt not found!"
        exit 1
    fi
    log_info "Python dependencies installed ✓"
    
    # 安装Node.js依赖 (如果存在package.json)
    if [ -f package.json ] && command -v npm &> /dev/null; then
        log_info "Installing Node.js dependencies..."
        npm install
        log_info "Node.js dependencies installed ✓"
    fi
}

# 检查区块链连接
check_blockchain_connection() {
    log_info "Checking blockchain connection..."
    source .env
    
    cd web3_integration_module
    
    python3 -c "
import os
from web3 import Web3

try:
    # 检查以太坊连接
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
"
    cd ..
    log_info "Blockchain connection check completed ✓"
}

# 初始化数据库
init_database() {
    log_info "Initializing database..."
    source .env
    
    cd web3_integration_module
    
    python3 -c "
from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('Database initialized successfully')
    except Exception as e:
        print(f'Database initialization failed: {e}')
        exit(1)
"
    cd ..
    log_info "Database initialized ✓"
}

# 编译智能合约 (如果需要)
compile_contracts() {
    if [ -d "web3_integration_module/contracts" ] && command -v npx &> /dev/null; then
        log_info "Compiling smart contracts..."
        cd web3_integration_module/contracts
        
        if [ -f package.json ]; then
            npx hardhat compile 2>/dev/null || log_warn "Smart contract compilation failed (optional)"
        fi
        
        cd ../..
        log_info "Smart contract compilation completed ✓"
    fi
}

# 启动应用
start_application() {
    log_info "Starting Web3 Integration Module..."
    source .env
    
    # 设置默认值
    export FLASK_ENV=${FLASK_ENV:-production}
    export PORT=${PORT:-5002}
    export HOST=${HOST:-0.0.0.0}
    
    cd web3_integration_module
    
    if [ "$FLASK_ENV" = "development" ]; then
        log_info "Starting in development mode..."
        python3 main.py
    else
        log_info "Starting in production mode with Gunicorn..."
        gunicorn --bind $HOST:$PORT --workers 4 --timeout 120 --worker-class eventlet main:app
    fi
}

# 主函数
main() {
    log_info "Starting Web3 Integration Module deployment..."
    
    # 检查系统要求
    check_python
    check_nodejs
    
    # 检查配置
    check_env_config
    
    # 设置虚拟环境
    setup_virtualenv
    
    # 安装依赖
    install_dependencies
    
    # 编译智能合约
    compile_contracts
    
    # 检查区块链连接
    check_blockchain_connection
    
    # 初始化数据库
    init_database
    
    # 启动应用
    start_application
}

# 信号处理
trap 'log_info "Shutting down gracefully..."; exit 0' SIGTERM SIGINT

# 显示帮助信息
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Web3 Integration Module Startup Script"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -h, --help         Show this help message"
    echo "  --dev              Run in development mode"
    echo "  --prod             Run in production mode"
    echo "  --compile-only     Only compile smart contracts"
    echo "  --check-connection Only check blockchain connection"
    echo ""
    echo "Environment variables:"
    echo "  PORT               Port to run on (default: 5002)"
    echo "  HOST               Host to bind to (default: 0.0.0.0)"
    echo "  DATABASE_URL       Database connection string"
    echo "  FLASK_ENV          Flask environment (development/production)"
    echo "  ETHEREUM_RPC_URL   Ethereum RPC endpoint"
    echo "  PRIVATE_KEY        Wallet private key"
    echo ""
    exit 0
fi

# 处理命令行参数
if [ "$1" = "--dev" ]; then
    export FLASK_ENV=development
elif [ "$1" = "--prod" ]; then
    export FLASK_ENV=production
elif [ "$1" = "--compile-only" ]; then
    compile_contracts
    exit 0
elif [ "$1" = "--check-connection" ]; then
    check_env_config
    check_blockchain_connection
    exit 0
fi

# 运行主函数
main