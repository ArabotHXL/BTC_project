#!/bin/bash
set -e  # 立即退出

BASE_URL=${BASE_URL:-"http://localhost:5000"}

# 必需API_KEY
if [ -z "$API_KEY_1" ]; then
    echo "❌ Error: API_KEY_1 environment variable is required"
    exit 1
fi

API_KEY=$API_KEY_1

# Test 1: 健康检查并保存基线
echo "[1/6] Capturing baseline metrics..."
health=$(curl -s -f "$BASE_URL/api/intelligence/health" || exit 1)
echo "$health" | jq '.' || exit 1

# 保存初始事件计数
initial_events=$(echo "$health" | jq -r '.events.total_processed // 0')

# 新增：保存初始portfolio数据
portfolio_before=$(curl -s -f "$BASE_URL/api/treasury/overview" \
  -H "X-API-Key: $API_KEY" || exit 1)
initial_miner_count=$(echo "$portfolio_before" | jq -r '.miners // .total_miners // 0')
initial_hashrate=$(echo "$portfolio_before" | jq -r '.total_hashrate // 0')

echo "Baseline: events=$initial_events, miners=$initial_miner_count, hashrate=$initial_hashrate"

# Test 2: 新增矿机
echo "[2/6] Adding miner..."
add_response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/user-miners" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Antminer S19 XP",
    "quantity": 1,
    "hashrate": 140,
    "power": 3010
  }')

http_code=$(echo "$add_response" | tail -n1)
response_body=$(echo "$add_response" | sed '$d')

# 断言HTTP 200或201
if [[ "$http_code" != "200" && "$http_code" != "201" ]]; then
    echo "❌ Add miner failed: HTTP $http_code"
    echo "$response_body"
    exit 1
fi

# 断言success字段
success=$(echo "$response_body" | jq -r '.success // false')
if [ "$success" != "true" ]; then
    echo "❌ Add miner response success=false"
    exit 1
fi

echo "✓ Miner added successfully"

# Test 3: 等待事件处理
echo "[3/6] Waiting for event processing (5s)..."
sleep 5

# Test 4: 验证事件计数增加
echo "[4/6] Verifying event processing..."
health_after=$(curl -s -f "$BASE_URL/api/intelligence/health" || exit 1)
events_after=$(echo "$health_after" | jq -r '.events.total_processed // 0')

if [ "$events_after" -le "$initial_events" ]; then
    echo "❌ Event count did not increase (before: $initial_events, after: $events_after)"
    exit 1
fi
echo "✓ Events processed: $initial_events → $events_after"

# Test 5: 验证portfolio增量（关键修复）
echo "[5/6] Verifying portfolio delta..."
portfolio_after=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/treasury/overview" \
  -H "X-API-Key: $API_KEY")

http_code=$(echo "$portfolio_after" | tail -n1)
portfolio_body=$(echo "$portfolio_after" | sed '$d')

if [ "$http_code" != "200" ]; then
    echo "❌ Portfolio fetch failed: HTTP $http_code"
    exit 1
fi

# 关键断言：矿机数量必须增加
miner_count_after=$(echo "$portfolio_body" | jq -r '.miners // .total_miners // 0')
if [ "$miner_count_after" -le "$initial_miner_count" ]; then
    echo "❌ Miner count did not increase (before: $initial_miner_count, after: $miner_count_after)"
    echo "This indicates failed recalculation or stale cache"
    exit 1
fi

# 可选：验证hashrate也增加
hashrate_after=$(echo "$portfolio_body" | jq -r '.total_hashrate // 0')
if [ "$hashrate_after" -le "$initial_hashrate" ]; then
    echo "⚠️  Warning: Hashrate did not increase (before: $initial_hashrate, after: $hashrate_after)"
fi

echo "✓ Portfolio updated: miners $initial_miner_count→$miner_count_after, hashrate $initial_hashrate→$hashrate_after"

# Test 6: 验证Analytics端点
echo "[6/6] Verifying analytics..."
market=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/analytics/market-data" \
  -H "X-API-Key: $API_KEY")

http_code=$(echo "$market" | tail -n1)
market_body=$(echo "$market" | sed '$d')

if [ "$http_code" != "200" ]; then
    echo "❌ Market data fetch failed: HTTP $http_code"
    exit 1
fi

# 断言包含BTC价格
btc_price=$(echo "$market_body" | jq -r '.btc_price // 0')
if [ "$btc_price" -lt 1 ]; then
    echo "❌ Invalid BTC price: $btc_price"
    exit 1
fi
echo "✓ Analytics working: BTC=$btc_price"

echo "✅ E2E Test Passed"
exit 0
