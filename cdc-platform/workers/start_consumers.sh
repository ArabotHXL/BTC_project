#!/bin/bash
###############################################################################
# HashInsight CDC Platform - Consumer Startup Script
# CDC平台消费者启动脚本
#
# 用法:
#   ./start_consumers.sh all         # 启动所有消费者
#   ./start_consumers.sh portfolio   # 仅启动Portfolio消费者
#   ./start_consumers.sh intel       # 仅启动Intelligence消费者
#
# 环境变量要求:
#   - DATABASE_URL: PostgreSQL连接字符串
#   - REDIS_URL: Redis连接字符串
#   - KAFKA_BOOTSTRAP_SERVERS: Kafka broker地址
###############################################################################

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查环境变量
check_env() {
    local missing=0
    
    if [ -z "$DATABASE_URL" ]; then
        echo -e "${RED}❌ DATABASE_URL is not set${NC}"
        missing=1
    fi
    
    if [ -z "$REDIS_URL" ]; then
        echo -e "${RED}❌ REDIS_URL is not set${NC}"
        missing=1
    fi
    
    if [ -z "$KAFKA_BOOTSTRAP_SERVERS" ]; then
        echo -e "${RED}❌ KAFKA_BOOTSTRAP_SERVERS is not set${NC}"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        echo -e "${YELLOW}💡 Example:${NC}"
        echo "   export DATABASE_URL='postgresql://user:pass@localhost/dbname'"
        echo "   export REDIS_URL='redis://localhost:6379/0'"
        echo "   export KAFKA_BOOTSTRAP_SERVERS='localhost:9092'"
        exit 1
    fi
}

# 启动Portfolio消费者
start_portfolio() {
    echo -e "${GREEN}🚀 Starting Portfolio Consumer...${NC}"
    python3 portfolio_consumer.py &
    echo $! > /tmp/portfolio_consumer.pid
    echo -e "${GREEN}✅ Portfolio Consumer started (PID: $(cat /tmp/portfolio_consumer.pid))${NC}"
}

# 启动Intelligence消费者
start_intel() {
    echo -e "${GREEN}🧠 Starting Intelligence Consumer...${NC}"
    python3 intel_consumer.py &
    echo $! > /tmp/intel_consumer.pid
    echo -e "${GREEN}✅ Intelligence Consumer started (PID: $(cat /tmp/intel_consumer.pid))${NC}"
}

# 停止所有消费者
stop_all() {
    echo -e "${YELLOW}🛑 Stopping all consumers...${NC}"
    
    if [ -f /tmp/portfolio_consumer.pid ]; then
        kill $(cat /tmp/portfolio_consumer.pid) 2>/dev/null || true
        rm /tmp/portfolio_consumer.pid
        echo -e "${GREEN}✅ Portfolio Consumer stopped${NC}"
    fi
    
    if [ -f /tmp/intel_consumer.pid ]; then
        kill $(cat /tmp/intel_consumer.pid) 2>/dev/null || true
        rm /tmp/intel_consumer.pid
        echo -e "${GREEN}✅ Intelligence Consumer stopped${NC}"
    fi
}

# 主逻辑
main() {
    cd "$(dirname "$0")"
    
    case "${1:-all}" in
        all)
            check_env
            echo -e "${GREEN}========================================${NC}"
            echo -e "${GREEN}📦 Starting All CDC Consumers${NC}"
            echo -e "${GREEN}========================================${NC}"
            start_portfolio
            start_intel
            echo -e "${GREEN}✅ All consumers started${NC}"
            echo -e "${YELLOW}💡 Logs:${NC}"
            echo "   - Portfolio: /tmp/portfolio_consumer.log"
            echo "   - Intelligence: /tmp/intel_consumer.log"
            ;;
        
        portfolio)
            check_env
            start_portfolio
            ;;
        
        intel)
            check_env
            start_intel
            ;;
        
        stop)
            stop_all
            ;;
        
        status)
            echo -e "${GREEN}📊 Consumer Status:${NC}"
            if [ -f /tmp/portfolio_consumer.pid ]; then
                if ps -p $(cat /tmp/portfolio_consumer.pid) > /dev/null; then
                    echo -e "  Portfolio: ${GREEN}Running${NC} (PID: $(cat /tmp/portfolio_consumer.pid))"
                else
                    echo -e "  Portfolio: ${RED}Stopped${NC}"
                fi
            else
                echo -e "  Portfolio: ${RED}Stopped${NC}"
            fi
            
            if [ -f /tmp/intel_consumer.pid ]; then
                if ps -p $(cat /tmp/intel_consumer.pid) > /dev/null; then
                    echo -e "  Intelligence: ${GREEN}Running${NC} (PID: $(cat /tmp/intel_consumer.pid))"
                else
                    echo -e "  Intelligence: ${RED}Stopped${NC}"
                fi
            else
                echo -e "  Intelligence: ${RED}Stopped${NC}"
            fi
            ;;
        
        *)
            echo "Usage: $0 {all|portfolio|intel|stop|status}"
            echo ""
            echo "Commands:"
            echo "  all        - Start all consumers"
            echo "  portfolio  - Start Portfolio consumer only"
            echo "  intel      - Start Intelligence consumer only"
            echo "  stop       - Stop all consumers"
            echo "  status     - Show consumer status"
            exit 1
            ;;
    esac
}

# 捕获退出信号，清理资源
trap stop_all EXIT INT TERM

main "$@"
