#!/bin/bash

# HashInsight Complete Mining Platform Deployment Script
# HashInsight完整挖矿平台部署脚本

set -e

# 版本信息
PLATFORM_VERSION="2.1.0"
BUILD_DATE="2025-09-27"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 艺术字Logo
print_logo() {
    echo -e "${CYAN}"
    cat << "EOF"
    ██╗  ██╗ █████╗ ███████╗██╗  ██╗██╗███╗   ██╗███████╗██╗ ██████╗ ██╗  ██╗████████╗
    ██║  ██║██╔══██╗██╔════╝██║  ██║██║████╗  ██║██╔════╝██║██╔════╝ ██║  ██║╚══██╔══╝
    ███████║███████║███████╗███████║██║██╔██╗ ██║███████╗██║██║  ███╗███████║   ██║   
    ██╔══██║██╔══██║╚════██║██╔══██║██║██║╚██╗██║╚════██║██║██║   ██║██╔══██║   ██║   
    ██║  ██║██║  ██║███████║██║  ██║██║██║ ╚████║███████║██║╚██████╔╝██║  ██║   ██║   
    ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   
                                                                                       
          Complete Mining Platform v2.1.0 - Professional Deployment Suite              
EOF
    echo -e "${NC}"
}

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
    echo -e "\n${PURPLE}============================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}============================================${NC}"
}

log_step() {
    echo -e "\n${CYAN}[STEP]${NC} $1"
}

# 系统检查函数
check_system_requirements() {
    log_header "System Requirements Check"
    
    # 检查操作系统
    OS=$(uname -s)
    log_info "Operating System: $OS"
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python $PYTHON_VERSION detected ✓"
    
    # 检查Node.js (可选)
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        log_info "Node.js $NODE_VERSION detected ✓"
    else
        log_warn "Node.js not found. Smart contract features may be limited."
    fi
    
    # 检查Docker (可选)
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | cut -d' ' -f3)
        log_info "Docker $DOCKER_VERSION detected ✓"
        DOCKER_AVAILABLE=true
    else
        log_warn "Docker not found. Container deployment unavailable."
        DOCKER_AVAILABLE=false
    fi
    
    # 检查可用端口
    check_port() {
        if netstat -tuln 2>/dev/null | grep -q ":$1 "; then
            log_warn "Port $1 is already in use"
            return 1
        else
            log_info "Port $1 is available ✓"
            return 0
        fi
    }
    
    log_step "Checking required ports..."
    check_port 5001 || PORT_5001_BUSY=true
    check_port 5002 || PORT_5002_BUSY=true  
    check_port 5003 || PORT_5003_BUSY=true
    check_port 8080 || PORT_8080_BUSY=true
    
    # 检查磁盘空间
    AVAILABLE_SPACE=$(df . | tail -1 | awk '{print $4}')
    REQUIRED_SPACE=10485760  # 10GB in KB
    if [ "$AVAILABLE_SPACE" -lt "$REQUIRED_SPACE" ]; then
        log_warn "Low disk space. Available: $(($AVAILABLE_SPACE/1024/1024))GB, Required: 10GB"
    else
        log_info "Disk space sufficient ✓"
    fi
    
    # 检查内存
    TOTAL_MEM=$(free -m | awk 'NR==2{print $2}')
    if [ "$TOTAL_MEM" -lt 4096 ]; then
        log_warn "Low memory. Available: ${TOTAL_MEM}MB, Recommended: 4GB+"
    else
        log_info "Memory sufficient ✓"
    fi
}

# 配置检查函数
check_configurations() {
    log_header "Configuration Check"
    
    # 检查各模块配置文件
    MODULES=("mining_core_module" "web3_integration_module" "user_management_module")
    CONFIG_FILES=("config.env.template" "blockchain_config.env.template" "database_config.env.template")
    
    for i in "${!MODULES[@]}"; do
        MODULE=${MODULES[$i]}
        CONFIG=${CONFIG_FILES[$i]}
        
        log_step "Checking $MODULE configuration..."
        
        if [ ! -d "$MODULE" ]; then
            log_error "Module directory $MODULE not found!"
            exit 1
        fi
        
        if [ ! -f "$CONFIG" ]; then
            log_error "Configuration template $CONFIG not found!"
            exit 1
        fi
        
        # 检查是否有对应的.env文件
        MODULE_ENV="$MODULE/.env"
        if [ ! -f "$MODULE_ENV" ]; then
            log_warn "No .env file found for $MODULE. Will create from template."
            mkdir -p "$(dirname "$MODULE_ENV")"
            cp "$CONFIG" "$MODULE_ENV"
            log_info "Created .env file for $MODULE"
        else
            log_info "$MODULE configuration found ✓"
        fi
    done
}

