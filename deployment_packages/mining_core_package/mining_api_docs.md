# Mining Core Module API Documentation
# 挖矿核心模块API文档

## 概述 Overview

Mining Core Module提供完整的RESTful API接口，支持挖矿收益计算、批量数据处理、市场数据获取等功能。所有API都支持JSON格式的请求和响应。

## 基础信息 Base Information

- **Base URL**: `http://localhost:5001/api/v1`
- **API Version**: v1.0
- **Content-Type**: `application/json`
- **响应格式**: JSON

## 认证 Authentication

目前API为公开访问，如需要认证可在环境变量中配置：

```env
API_ACCESS_KEY=your-api-key
```

使用时在请求头中添加：
```http
Authorization: Bearer your-api-key
```

## 通用响应格式 Response Format

### 成功响应
```json
{
    "success": true,
    "data": {
        // 具体数据
    },
    "message": "Operation successful",
    "timestamp": "2025-09-27T12:00:00Z"
}
```

### 错误响应
```json
{
    "success": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "Error description",
        "details": "Detailed error information"
    },
    "timestamp": "2025-09-27T12:00:00Z"
}
```

## API端点 Endpoints

### 1. 健康检查 Health Check

#### GET /health
检查系统健康状态

**请求示例:**
```http
GET /health
```

**响应示例:**
```json
{
    "status": "healthy",
    "timestamp": "2025-09-27T12:00:00Z",
    "version": "2.1.0",
    "uptime": "1d 5h 23m",
    "services": {
        "database": "connected",
        "cache": "connected",
        "api": "running"
    }
}
```

### 2. 挖矿计算器 Mining Calculator

#### POST /api/v1/calculate
计算挖矿收益

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| hashrate | float | 是 | 算力 (TH/s) |
| power_consumption | float | 是 | 功耗 (W) |
| electricity_cost | float | 否 | 电费 ($/kWh) |
| miner_model | string | 否 | 矿机型号 |
| miner_count | integer | 否 | 矿机数量 |
| pool_fee | float | 否 | 矿池费率 (0-1) |

**请求示例:**
```http
POST /api/v1/calculate
Content-Type: application/json

{
    "hashrate": 110.0,
    "power_consumption": 3250.0,
    "electricity_cost": 0.06,
    "miner_model": "Antminer S19 Pro",
    "miner_count": 10,
    "pool_fee": 0.025
}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "daily_profit": {
            "btc": 0.00475,
            "usd": 520.85
        },
        "monthly_profit": {
            "btc": 0.14250,
            "usd": 15625.50
        },
        "yearly_profit": {
            "btc": 1.71000,
            "usd": 187506.00
        },
        "roi": {
            "days": 756,
            "months": 25.2,
            "percentage": 15.87
        },
        "network_stats": {
            "difficulty": 85768066180242,
            "hashrate": "592.50 EH/s",
            "block_reward": 3.125,
            "next_difficulty_change": "3 days"
        },
        "calculation_details": {
            "algorithm_used": "difficulty_based",
            "bitcoin_price": 109680.00,
            "electricity_cost_daily": 46.80,
            "pool_fee_applied": 2.5,
            "total_hashrate": 1100.0,
            "total_power": 32500.0
        }
    },
    "timestamp": "2025-09-27T12:00:00Z"
}
```

### 3. 批量计算 Batch Calculation

#### POST /api/v1/batch/calculate
批量处理挖矿数据计算

**请求参数:**
- 文件上传 (multipart/form-data)
- 支持格式: CSV, XLSX

**CSV格式要求:**
```csv
miner_id,model,hashrate,power_consumption,count,electricity_cost
1,Antminer S19 Pro,110,3250,10,0.06
2,Antminer S19,95,3250,5,0.08
```

**请求示例:**
```http
POST /api/v1/batch/calculate
Content-Type: multipart/form-data

file: miners.csv
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "batch_id": "batch_20250927_120000",
        "total_miners": 15,
        "processed": 15,
        "failed": 0,
        "total_stats": {
            "total_hashrate": 1650.0,
            "total_power": 48750.0,
            "daily_profit_btc": 0.07125,
            "daily_profit_usd": 781.28,
            "monthly_profit_usd": 23438.40
        },
        "individual_results": [
            {
                "miner_id": "1",
                "model": "Antminer S19 Pro",
                "daily_profit_usd": 520.85,
                "roi_days": 756
            }
        ],
        "download_links": {
            "excel": "/api/v1/batch/download/batch_20250927_120000.xlsx",
            "pdf": "/api/v1/batch/download/batch_20250927_120000.pdf"
        }
    },
    "timestamp": "2025-09-27T12:00:00Z"
}
```

