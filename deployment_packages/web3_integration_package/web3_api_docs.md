# Web3 Integration Module API Documentation
# Web3集成模块API文档

## 概述 Overview

Web3 Integration Module提供完整的区块链集成API，支持钱包管理、智能合约交互、NFT铸造、加密货币支付等功能。所有API都支持JSON格式的请求和响应。

## 基础信息 Base Information

- **Base URL**: `http://localhost:5002/api/v1`
- **API Version**: v1.0
- **Content-Type**: `application/json`
- **响应格式**: JSON

## 认证 Authentication

使用API密钥进行认证：

```http
Authorization: Bearer your-web3-api-key
```

配置方式：
```env
WEB3_API_ACCESS_KEY=your-secure-api-key
```

## 通用响应格式 Response Format

### 成功响应
```json
{
    "success": true,
    "data": {
        // 具体数据
    },
    "transaction_hash": "0x...", // 如果涉及区块链交易
    "block_number": 18450000,   // 区块号
    "timestamp": "2025-09-27T12:00:00Z"
}
```

### 错误响应
```json
{
    "success": false,
    "error": {
        "code": "BLOCKCHAIN_ERROR",
        "message": "Transaction failed",
        "details": "Insufficient gas fee",
        "transaction_hash": "0x..." // 如果有
    },
    "timestamp": "2025-09-27T12:00:00Z"
}
```

## API端点 Endpoints

### 1. 健康检查 Health Check

#### GET /health
检查系统和区块链连接状态

**请求示例:**
```http
GET /health
```

**响应示例:**
```json
{
    "status": "healthy",
    "blockchain_status": {
        "ethereum": {
            "connected": true,
            "latest_block": 18450000,
            "chain_id": 1,
            "network": "mainnet"
        }
    },
    "services": {
        "database": "connected",
        "redis": "connected",
        "ipfs": "connected"
    },
    "version": "2.1.0",
    "uptime": "2d 5h 23m"
}
```

### 2. 钱包管理 Wallet Management

#### POST /api/v1/wallet/create
创建新钱包

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| name | string | 是 | 钱包名称 |
| type | string | 是 | 钱包类型 (hot_wallet/cold_wallet) |
| password | string | 否 | 钱包密码 |

**请求示例:**
```http
POST /api/v1/wallet/create
Content-Type: application/json

{
    "name": "Mining Payment Wallet",
    "type": "hot_wallet",
    "password": "secure-password"
}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "address": "0x742d35Cc6636C0532925a3b8D6f1Ff59537BA23d",
        "name": "Mining Payment Wallet",
        "type": "hot_wallet",
        "created_at": "2025-09-27T12:00:00Z",
        "encrypted_private_key": "encrypted_key_data"
    }
}
```

#### GET /api/v1/wallet/{address}/balance
查询钱包余额

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| token | string | 否 | 代币符号 (ETH/USDC/USDT) |

**请求示例:**
```http
GET /api/v1/wallet/0x742d35Cc6636C0532925a3b8D6f1Ff59537BA23d/balance?token=ETH
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "address": "0x742d35Cc6636C0532925a3b8D6f1Ff59537BA23d",
        "balances": {
            "ETH": {
                "balance": "2.5",
                "balance_wei": "2500000000000000000",
                "usd_value": "4350.00"
            },
            "USDC": {
                "balance": "1000.50",
                "decimals": 6,
                "contract_address": "0xA0b86a33E6417bfD4032198c4B9Ba15A5B00B8b8"
            }
        },
        "total_usd_value": "5350.50"
    }
}
```

#### POST /api/v1/wallet/send
发送交易

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| from | string | 是 | 发送方地址 |
| to | string | 是 | 接收方地址 |
| amount | string | 是 | 金额 |
| token | string | 否 | 代币类型 (默认ETH) |
| gas_price | string | 否 | Gas价格 (gwei) |

**请求示例:**
```http
POST /api/v1/wallet/send
Content-Type: application/json

{
    "from": "0x742d35Cc6636C0532925a3b8D6f1Ff59537BA23d",
    "to": "0x1234567890123456789012345678901234567890",
    "amount": "0.1",
    "token": "ETH",
    "gas_price": "20"
}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "transaction_hash": "0xabc123...",
        "from": "0x742d35Cc6636C0532925a3b8D6f1Ff59537BA23d",
        "to": "0x1234567890123456789012345678901234567890",
        "amount": "0.1",
        "token": "ETH",
        "gas_used": "21000",
        "gas_price": "20000000000",
        "status": "pending"
    },
    "transaction_hash": "0xabc123...",
    "block_number": null
}
```

### 3. 智能合约管理 Smart Contract Management

#### POST /api/v1/contracts/deploy
部署智能合约

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| contract_name | string | 是 | 合约名称 |
| constructor_args | array | 否 | 构造函数参数 |
| gas_limit | integer | 否 | Gas限制 |

