# HashInsight Enterprise - TypeScript Microservices Layer

## 概述

本TypeScript服务层为HashInsight Enterprise提供高性能的实时监控、矿机控制和限电策略功能。采用混合架构，与现有Flask核心系统协同工作。

## 核心功能

### 1. 统一数据中心 (DataHub)
智能数据聚合层，支持多源fallback机制：
- **价格数据**: CoinGecko → CoinDesk fallback
- **链上数据**: Blockchain.info → Mempool.space fallback
- **缓存策略**: LRU cache with TTL (价格30s, 链上数据5分钟)
- **超时处理**: 8秒超时 + 指数退避重试

API端点：
```
GET /api/datahub/price      # BTC价格
GET /api/datahub/chain      # 难度/算力/区块奖励
GET /api/datahub/all        # 所有数据
```

### 2. 矿机适配器层 (Miner Adapters)
标准化矿机控制接口：
- **Antminer适配器**: 通过CGMiner/BMminer API控制S19/S21系列
- **WhatsMiner模拟器**: 仿真M50/M53/M56系列（DEMO模式）
- **统一接口**: `getState()`, `setPowerLimit()`, `reboot()`
- **安全机制**: 双重确认 + 完整审计日志

API端点：
```
GET  /api/miners             # 获取所有矿机状态
GET  /api/miners/:id         # 获取单台矿机状态
POST /api/miners/:id/power-limit  # 设置功率限制 (需confirmed=true)
POST /api/miners/:id/reboot       # 重启矿机 (需confirmed=true)
```

### 3. 限电策略引擎 (Curtailment Strategy)
根据电价自动优化功率分配：
- **智能计算**: 按利润率排序，优先限制低效矿机
- **策略类型**: 停机(stop) 或 限功率(throttle)
- **收益分析**: 计算节电收益 vs 收入损失
- **执行流程**: Plan → Confirm → Execute → Rollback

API端点：
```
POST /api/curtailment/plan      # 计算限电方案
POST /api/curtailment/execute   # 执行方案 (需confirmed=true)
POST /api/curtailment/rollback  # 回滚方案
```

### 4. 事件日志系统 (Event Logging)
结构化JSONL事件追踪：
- **事件类型**: `datahub.fetch`, `monitor.alert`, `monitor.command`, `curtailment.plan/execute`
- **存储格式**: `events/YYYY-MM-DD/events.jsonl`
- **导出功能**: CSV格式事件导出

API端点：
```
GET /api/events/export?format=csv&since=24h
```

## 项目结构

```
api/
├── datahub/
│   ├── index.ts                    # DataHub主入口
│   └── providers/                   # 数据提供商
│       ├── price.coingecko.ts      # CoinGecko价格
│       ├── price.fallback.coindesk.ts
│       ├── chain.blockchaininfo.ts # 链上数据
│       └── chain.fallback.mempool.ts
└── server.ts                        # Express API服务器

common/
├── types.ts                         # 共享类型定义
├── eventLogger.ts                   # 事件日志核心
├── cache.ts                         # LRU缓存
└── retry.ts                         # 重试机制

modules/
├── miner_adapters/
│   ├── antminer.ts                 # Antminer适配器
│   ├── whatsminer.sim.ts           # WhatsMiner模拟器
│   └── registry.ts                  # 适配器注册表
└── curtailment_service/
    └── index.ts                     # 限电策略服务

config/
├── miners.json                      # 矿机配置
└── curtailment.json                 # 限电策略配置

test/
├── datahub.timeout.spec.ts         # 超时测试
├── datahub.fallback.spec.ts        # Fallback测试
└── datahub.exception.spec.ts       # 异常处理测试
```

## 环境变量配置

创建 `.env` 文件（参考 `.env.example`）：

```bash
# 基础配置
NODE_ENV=development
TS_API_PORT=3000
DEMO_MODE=1                          # 启用DEMO模式（使用模拟器）

# DataHub配置
DATAHUB_PRICE_TTL=30                 # 价格缓存TTL（秒）
DATAHUB_CHAIN_TTL=300                # 链上数据缓存TTL（秒）
DATAHUB_TIMEOUT_MS=8000              # API请求超时（毫秒）

# 外部API
COINGECKO_API_URL=https://api.coingecko.com/api/v3
BLOCKCHAIN_INFO_API_URL=https://blockchain.info
MEMPOOL_API_URL=https://mempool.space/api

# 矿机适配器
ANTMINER_DEFAULT_PORT=4028
ANTMINER_TIMEOUT_MS=5000

# 限电策略
CURTAILMENT_MAX_THROTTLE=0.5         # 最大限功率比例（50%）
CURTAILMENT_PRICE_THRESHOLD=0.10     # 触发限电的电价阈值（USD/kWh）
CURTAILMENT_REQUIRE_CONFIRM=true     # 执行前需要确认

# 数据库
DATABASE_URL=postgresql://...
WEB3_SQLITE_PATH=./database/web3.sqlite
```