#### GET /api/v1/batch/status/{batch_id}
查询批量计算状态

**请求示例:**
```http
GET /api/v1/batch/status/batch_20250927_120000
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "batch_id": "batch_20250927_120000",
        "status": "completed",
        "progress": 100,
        "created_at": "2025-09-27T12:00:00Z",
        "completed_at": "2025-09-27T12:05:00Z",
        "processing_time": "5 minutes",
        "total_items": 15,
        "processed_items": 15,
        "failed_items": 0
    }
}
```

### 4. 市场数据 Market Data

#### GET /api/v1/market/data
获取最新市场数据

**请求示例:**
```http
GET /api/v1/market/data
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "bitcoin_price": {
            "usd": 109680.00,
            "source": "coingecko",
            "last_updated": "2025-09-27T12:00:00Z"
        },
        "network_stats": {
            "difficulty": 85768066180242,
            "hashrate": "592.50 EH/s",
            "block_height": 867234,
            "next_difficulty_change": {
                "blocks_remaining": 1234,
                "estimated_time": "3 days 5 hours",
                "estimated_change": "+2.5%"
            }
        },
        "mining_economics": {
            "average_block_time": "10.2 minutes",
            "blocks_per_day": 141.18,
            "daily_btc_issuance": 441.19,
            "network_revenue_daily": 48376830.00
        }
    },
    "timestamp": "2025-09-27T12:00:00Z"
}
```

#### GET /api/v1/market/history
获取历史市场数据

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| days | integer | 否 | 历史天数 (默认30) |
| interval | string | 否 | 数据间隔 (hour/day/week) |

**请求示例:**
```http
GET /api/v1/market/history?days=7&interval=day
```

### 5. 矿机数据 Miner Data

#### GET /api/v1/miners/models
获取支持的矿机型号

**请求示例:**
```http
GET /api/v1/miners/models
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "miners": [
            {
                "model": "Antminer S19 Pro",
                "manufacturer": "Bitmain",
                "hashrate": 110.0,
                "power_consumption": 3250.0,
                "efficiency": 29.5,
                "release_date": "2021-05-01",
                "status": "active"
            },
            {
                "model": "Antminer S19j Pro",
                "manufacturer": "Bitmain", 
                "hashrate": 104.0,
                "power_consumption": 3068.0,
                "efficiency": 29.5,
                "release_date": "2021-08-01",
                "status": "active"
            }
        ],
        "total_count": 25
    }
}
```

#### POST /api/v1/miners/models
添加新矿机型号 (管理员功能)

**请求示例:**
```http
POST /api/v1/miners/models
Content-Type: application/json

{
    "model": "Custom Miner X1",
    "manufacturer": "Custom",
    "hashrate": 120.0,
    "power_consumption": 3000.0,
    "efficiency": 25.0
}
```

### 6. 分析和报告 Analytics & Reports

#### GET /api/v1/analytics/profitability
获取盈利能力分析

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| hashrate | float | 是 | 算力 (TH/s) |
| electricity_cost | float | 是 | 电费 ($/kWh) |
| period | string | 否 | 分析周期 (30d/90d/1y) |

**请求示例:**
```http
GET /api/v1/analytics/profitability?hashrate=110&electricity_cost=0.06&period=90d
```

#### POST /api/v1/reports/generate
生成分析报告

**请求示例:**
```http
POST /api/v1/reports/generate
Content-Type: application/json

{
    "report_type": "profitability_analysis",
    "format": "pdf",
    "data": {
        "hashrate": 110.0,
        "power_consumption": 3250.0,
        "electricity_cost": 0.06,
        "analysis_period": "90d"
    },
    "options": {
        "include_charts": true,
        "include_recommendations": true
    }
}
```

## 错误代码 Error Codes