**请求示例:**
```http
POST /api/v1/contracts/deploy
Content-Type: application/json

{
    "contract_name": "MiningDataRegistry",
    "constructor_args": ["HashInsight Mining", "MINING"],
    "gas_limit": 2000000
}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "contract_address": "0x9876543210987654321098765432109876543210",
        "transaction_hash": "0xdef456...",
        "contract_name": "MiningDataRegistry",
        "deployed_by": "0x742d35Cc6636C0532925a3b8D6f1Ff59537BA23d",
        "gas_used": "1800000",
        "deployment_time": "2025-09-27T12:05:00Z"
    },
    "transaction_hash": "0xdef456..."
}
```

#### POST /api/v1/contracts/{address}/call
调用智能合约方法

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| method | string | 是 | 合约方法名 |
| args | array | 否 | 方法参数 |
| value | string | 否 | 发送的ETH数量 |

**请求示例:**
```http
POST /api/v1/contracts/0x9876543210987654321098765432109876543210/call
Content-Type: application/json

{
    "method": "registerMiningData",
    "args": [
        "miner_001",
        "2025-09-27",
        "100000000000000",
        "online"
    ]
}
```

### 4. NFT管理 NFT Management

#### POST /api/v1/nft/mint
铸造NFT

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| to | string | 是 | 接收方地址 |
| metadata | object | 是 | NFT元数据 |
| token_id | integer | 否 | 指定代币ID |

**请求示例:**
```http
POST /api/v1/nft/mint
Content-Type: application/json

{
    "to": "0x1234567890123456789012345678901234567890",
    "metadata": {
        "name": "Mining SLA Certificate #001",
        "description": "Proof of mining service agreement compliance",
        "image": "ipfs://QmYourImageHash",
        "attributes": [
            {"trait_type": "Mining Period", "value": "30 days"},
            {"trait_type": "Hashrate Guaranteed", "value": "100 TH/s"},
            {"trait_type": "Uptime", "value": "99.9%"},
            {"trait_type": "Issue Date", "value": "2025-09-27"}
        ]
    }
}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "token_id": 1001,
        "contract_address": "0x...",
        "to": "0x1234567890123456789012345678901234567890",
        "metadata_uri": "ipfs://QmMetadataHash",
        "image_uri": "ipfs://QmImageHash",
        "transaction_hash": "0xghi789...",
        "gas_used": "150000"
    },
    "transaction_hash": "0xghi789..."
}
```

#### GET /api/v1/nft/{contract_address}/{token_id}
获取NFT详情

**请求示例:**
```http
GET /api/v1/nft/0x.../1001
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "token_id": 1001,
        "contract_address": "0x...",
        "owner": "0x1234567890123456789012345678901234567890",
        "metadata": {
            "name": "Mining SLA Certificate #001",
            "description": "Proof of mining service agreement compliance",
            "image": "ipfs://QmYourImageHash",
            "attributes": [...]
        },
        "mint_transaction": "0xghi789...",
        "mint_block": 18450100,
        "mint_date": "2025-09-27T12:10:00Z"
    }
}
```

### 5. 支付处理 Payment Processing

#### POST /api/v1/payment/create
创建支付请求

**请求参数:**
| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| amount | string | 是 | 支付金额 |
| currency | string | 是 | 支付币种 |
| description | string | 否 | 支付描述 |
| callback_url | string | 否 | 回调URL |
| expires_in | integer | 否 | 过期时间(秒) |

**请求示例:**
```http
POST /api/v1/payment/create
Content-Type: application/json

{
    "amount": "100.00",
    "currency": "USDC",
    "description": "Mining hosting service - Month 1",
    "callback_url": "https://your-app.com/webhook/payment",
    "expires_in": 3600
}
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "payment_id": "pay_1234567890",
        "payment_address": "0x...",
        "amount": "100.00",
        "currency": "USDC",
        "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
        "expires_at": "2025-09-27T13:00:00Z",
        "status": "pending"
    }
}
```

#### GET /api/v1/payment/{payment_id}
查询支付状态

**请求示例:**
```http
GET /api/v1/payment/pay_1234567890
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "payment_id": "pay_1234567890",
        "amount": "100.00",
        "currency": "USDC",
        "status": "completed",
        "transaction_hash": "0xjkl012...",
        "confirmation_count": 12,
        "paid_at": "2025-09-27T12:15:00Z",
        "confirmed_at": "2025-09-27T12:20:00Z"
    }
}
```

### 6. DeFi集成 DeFi Integration

#### POST /api/v1/defi/swap
代币交换

**请求示例:**
```http
POST /api/v1/defi/swap
Content-Type: application/json

{
    "token_in": "ETH",
    "token_out": "USDC",
    "amount_in": "1.0",
    "slippage": "0.5",
    "deadline": 1800
}
```

#### GET /api/v1/defi/price
获取代币价格

**请求示例:**
```http
GET /api/v1/defi/price?token=ETH&vs_currency=USD
```

### 7. 区块链监控 Blockchain Monitoring

