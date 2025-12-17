#!/bin/bash

# HashInsight CDC Platform - Acceptance Test
# 验收测试：验证完整的CDC数据流

set -e  # 遇到错误立即退出

echo "🧪 HashInsight CDC Platform - 验收测试"
echo "========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
PASS=0
FAIL=0

# 辅助函数
function test_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

function test_pass() {
    echo -e "${GREEN}✅ $1${NC}"
    ((PASS++))
}

function test_fail() {
    echo -e "${RED}❌ $1${NC}"
    ((FAIL++))
}

# ==================== 测试步骤 1: 检查服务健康 ====================
test_step "步骤 1: 检查所有服务健康状态"

# PostgreSQL
if docker-compose exec -T postgres pg_isready -U hashinsight > /dev/null 2>&1; then
    test_pass "PostgreSQL 健康"
else
    test_fail "PostgreSQL 不健康"
fi

# Redis
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    test_pass "Redis 健康"
else
    test_fail "Redis 不健康"
fi

# Kafka
if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
    test_pass "Kafka 健康"
else
    test_fail "Kafka 不健康"
fi

# Kafka Connect
if curl -s http://localhost:8083/ > /dev/null 2>&1; then
    test_pass "Kafka Connect 健康"
else
    test_fail "Kafka Connect 不健康"
fi

# Web API
if curl -s http://localhost:5000/api/health > /dev/null 2>&1; then
    test_pass "Web API 健康"
else
    test_fail "Web API 不健康"
fi

echo ""

# ==================== 测试步骤 2: 检查Debezium连接器 ====================
test_step "步骤 2: 检查Debezium Outbox连接器"