# 依赖安装函数
install_dependencies() {
    log_header "Installing Dependencies"
    
    # 为每个模块创建虚拟环境并安装依赖
    MODULES=("mining_core_module" "web3_integration_module" "user_management_module")
    
    for MODULE in "${MODULES[@]}"; do
        log_step "Installing dependencies for $MODULE..."
        
        cd "$MODULE"
        
        # 创建虚拟环境
        if [ ! -d "venv" ]; then
            log_info "Creating virtual environment for $MODULE..."
            python3 -m venv venv
        fi
        
        # 激活虚拟环境
        source venv/bin/activate
        
        # 升级pip
        pip install --upgrade pip
        
        # 安装依赖
        if [ -f "requirements.txt" ]; then
            pip install -r requirements.txt
            log_info "$MODULE dependencies installed ✓"
        else
            log_error "requirements.txt not found in $MODULE!"
            cd ..
            exit 1
        fi
        
        # 检查关键依赖
        case $MODULE in
            "mining_core_module")
                python3 -c "import flask, psutil, schedule" 2>/dev/null && log_info "Core dependencies verified ✓" || log_error "Core dependencies missing!"
                ;;
            "web3_integration_module")
                python3 -c "import web3, eth_account, cryptography" 2>/dev/null && log_info "Web3 dependencies verified ✓" || log_error "Web3 dependencies missing!"
                ;;
            "user_management_module")
                python3 -c "import flask_sqlalchemy, flask_login, celery" 2>/dev/null && log_info "User management dependencies verified ✓" || log_error "User management dependencies missing!"
                ;;
        esac
        
        deactivate
        cd ..
    done
}

# 数据库初始化函数
initialize_databases() {
    log_header "Database Initialization"
    
    # 初始化各模块数据库
    MODULES=("mining_core_module" "web3_integration_module" "user_management_module")
    
    for MODULE in "${MODULES[@]}"; do
        log_step "Initializing database for $MODULE..."
        
        cd "$MODULE"
        source venv/bin/activate
        source .env
        
        # 初始化数据库
        python3 -c "
from app import app, db
with app.app_context():
    try:
        db.create_all()
        print('✓ Database initialized for $MODULE')
    except Exception as e:
        print(f'✗ Database initialization failed for $MODULE: {e}')
        exit(1)
" 2>/dev/null || log_warn "Database initialization failed for $MODULE (manual setup may be required)"
        
        deactivate
        cd ..
    done
}

