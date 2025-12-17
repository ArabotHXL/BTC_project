.PHONY: help up down logs migrate seed connect register test health clean

# 默认目标
help:
	@echo "HashInsight CDC Platform - Makefile Commands"
	@echo "=============================================="
	@echo "  make up          - 启动所有服务"
	@echo "  make down        - 停止所有服务"
	@echo "  make logs        - 查看所有日志"
	@echo "  make migrate     - 运行数据库迁移"
	@echo "  make seed        - 填充测试数据"
	@echo "  make connect     - 检查Kafka Connect状态"
	@echo "  make register    - 注册Debezium连接器"
	@echo "  make test        - 运行验收测试"
	@echo "  make health      - 检查系统健康"
	@echo "  make clean       - 清理所有数据和容器"
	@echo ""

# 启动所有服务
up:
	@echo "🚀 启动CDC平台..."
	docker-compose up -d
	@echo "⏳ 等待服务就绪..."
	@sleep 10
	@echo "✅ 服务已启动！"
	@make health

# 停止所有服务
down:
	@echo "🛑 停止CDC平台..."
	docker-compose down
	@echo "✅ 已停止"

# 查看日志
logs:
	docker-compose logs -f

# 数据库迁移
migrate:
	@echo "📊 运行数据库迁移..."
	docker-compose exec postgres psql -U hashinsight -d hashinsight -f /docker-entrypoint-initdb.d/001_cdc_foundation.sql
	@echo "✅ 迁移完成"

# 填充测试数据
seed:
	@echo "🌱 填充测试数据..."
	docker-compose exec web python scripts/seed_data.py
	@echo "✅ 数据已填充"

# 检查Kafka Connect
connect:
	@echo "🔌 检查Kafka Connect状态..."
	@curl -s http://localhost:8083/ | jq '.'
	@echo ""
	@curl -s http://localhost:8083/connectors | jq '.'

# 注册Debezium连接器
register:
	@echo "📡 注册Debezium Outbox连接器..."
	@curl -X POST -H "Content-Type: application/json" \
		--data @connectors/outbox-connector.json \
		http://localhost:8083/connectors
	@echo ""
	@echo "✅ 连接器已注册"
	@sleep 3
	@make connect

# 验收测试
test:
	@echo "🧪 运行验收测试..."
	@bash scripts/acceptance_test.sh

# 健康检查
health:
	@echo "🏥 系统健康检查..."
	@echo "PostgreSQL: "
	@docker-compose exec postgres pg_isready -U hashinsight || echo "❌ 失败"
	@echo ""
	@echo "Redis: "
	@docker-compose exec redis redis-cli ping || echo "❌ 失败"
	@echo ""
	@echo "Kafka: "
	@docker-compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo "✅ OK" || echo "❌ 失败"
	@echo ""
	@echo "Kafka Connect: "
	@curl -s http://localhost:8083/connectors | jq 'length' | xargs echo "连接器数量: " || echo "❌ 失败"
	@echo ""
	@echo "Web API: "
	@curl -s http://localhost:5000/api/health | jq '.status' || echo "❌ 失败"

# 清理所有数据
clean:
	@echo "🗑️  清理所有数据..."
	docker-compose down -v
	@echo "✅ 已清理"
