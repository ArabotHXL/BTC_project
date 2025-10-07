#!/bin/bash
set -e

BASE_URL=${BASE_URL:-"http://localhost:5000"}

if [ -z "$API_KEY_1" ]; then
    echo "❌ Error: API_KEY_1 is required"
    exit 1
fi

echo "=== API Permission Test ==="

# Test 1: 无API Key应返回401或403
echo "[1/5] Testing no API key (expect 401/403)..."
http_code=$(curl -s -w "%{http_code}" -o /dev/null "$BASE_URL/api/treasury/overview")
if [[ "$http_code" != "401" && "$http_code" != "403" ]]; then
    echo "❌ Expected 401/403 but got $http_code"
    exit 1
fi
echo "✓ Correctly denied: $http_code"

# Test 2: 有效API Key应成功
echo "[2/5] Testing valid API key..."
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/treasury/overview" \
  -H "X-API-Key: $API_KEY_1")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" != "200" ]; then
    echo "❌ Valid key failed: HTTP $http_code"
    exit 1
fi
echo "✓ Valid key accepted"

# Test 3: CRM权限测试（403应视为失败）
echo "[3/5] Testing CRM sync permission..."
http_code=$(curl -s -w "%{http_code}" -o /dev/null -X POST \
  "$BASE_URL/api/crm-integration/sync/customer" \
  -H "X-API-Key: $API_KEY_1" \
  -H "Content-Type: application/json" \
  -d '{"customer_id": 1}')

# 关键修复：403表示无权限，应失败
if [[ "$http_code" == "403" ]]; then
    echo "❌ CRM permission denied (403): API key lacks CRM_SYNC permission"
    exit 1
elif [[ "$http_code" != "200" && "$http_code" != "201" && "$http_code" != "503" ]]; then
    echo "❌ Unexpected CRM response: $http_code"
    exit 1
fi

# 503是可接受的（功能未启用）
if [ "$http_code" == "503" ]; then
    echo "✓ CRM permission check: 503 (feature disabled)"
else
    echo "✓ CRM permission granted: $http_code"
fi

echo "[4/5] Testing Web3 mint permission..."
http_code=$(curl -s -w "%{http_code}" -o /dev/null -X POST \
  "$BASE_URL/api/web3/sla/mint-request" \
  -H "X-API-Key: $API_KEY_1" \
  -H "Content-Type: application/json" \
  -d '{"recipient": "0x123"}')

if [[ "$http_code" == "403" ]]; then
    echo "❌ Web3 permission denied (403): API key lacks WEB3_MINT permission"
    exit 1
elif [[ "$http_code" != "200" && "$http_code" != "201" && "$http_code" != "503" ]]; then
    echo "❌ Unexpected Web3 response: $http_code"
    exit 1
fi

if [ "$http_code" == "503" ]; then
    echo "✓ Web3 permission check: 503 (feature disabled)"
else
    echo "✓ Web3 permission granted: $http_code"
fi

echo "[5/5] Testing Treasury execution permission..."
http_code=$(curl -s -w "%{http_code}" -o /dev/null -X POST \
  "$BASE_URL/api/treasury-exec/execute" \
  -H "X-API-Key: $API_KEY_1" \
  -H "Content-Type: application/json" \
  -d '{"action": "sell"}')

if [[ "$http_code" == "403" ]]; then
    echo "❌ Treasury permission denied (403): API key lacks TREASURY_TRADE permission"
    exit 1
elif [[ "$http_code" != "200" && "$http_code" != "201" && "$http_code" != "503" ]]; then
    echo "❌ Unexpected Treasury response: $http_code"
    exit 1
fi

if [ "$http_code" == "503" ]; then
    echo "✓ Treasury permission check: 503 (feature disabled)"
else
    echo "✓ Treasury permission granted: $http_code"
fi

echo "✅ Permission Test Passed"
exit 0
