# TypeScript微服务层 - 快速开始指南

## ✅ 已实现功能（全部通过Architect审查）

1. **统一数据中心 (DataHub)** - 价格/链上数据聚合，智能fallback
2. **矿机适配器层** - Antminer控制 + WhatsMiner模拟器
3. **限电策略引擎** - 根据电价优化功率分配
4. **事件日志系统** - JSONL格式结构化追踪
5. **API认证机制** - Bearer token + 双重确认
6. **完整测试覆盖** - Jest单元测试

## 🚀 快速启动

### 1. 安装依赖
```bash
# 依赖已安装完成
npm install  # 如需重新安装
```

### 2. 配置环境变量
```bash
# 创建.env文件
cp .env.example .env

# 编辑关键配置
TS_API_PORT=3000
TS_API_KEY=hashinsight_dev_key_2025  # 生产环境请更换！
DEMO_MODE=1  # 启用演示模式（5台模拟矿机）
```

### 3. 运行测试
```bash
# 运行所有测试（包括DataHub timeout/fallback/exception + Curtailment聚合测试）
npm test

# 预期结果：所有测试通过 ✅
```

### 4. 启动TypeScript API服务
```bash
# 开发模式（端口3000）
npm run dev

# 或者构建后运行
npm run build
npm start
```

### 5. 测试API端点

#### 健康检查（无需认证）
```bash
curl http://localhost:3000/health
```

#### 获取DataHub数据（无需认证）
```bash
# BTC价格（CoinGecko → CoinDesk fallback）
curl http://localhost:3000/api/datahub/price

# 链上数据（Blockchain.info → Mempool fallback）
curl http://localhost:3000/api/datahub/chain

# 所有数据
curl http://localhost:3000/api/datahub/all
```

#### 矿机控制（需要认证）
```bash
# 设置环境变量
export API_KEY="hashinsight_dev_key_2025"

# 获取所有矿机状态
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/miners

# 获取单台矿机状态
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/miners/demo-antminer-s19-001

# 设置功率限制（需confirmed: true）
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"percent": 0.8, "confirmed": true, "actor": "user:admin@example.com"}' \
  http://localhost:3000/api/miners/demo-antminer-s19-001/power-limit

# 重启矿机（需confirmed: true）
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"confirmed": true, "actor": "user:admin@example.com"}' \
  http://localhost:3000/api/miners/demo-antminer-s19-001/reboot
```

#### 限电策略（需要认证）
```bash
# 计算限电方案
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"electricity_price": 0.12, "btc_price": 45000}' \
  http://localhost:3000/api/curtailment/plan

# 执行方案（需confirmed: true）
curl -X POST -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "xxx-xxx-xxx",
    "plan": {...},
    "confirmed": true,
    "actor": "user:operations@example.com"
  }' \
  http://localhost:3000/api/curtailment/execute
```

#### 事件导出（需要认证）
```bash
# 导出今日事件（JSON格式）
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:3000/api/events/export

# 导出CSV格式
curl -H "Authorization: Bearer $API_KEY" \
  "http://localhost:3000/api/events/export?format=csv" \
  > events_today.csv
```

## 📊 DEMO模式说明

`DEMO_MODE=1` 时系统提供：
- **5台模拟矿机**：
  - demo-antminer-s19-001 (Antminer S19 Pro)
  - demo-antminer-s19-002 (Antminer S19j Pro)
  - demo-whatsminer-m50s-001 (WhatsMiner M50S)
  - demo-whatsminer-m53s-001 (WhatsMiner M53S+)
  - demo-whatsminer-m56s-001 (WhatsMiner M56S++)
- **仿真数据**：算力/温度/风扇转速带随机波动
- **无实际执行**：所有控制操作no-op，但完整记录审计日志

## 🔒 安全机制

### API认证
所有敏感端点需要Bearer token：
```
Authorization: Bearer hashinsight_dev_key_2025
```