| 错误代码 | HTTP状态码 | 说明 |
|----------|------------|------|
| INVALID_REQUEST | 400 | 请求参数无效 |
| UNAUTHORIZED | 401 | 未授权访问 |
| FORBIDDEN | 403 | 访问被拒绝 |
| NOT_FOUND | 404 | 资源不存在 |
| METHOD_NOT_ALLOWED | 405 | 方法不允许 |
| VALIDATION_ERROR | 422 | 数据验证失败 |
| RATE_LIMIT_EXCEEDED | 429 | 请求频率超限 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |
| SERVICE_UNAVAILABLE | 503 | 服务不可用 |

## 速率限制 Rate Limiting

- 默认限制: 60 请求/分钟
- 批量计算: 10 请求/分钟
- 报告生成: 5 请求/分钟

超出限制时会返回 429 状态码:
```json
{
    "success": false,
    "error": {
        "code": "RATE_LIMIT_EXCEEDED",
        "message": "Too many requests",
        "retry_after": 60
    }
}
```

## SDK和示例代码 SDK & Examples

### Python示例
```python
import requests

# 基础配置
BASE_URL = "http://localhost:5001/api/v1"

# 挖矿计算
def calculate_mining_profit(hashrate, power, electricity_cost):
    url = f"{BASE_URL}/calculate"
    data = {
        "hashrate": hashrate,
        "power_consumption": power,
        "electricity_cost": electricity_cost
    }
    
    response = requests.post(url, json=data)
    return response.json()

# 使用示例
result = calculate_mining_profit(110.0, 3250.0, 0.06)
print(f"Daily profit: ${result['data']['daily_profit']['usd']}")
```

### JavaScript示例
```javascript
// 挖矿计算
async function calculateMiningProfit(hashrate, power, electricityCost) {
    const response = await fetch('http://localhost:5001/api/v1/calculate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            hashrate: hashrate,
            power_consumption: power,
            electricity_cost: electricityCost
        })
    });
    
    return response.json();
}

// 使用示例
calculateMiningProfit(110.0, 3250.0, 0.06)
    .then(result => {
        console.log(`Daily profit: $${result.data.daily_profit.usd}`);
    });
```

### cURL示例
```bash
# 健康检查
curl -X GET http://localhost:5001/health

# 挖矿计算
curl -X POST http://localhost:5001/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{
    "hashrate": 110.0,
    "power_consumption": 3250.0,
    "electricity_cost": 0.06,
    "miner_model": "Antminer S19 Pro"
  }'

# 获取市场数据
curl -X GET http://localhost:5001/api/v1/market/data

# 批量上传
curl -X POST http://localhost:5001/api/v1/batch/calculate \
  -F "file=@miners.csv"
```

## WebSocket接口 WebSocket API

### 实时数据推送
```javascript
// 连接WebSocket
const ws = new WebSocket('ws://localhost:5001/ws/mining-data');

// 监听实时数据
ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('实时数据:', data);
};

// 订阅特定数据类型
ws.send(JSON.stringify({
    action: 'subscribe',
    topics: ['bitcoin_price', 'network_difficulty', 'hashrate']
}));
```

## 最佳实践 Best Practices

### 1. 错误处理
```python
try:
    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    
    if not result.get('success'):
        print(f"API错误: {result.get('error', {}).get('message')}")
        
except requests.exceptions.Timeout:
    print("请求超时")
except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}")
```

### 2. 重试机制
```python
import time
from functools import wraps

def retry(max_attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
            return None
        return wrapper
    return decorator

@retry(max_attempts=3)
def api_call():
    # API调用代码
    pass
```

### 3. 数据缓存
```python
import time

class APICache:
    def __init__(self, ttl=300):  # 5分钟TTL
        self.cache = {}
        self.ttl = ttl
    
    def get(self, key):
        if key in self.cache:
            data, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return data
            del self.cache[key]
        return None
    
    def set(self, key, data):
        self.cache[key] = (data, time.time())
```

## 版本更新 Version Updates

### v1.0 (当前版本)
- 基础挖矿计算API
- 批量处理功能
- 市场数据获取
- 报告生成

### 计划中的功能
- v1.1: WebSocket实时数据推送
- v1.2: 高级分析API
- v1.3: 机器学习预测API
- v2.0: GraphQL支持

---

**技术支持**: api-support@hashinsight.net  
**文档更新**: 2025-09-27  
**API版本**: v1.0