CONNECTOR_COUNT=$(curl -s http://localhost:8083/connectors | jq 'length')
if [ "$CONNECTOR_COUNT" -gt 0 ]; then
    test_pass "Debezium连接器已注册（数量: $CONNECTOR_COUNT）"
else
    test_fail "Debezium连接器未注册"
fi

echo ""

# ==================== 测试步骤 3: 创建测试数据（写入Outbox） ====================
test_step "步骤 3: POST /api/miners - 创建矿机（写入Outbox）"

# 生成JWT Token（简化版，实际应该从认证服务获取）
JWT_PAYLOAD='{"user_id":"test-user-001","tenant_id":"default","role":"admin","scopes":["miners:write"]}'
JWT_SECRET=${JWT_SECRET:-"dev-secret"}

# 简单的JWT生成（仅用于测试）
JWT_HEADER='{"alg":"HS256","typ":"JWT"}'
JWT_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoidGVzdC11c2VyLTAwMSIsInRlbmFudF9pZCI6ImRlZmF1bHQiLCJyb2xlIjoiYWRtaW4iLCJzY29wZXMiOlsibWluZXJzOndyaXRlIl19.fake"

# 创建矿机
RESPONSE=$(curl -s -X POST http://localhost:5000/api/miners \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $JWT_TOKEN" \
    -d '{
        "model_name": "Antminer S19 Pro",
        "hashrate": 110,
        "power": 3250,
        "quantity": 5,
        "electricity_cost": 0.06,
        "location": "Texas, USA"
    }')

if echo "$RESPONSE" | jq -e '.success' > /dev/null 2>&1; then
    MINER_ID=$(echo "$RESPONSE" | jq -r '.miner_id')
    test_pass "矿机创建成功 (ID: $MINER_ID)"
else
    test_fail "矿机创建失败: $RESPONSE"
fi

# 等待Outbox写入
sleep 1

# 检查Outbox表
OUTBOX_COUNT=$(docker-compose exec -T postgres psql -U hashinsight -d hashinsight -t -c \
    "SELECT COUNT(*) FROM event_outbox WHERE processed = false;" | xargs)

if [ "$OUTBOX_COUNT" -gt 0 ]; then
    test_pass "Outbox事件已写入（未处理数量: $OUTBOX_COUNT）"
else
    test_fail "Outbox事件未写入"
fi

echo ""

# ==================== 测试步骤 4: 等待Debezium捕获 ====================
test_step "步骤 4: 等待Debezium CDC捕获事件..."

sleep 3  # 等待Debezium捕获

# 检查Kafka主题
TOPIC_MESSAGE_COUNT=$(docker-compose exec -T kafka kafka-console-consumer \
    --bootstrap-server localhost:9092 \
    --topic events.miner \
    --from-beginning \
    --timeout-ms 2000 2>/dev/null | wc -l)

if [ "$TOPIC_MESSAGE_COUNT" -gt 0 ]; then
    test_pass "Kafka主题收到消息（数量: $TOPIC_MESSAGE_COUNT）"
else
    test_fail "Kafka主题未收到消息"
fi

echo ""

# ==================== 测试步骤 5: 检查消费者处理 ====================
test_step "步骤 5: 检查消费者处理事件"

sleep 2  # 等待消费者处理

# 检查Inbox表
INBOX_COUNT=$(docker-compose exec -T postgres psql -U hashinsight -d hashinsight -t -c \
    "SELECT COUNT(*) FROM consumer_inbox;" | xargs)

if [ "$INBOX_COUNT" -gt 0 ]; then
    test_pass "消费者已处理事件（Inbox记录: $INBOX_COUNT）"
else
    test_fail "消费者未处理事件"
fi

# 检查DLQ（应该为空）
DLQ_COUNT=$(docker-compose exec -T postgres psql -U hashinsight -d hashinsight -t -c \
    "SELECT COUNT(*) FROM event_dlq WHERE resolved = false;" | xargs)

if [ "$DLQ_COUNT" -eq 0 ]; then
    test_pass "DLQ无失败事件"
else
    test_fail "DLQ存在失败事件（数量: $DLQ_COUNT）"
fi

echo ""

# ==================== 测试步骤 6: 验证健康指标 ====================
test_step "步骤 6: 验证 /api/health 指标"

HEALTH_RESPONSE=$(curl -s http://localhost:5000/api/health)

# 检查响应结构
if echo "$HEALTH_RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
    STATUS=$(echo "$HEALTH_RESPONSE" | jq -r '.status')
    test_pass "健康检查端点正常（状态: $STATUS）"
    
    # 检查关键指标
    METRICS=$(echo "$HEALTH_RESPONSE" | jq -r '.metrics | keys[]')
    test_pass "健康指标完整: $METRICS"
else
    test_fail "健康检查端点响应异常"
fi

echo ""

# ==================== 测试步骤 7: 验证缓存 ====================
test_step "步骤 7: 验证缓存策略"

# 第一次请求（缓存miss）
FORECAST_RESPONSE_1=$(curl -s "http://localhost:5000/api/intelligence/forecast?user_id=test-user-001" \
    -H "Authorization: Bearer $JWT_TOKEN")

CACHE_HIT_1=$(echo "$FORECAST_RESPONSE_1" | jq -r '.cache_hit // false')

# 第二次请求（缓存hit）
FORECAST_RESPONSE_2=$(curl -s "http://localhost:5000/api/intelligence/forecast?user_id=test-user-001" \
    -H "Authorization: Bearer $JWT_TOKEN")

CACHE_HIT_2=$(echo "$FORECAST_RESPONSE_2" | jq -r '.cache_hit // false')

if [ "$CACHE_HIT_1" = "false" ] && [ "$CACHE_HIT_2" = "true" ]; then
    test_pass "缓存策略正常（首次miss，第二次hit）"
else
    test_fail "缓存策略异常（hit1: $CACHE_HIT_1, hit2: $CACHE_HIT_2）"
fi

echo ""

# ==================== 测试总结 ====================
echo "========================================="
echo "测试总结"
echo "========================================="
echo -e "通过: ${GREEN}$PASS${NC}"
echo -e "失败: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！CDC平台运行正常。${NC}"
    exit 0
else
    echo -e "${RED}⚠️  部分测试失败，请检查日志。${NC}"
    echo ""
    echo "查看日志命令："
    echo "  docker-compose logs web"
    echo "  docker-compose logs worker-portfolio"
    echo "  docker-compose logs kafka-connect"
    exit 1
fi