# 网关配置函数
setup_gateway() {
    log_header "Setting up API Gateway"
    
    # 创建Nginx配置
    mkdir -p nginx/conf.d
    
    cat > nginx/conf.d/hashinsight_platform.conf << 'EOF'
# HashInsight Platform Nginx Configuration
upstream mining_core {
    server localhost:5001;
}

upstream web3_integration {
    server localhost:5002;
}

upstream user_management {
    server localhost:5003;
}

# Main platform server
server {
    listen 8080;
    server_name localhost;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    # Mining Core Module
    location /api/mining/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://mining_core/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Web3 Integration Module
    location /api/web3/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://web3_integration/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # User Management Module
    location /api/users/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://user_management/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Admin interfaces
    location /admin/mining/ {
        proxy_pass http://mining_core/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /admin/web3/ {
        proxy_pass http://web3_integration/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /admin/users/ {
        proxy_pass http://user_management/admin/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
    
    # Static files
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Default route - platform dashboard
    location / {
        proxy_pass http://user_management/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF
    
    log_info "Nginx configuration created ✓"
}

# 服务启动函数
start_services() {
    log_header "Starting Platform Services"
    
    # 启动模块服务
    MODULES=("mining_core_module" "web3_integration_module" "user_management_module")
    PORTS=(5001 5002 5003)
    PIDS=()
    
    for i in "${!MODULES[@]}"; do
        MODULE=${MODULES[$i]}
        PORT=${PORTS[$i]}
        
        log_step "Starting $MODULE on port $PORT..."
        
        cd "$MODULE"
        source venv/bin/activate
        source .env
        
        # 设置端口
        export PORT=$PORT
        export HOST=0.0.0.0
        
        # 启动服务
        nohup gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 main:app > ../logs/${MODULE}.log 2>&1 &
        PID=$!
        PIDS+=($PID)
        
        # 等待服务启动
        sleep 3
        
        # 检查服务状态
        if kill -0 $PID 2>/dev/null; then
            log_info "$MODULE started successfully (PID: $PID) ✓"
        else
            log_error "$MODULE failed to start!"
            exit 1
        fi
        
        deactivate
        cd ..
    done
    
    # 保存PID到文件
    echo "${PIDS[@]}" > platform.pids
    
    # 启动Nginx (如果可用)
    if command -v nginx &> /dev/null; then
        log_step "Starting Nginx gateway..."
        nginx -t -c $(pwd)/nginx/conf.d/hashinsight_platform.conf
        nginx -c $(pwd)/nginx/conf.d/hashinsight_platform.conf
        log_info "Nginx gateway started ✓"
    else
        log_warn "Nginx not available. Services accessible directly on their ports."
    fi
}

# 健康检查函数
health_check() {
    log_header "Platform Health Check"
    
    SERVICES=(
        "Mining Core:http://localhost:5001/health"
        "Web3 Integration:http://localhost:5002/health"
        "User Management:http://localhost:5003/health"
        "Platform Gateway:http://localhost:8080/health"
    )
    
    for service in "${SERVICES[@]}"; do
        name=$(echo $service | cut -d: -f1)
        url=$(echo $service | cut -d: -f2-)
        
        log_step "Checking $name..."
        
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_info "$name is healthy ✓"
        else
            log_warn "$name is not responding"
        fi
    done
}

# 停止函数
stop_services() {
    log_header "Stopping Platform Services"
    
    # 停止Nginx
    if pgrep nginx > /dev/null; then
        log_step "Stopping Nginx..."
        nginx -s quit 2>/dev/null || nginx -s stop 2>/dev/null
    fi
    
    # 停止模块服务
    if [ -f "platform.pids" ]; then
        log_step "Stopping platform services..."
        while read -r pid; do
            if kill -0 $pid 2>/dev/null; then
                kill $pid
                log_info "Stopped service (PID: $pid)"
            fi
        done < platform.pids
        rm -f platform.pids
    fi
    
    log_info "All services stopped ✓"
}

# 显示帮助函数
show_help() {
    cat << EOF
HashInsight Complete Mining Platform Deployment Script v$PLATFORM_VERSION

Usage: $0 [COMMAND] [OPTIONS]

Commands:
    install         Install and configure all modules
    start           Start all platform services
    stop            Stop all platform services
    restart         Restart all platform services
    status          Check platform status
    health          Perform health check
    logs            Show service logs
    update          Update platform
    backup          Backup platform data
    help            Show this help message

Options:
    --dev           Run in development mode
    --prod          Run in production mode (default)
    --docker        Use Docker deployment
    --skip-deps     Skip dependency installation
    --force         Force operation without confirmation

Examples:
    $0 install              # Install complete platform
    $0 start --prod         # Start in production mode
    $0 health               # Check all services
    $0 logs mining_core     # Show mining core logs

Environment Variables:
    PLATFORM_ENV            Environment (development/production)
    ENABLE_GATEWAY          Enable API gateway (true/false)
    DATABASE_HOST           Database host
    REDIS_HOST              Redis host

Services:
    Mining Core Module      http://localhost:5001
    Web3 Integration        http://localhost:5002
    User Management         http://localhost:5003
    Platform Gateway        http://localhost:8080

For detailed documentation, see COMPLETE_DEPLOYMENT_GUIDE.md
EOF
}

# 主函数
main() {
    print_logo
    
    case "${1:-install}" in
        "install")
            log_header "HashInsight Platform Installation"
            check_system_requirements
            check_configurations
            install_dependencies
            initialize_databases
            setup_gateway
            log_header "Installation Complete!"
            echo -e "\n${GREEN}Next steps:${NC}"
            echo -e "1. Review and update .env files in each module"
            echo -e "2. Run: $0 start"
            echo -e "3. Access platform at: ${CYAN}http://localhost:8080${NC}"
            ;;
        "start")
            create_directories
            start_services
            sleep 5
            health_check
            log_header "Platform Started Successfully!"
            echo -e "\n${GREEN}Platform Access URLs:${NC}"
            echo -e "• Platform Gateway: ${CYAN}http://localhost:8080${NC}"
            echo -e "• Mining Core: ${CYAN}http://localhost:5001${NC}"
            echo -e "• Web3 Integration: ${CYAN}http://localhost:5002${NC}"
            echo -e "• User Management: ${CYAN}http://localhost:5003${NC}"
            ;;
        "stop")
            stop_services
            ;;
        "restart")
            stop_services
            sleep 2
            start_services
            ;;
        "status"|"health")
            health_check
            ;;
        "logs")
            if [ -n "$2" ]; then
                tail -f logs/${2}.log
            else
                echo "Available logs:"
                ls logs/*.log 2>/dev/null || echo "No logs found"
            fi
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            echo "Unknown command: $1"
            show_help
            exit 1
            ;;
    esac
}

# 创建必要的目录
create_directories() {
    mkdir -p logs nginx/conf.d ssl backups
}

# 信号处理
trap 'log_info "Deployment interrupted"; stop_services; exit 1' SIGINT SIGTERM

# 运行主函数
main "$@"