### 双重确认
控制操作（限功率/重启/执行限电）需要：
1. **confirmed: true** - 明确确认
2. **actor: "user:email"** - 操作者身份
3. 完整审计日志记录到 `events/YYYY-MM-DD/events.jsonl`

### 审计日志示例
```jsonl
{"ts":"2025-11-01T12:00:00Z","type":"monitor.command","source":"ui","key":"demo-001:setPowerLimit","status":"ok","actor":"user:admin@example.com","details":{"percent":0.8}}
{"ts":"2025-11-01T12:05:00Z","type":"curtailment.execute","source":"ui","key":"plan-uuid","status":"ok","actor":"user:ops@example.com","details":{"actions_count":3}}
```

## 🧪 运行测试

### DataHub测试
```bash
# 超时fallback测试
npm test -- test/datahub.timeout.spec.ts

# Fallback机制测试
npm test -- test/datahub.fallback.spec.ts

# 异常处理测试
npm test -- test/datahub.exception.spec.ts
```

### Curtailment测试
```bash
npm test -- test/curtailment.spec.ts
```

预期结果：
- ✅ Revenue impact为负值
- ✅ Impact percentage基于总收入计算
- ✅ 优先限制低效矿机
- ✅ 聚合计算正确

## 🔗 与Flask集成

Flask应用通过HTTP调用TypeScript API：

```python
# Python示例
import requests

# 设置API密钥
headers = {"Authorization": "Bearer hashinsight_dev_key_2025"}

# 获取实时数据
response = requests.get(
    "http://localhost:3000/api/datahub/all",
    headers=headers  # DataHub不需要认证，但为了一致性可加上
)
data = response.json()
print(f"BTC价格: ${data['price']['data']['btc_usd']}")
print(f"数据源: {data['price']['source']}")

# 获取矿机状态
response = requests.get(
    "http://localhost:3000/api/miners",
    headers=headers
)
miners = response.json()['miners']

# 计算限电策略
response = requests.post(
    "http://localhost:3000/api/curtailment/plan",
    headers=headers,
    json={
        "electricity_price": 0.12,
        "btc_price": 45000
    }
)
plan = response.json()
print(f"节电：${plan['expected_savings_usd']:.2f}/小时")
print(f"收入影响：${plan['expected_revenue_impact_usd']:.2f}/小时")
```

## ⚠️ 当前状态

### ✅ TypeScript服务层 - 完全就绪
- 所有功能实现完成
- Architect审查通过
- 测试覆盖完整
- 可独立运行（端口3000）

### ⚠️ Flask应用 - 数据库连接问题
```
ERROR: The endpoint has been disabled. Enable it using Neon API and retry.
```

**解决方案**：
1. 登录Neon控制台
2. 启用数据库endpoint
3. 或者更新 `DATABASE_URL` 到可用的数据库

## 📁 关键文件

```
api/
├── server.ts           # Express API服务器（✅已认证保护）
├── auth.ts             # 认证中间件
└── datahub/            # 数据聚合层

modules/
├── miner_adapters/     # 矿机控制
└── curtailment_service/ # 限电策略（✅计算修复）

common/
├── types.ts            # 类型定义
├── eventLogger.ts      # JSONL事件日志
├── cache.ts            # LRU缓存
└── retry.ts            # 重试机制

test/                   # Jest测试
config/                 # 配置文件
events/                 # JSONL事件日志目录
```

## 🎯 下一步

1. **修复Flask数据库连接**
2. **集成TypeScript服务到Flask UI**
3. **配置生产环境API密钥**
4. **部署到Replit**
5. **配置真实矿机（config/miners.json）**

## 📞 技术支持

所有代码已通过Architect审查：
- ✅ Curtailment聚合计算正确
- ✅ API认证机制完整
- ✅ 测试覆盖充分
- ✅ 事件日志系统完善

生产部署前请：
1. 更换 `TS_API_KEY` 为强密钥
2. 设置 `DEMO_MODE=0`
3. 配置真实矿机IP
4. 设置 `CURTAILMENT_REQUIRE_CONFIRM=true`