#### GET /api/v1/blockchain/status
获取区块链状态

**请求示例:**
```http
GET /api/v1/blockchain/status
```

**响应示例:**
```json
{
    "success": true,
    "data": {
        "network": "mainnet",
        "chain_id": 1,
        "latest_block": 18450000,
        "gas_price": {
            "safe": "15",
            "standard": "20",
            "fast": "25"
        },
        "network_congestion": "medium",
        "avg_block_time": "12.5"
    }
}
```

#### GET /api/v1/blockchain/transaction/{hash}
查询交易详情

**请求示例:**
```http
GET /api/v1/blockchain/transaction/0xabc123...
```

## WebSocket实时事件 WebSocket Real-time Events

### 连接WebSocket
```javascript
const ws = new WebSocket('ws://localhost:5002/ws/blockchain-events');

ws.onopen = function() {
    // 订阅事件
    ws.send(JSON.stringify({
        action: 'subscribe',
        events: ['payment_received', 'nft_minted', 'contract_event']
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('收到事件:', data);
};
```

### 事件类型
```json
{
    "event_type": "payment_received",
    "data": {
        "payment_id": "pay_1234567890",
        "amount": "100.00",
        "currency": "USDC",
        "transaction_hash": "0x..."
    },
    "timestamp": "2025-09-27T12:15:00Z"
}
```

## 错误码 Error Codes

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| INVALID_ADDRESS | 400 | 无效的地址格式 |
| INSUFFICIENT_BALANCE | 400 | 余额不足 |
| INVALID_PRIVATE_KEY | 400 | 无效的私钥 |
| TRANSACTION_FAILED | 400 | 交易失败 |
| CONTRACT_NOT_FOUND | 404 | 合约不存在 |
| GAS_LIMIT_EXCEEDED | 400 | Gas限制超出 |
| NETWORK_ERROR | 503 | 网络连接错误 |
| BLOCKCHAIN_TIMEOUT | 408 | 区块链请求超时 |

## 限流 Rate Limiting

- 钱包操作: 10 请求/分钟
- 交易发送: 5 请求/分钟
- NFT铸造: 20 请求/小时
- 查询操作: 100 请求/分钟

## SDK示例 SDK Examples

### Python示例
```python
import requests
from web3 import Web3

class Web3API:
    def __init__(self, base_url, api_key):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
    
    def create_wallet(self, name, wallet_type='hot_wallet'):
        data = {'name': name, 'type': wallet_type}
        response = requests.post(
            f"{self.base_url}/wallet/create",
            json=data,
            headers=self.headers
        )
        return response.json()
    
    def mint_nft(self, to_address, metadata):
        data = {'to': to_address, 'metadata': metadata}
        response = requests.post(
            f"{self.base_url}/nft/mint",
            json=data,
            headers=self.headers
        )
        return response.json()

# 使用示例
api = Web3API('http://localhost:5002/api/v1', 'your-api-key')

# 创建钱包
wallet = api.create_wallet('Mining Wallet')
print(f"新钱包地址: {wallet['data']['address']}")

# 铸造NFT
metadata = {
    'name': 'Mining Certificate',
    'description': 'Proof of mining service',
    'attributes': [
        {'trait_type': 'Duration', 'value': '30 days'}
    ]
}
nft = api.mint_nft('0x...', metadata)
print(f"NFT Token ID: {nft['data']['token_id']}")
```

### JavaScript示例
```javascript
class Web3API {
    constructor(baseUrl, apiKey) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json'
        };
    }
    
    async createPayment(amount, currency, description) {
        const response = await fetch(`${this.baseUrl}/payment/create`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({
                amount,
                currency,
                description
            })
        });
        return response.json();
    }
    
    async getPaymentStatus(paymentId) {
        const response = await fetch(`${this.baseUrl}/payment/${paymentId}`, {
            headers: this.headers
        });
        return response.json();
    }
}

// 使用示例
const api = new Web3API('http://localhost:5002/api/v1', 'your-api-key');

// 创建支付
api.createPayment('100.00', 'USDC', 'Mining service')
    .then(result => {
        console.log('支付地址:', result.data.payment_address);
        console.log('二维码:', result.data.qr_code);
    });
```

## 最佳实践 Best Practices

### 1. 安全性
- 永远不要在客户端存储私钥
- 使用HTTPS进行所有API调用
- 实施适当的访问控制和API密钥管理
- 定期轮换API密钥

### 2. 性能优化
- 使用WebSocket接收实时事件
- 实施客户端缓存策略
- 批量处理多个操作
- 监控Gas价格，选择合适的时机发送交易

### 3. 错误处理
```python
import time
from functools import wraps

def retry_on_network_error(max_retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, TimeoutError) as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(delay * (2 ** attempt))
        return wrapper
    return decorator

@retry_on_network_error()
def call_api():
    # API调用代码
    pass
```

---

**技术支持**: web3-api-support@hashinsight.net  
**文档更新**: 2025-09-27  
**API版本**: v1.0