## 安装与运行

### 安装依赖
```bash
npm install
```

### 运行测试
```bash
npm test                             # 运行所有测试
npm run test:watch                   # 监听模式
```

### 启动开发服务器
```bash
npm run dev                          # 端口3000
```

### 生产构建
```bash
npm run build                        # 编译TypeScript
npm start                            # 运行生产版本
```

## DEMO模式

设置 `DEMO_MODE=1` 启用演示功能：
- 使用5台模拟矿机（2台Antminer + 3台WhatsMiner）
- 所有控制操作为no-op，但完整记录日志
- 适合离线演示和功能展示

## 安全机制

### 双重确认
所有控制操作（限功率、重启、执行限电策略）必须：
1. 请求中包含 `confirmed: true`
2. 提供操作者信息 `actor: "user:email@example.com"`
3. 记录完整审计日志到events/

示例请求：
```json
POST /api/miners/demo-001/power-limit
{
  "percent": 0.8,
  "confirmed": true,
  "actor": "user:admin@hashinsight.com"
}
```

### 审计日志
所有操作记录到 `events/YYYY-MM-DD/events.jsonl`：
```jsonl
{"ts":"2025-11-01T12:00:00Z","type":"monitor.command","source":"ui","key":"demo-001:setPowerLimit","status":"ok","actor":"user:admin@hashinsight.com","details":{"percent":0.8}}
```

## 与Flask集成

TypeScript服务作为独立微服务运行在端口3000，Flask调用API进行集成：

### Flask调用示例
```python
import requests

# 获取实时数据
response = requests.get('http://localhost:3000/api/datahub/all')
data = response.json()
btc_price = data['price']['data']['btc_usd']
source = data['price']['source']  # 'coingecko' or 'coindesk'

# 获取矿机状态
response = requests.get('http://localhost:3000/api/miners')
miners = response.json()['miners']

# 执行限电策略
plan_response = requests.post('http://localhost:3000/api/curtailment/plan', json={
    'electricity_price': 0.12,
    'btc_price': 45000
})
plan = plan_response.json()

# 确认并执行
execute_response = requests.post('http://localhost:3000/api/curtailment/execute', json={
    'plan_id': plan['id'],
    'plan': plan,
    'confirmed': True,
    'actor': 'user:operations@hashinsight.com'
})
```

## 测试覆盖

### DataHub测试
- ✅ 超时场景：主源超时 → fallback成功
- ✅ Fallback场景：主源失败 → fallback成功
- ✅ 异常处理：所有源失败 → 抛出明确错误

运行测试：
```bash
npm test -- test/datahub
```

## 生产部署注意事项

1. **关闭DEMO模式**: 设置 `DEMO_MODE=0`
2. **配置真实矿机**: 编辑 `config/miners.json`
3. **设置安全确认**: 保持 `CURTAILMENT_REQUIRE_CONFIRM=true`
4. **配置HTTPS**: 使用反向代理（nginx/caddy）
5. **监控日志**: 定期归档 `events/` 目录
6. **备份配置**: `config/*.json` 文件

## 故障排查

### 端口冲突
```bash
# 查看端口占用
lsof -i :3000

# 修改端口
export TS_API_PORT=3001
```

### 数据源失败
检查事件日志：
```bash
cat events/$(date +%Y-%m-%d)/events.jsonl | grep "error"
```

### 矿机连接失败
1. 检查矿机IP/端口配置
2. 确认矿机API已启用（CGMiner API port 4028）
3. 网络防火墙规则

## 开发指南

### 添加新的数据提供商
1. 在 `api/datahub/providers/` 创建新文件
2. 实现 `fetchPrice()` 或 `fetchChainData()` 函数
3. 在 `api/datahub/index.ts` 中添加fallback逻辑

### 添加新的矿机适配器
1. 在 `modules/miner_adapters/` 创建新适配器
2. 实现 `MinerAdapter` 接口
3. 在 `registry.ts` 中注册

### 添加新的事件类型
1. 在 `common/types.ts` 扩展 `EventType`
2. 在 `eventLogger.ts` 添加helper方法

## 许可证
MIT License

## 支持
HashInsight Enterprise Team
