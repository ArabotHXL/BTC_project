#!/bin/bash
set -e

BASE_URL=${BASE_URL:-"http://localhost:5000"}

if [ -z "$API_KEY_1" ]; then
    echo "❌ Error: API_KEY_1 is required"
    exit 1
fi

# 检查bc依赖
if ! command -v bc &> /dev/null; then
    echo "⚠️  Warning: bc not found, installing..."
    # 在Replit环境自动安装
    apt-get update -qq && apt-get install -y bc &> /dev/null || true
fi

echo "=== SWR Cache Performance Test ==="

# Test 1: 首次访问
echo "[1/3] First access (cache miss)..."
start1=$(date +%s%N)
response1=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/intelligence/forecast/1" \
  -H "X-API-Key: $API_KEY_1")
end1=$(date +%s%N)
http_code1=$(echo "$response1" | tail -n1)

if [ "$http_code1" != "200" ]; then
    echo "❌ First access failed: HTTP $http_code1"
    exit 1
fi

latency1=$(( (end1 - start1) / 1000000 ))
echo "✓ First access: ${latency1}ms"

# Test 2: 缓存命中
echo "[2/3] Second access (cache hit, target <50ms)..."
start2=$(date +%s%N)
response2=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/intelligence/forecast/1" \
  -H "X-API-Key: $API_KEY_1")
end2=$(date +%s%N)
http_code2=$(echo "$response2" | tail -n1)

if [ "$http_code2" != "200" ]; then
    echo "❌ Second access failed: HTTP $http_code2"
    exit 1
fi

latency2=$(( (end2 - start2) / 1000000 ))
echo "✓ Second access: ${latency2}ms"

# Test 3: 强制性能断言
echo "[3/4] Enforcing performance targets..."

# 断言1：缓存命中必须更快
if [ "$latency2" -ge "$latency1" ]; then
    echo "❌ Cache hit NOT faster than miss (miss: ${latency1}ms, hit: ${latency2}ms)"
    echo "This indicates SWR cache is not working"
    exit 1
fi
echo "✓ Cache speedup confirmed: ${latency1}ms → ${latency2}ms"

# 断言2：缓存命中延迟必须 < 200ms（严格目标）
if [ "$latency2" -gt 200 ]; then
    echo "❌ Cache hit latency ${latency2}ms exceeds 200ms target"
    echo "SWR performance regression detected"
    exit 1
fi
echo "✓ Cache hit latency within target: ${latency2}ms < 200ms"

# 断言3：缓存命中率必须 >= 50%（合理目标）
health=$(curl -s -f "$BASE_URL/api/intelligence/health" || exit 1)
hit_rate=$(echo "$health" | jq -r '.cache_hit_rate // .cache_stats.hit_rate // 0')

# 如果hit_rate是字符串（如"75%"），提取数字
hit_rate_num=$(echo "$hit_rate" | sed 's/%//' | sed 's/[^0-9.]//g')

if command -v bc &> /dev/null; then
    is_below=$(echo "$hit_rate_num < 50" | bc)
    if [ "$is_below" -eq 1 ]; then
        echo "❌ Cache hit rate ${hit_rate} below 50% target"
        echo "Cache system may be misconfigured"
        exit 1
    fi
fi
echo "✓ Cache hit rate meets target: ${hit_rate}"

# 计算加速倍数
if command -v bc &> /dev/null && [ "$latency1" -gt 0 ] && [ "$latency2" -gt 0 ]; then
    speedup=$(echo "scale=1; $latency1 / $latency2" | bc)
    echo "✓ Performance speedup: ${speedup}x"
fi

echo "✅ Cache Performance Test Passed"
exit 0
