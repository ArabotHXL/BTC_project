# E2E Acceptance Tests

## Prerequisites

- `jq`: JSON processor (auto-installed if missing)
- `bc`: Basic calculator for performance calculations (auto-installed if missing)  
- `curl`: HTTP client (pre-installed in most systems)
- Valid API key in environment variable `API_KEY_1`

## Installation

```bash
# Install missing dependencies (Replit auto-handles this)
apt-get update && apt-get install -y jq bc
```

---

## 验收测试脚本

本目录包含BTC Mining Calculator的端到端验收测试脚本，用于验证事件驱动架构、RBAC权限控制和SWR缓存性能。

### 测试脚本列表

1. **e2e_acceptance.sh** - 端到端流程测试
2. **api_scope_test.sh** - API权限测试
3. **cache_swr_test.sh** - SWR缓存性能测试

---

## 1. 端到端流程测试

验证事件驱动架构：矿机添加 → 事件 → Worker → 重算 → 缓存

### 使用方法

```bash
chmod +x tests/e2e_acceptance.sh
API_KEY_1=your_api_key ./tests/e2e_acceptance.sh
```

### 测试步骤

1. **健康检查** - 验证Intelligence层服务状态
2. **新增矿机** - 触发miner.added事件
3. **等待处理** - 等待Worker消费outbox事件
4. **事件统计** - 检查事件处理状态
5. **验证缓存** - 确认portfolio缓存刷新
6. **Analytics** - 验证市场数据端点

### 预期结果

- 所有6步测试成功
- 事件正确处理
- 数据实时更新

---

## 2. API权限测试

验证RBAC细粒度权限控制

### 使用方法

```bash
chmod +x tests/api_scope_test.sh
API_KEY_1=your_api_key ./tests/api_scope_test.sh
```

### 测试步骤

1. **无Key访问** - 应返回401/403
2. **有效Key** - 成功访问
3. **CRM权限** - 测试CRM_SYNC权限
4. **Web3权限** - 测试WEB3_MINT权限
5. **Treasury权限** - 测试TREASURY_TRADE权限

### 预期结果

- 无Key返回401/403
- 有效Key成功访问
- 功能未启用返回503（预期行为）
- 权限不足返回403

---

## 3. SWR缓存性能测试

验证缓存命中率和响应时间

### 使用方法

```bash
chmod +x tests/cache_swr_test.sh
API_KEY_1=your_api_key ./tests/cache_swr_test.sh
```

### 测试步骤

1. **首次访问** - 缓存未命中，记录响应时间
2. **再次访问** - 缓存命中，应<50ms
3. **缓存统计** - 检查命中率和统计信息

### 预期结果

- 二次访问响应时间<50ms
- 缓存命中率>80%
- 性能提升明显

---

## 环境变量

所有测试脚本支持以下环境变量：

- `BASE_URL` - API基础URL（默认：http://localhost:5000）
- `API_KEY_1` - 测试用API Key（需要从环境变量读取）

### 设置环境变量

```bash
export BASE_URL="https://your-domain.com"
export API_KEY_1="your_api_key_here"
```

---

## 关键API端点

测试脚本验证以下端点：

### Intelligence Layer
- `GET /api/intelligence/health` - 系统健康检查
- `GET /api/intelligence/forecast/<user_id>` - 预测数据

### Analytics
- `GET /api/analytics/market-data` - 市场数据
- `GET /api/treasury/overview` - Treasury概览

### Batch Operations
- `POST /api/user-miners` - 添加矿机

### Permissions (需要特定权限)
- `POST /api/crm-integration/sync/customer` - CRM同步（需要CRM_SYNC）
- `POST /api/web3/sla/mint-request` - Web3 Mint（需要WEB3_MINT）
- `POST /api/treasury-exec/execute` - Treasury执行（需要TREASURY_TRADE）

---

## 故障排查

### 测试失败常见原因

1. **API Key未设置**
   ```bash
   export API_KEY_1="your_api_key"
   ```

2. **jq未安装**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install jq
   
   # macOS
   brew install jq
   ```

3. **服务未运行**
   ```bash
   # 检查服务状态
   curl http://localhost:5000/api/health
   ```

4. **权限不足**
   - 确保API Key具有所需权限
   - 检查用户角色配置

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log

# 查看Worker日志
tail -f logs/worker.log
```

---

## 性能基准

### 目标指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 健康检查响应 | <100ms | 系统状态查询 |
| 缓存命中响应 | <50ms | 二次访问时间 |
| 缓存命中率 | >80% | 缓存效率 |
| 事件处理延迟 | <3s | Worker处理时间 |
| P95响应时间 | <5s | 95%请求响应 |

### 运行所有测试

```bash
#!/bin/bash
export API_KEY_1="your_api_key"
export BASE_URL="http://localhost:5000"

echo "Running all E2E tests..."
./tests/e2e_acceptance.sh
./tests/api_scope_test.sh
./tests/cache_swr_test.sh
echo "All tests completed!"
```

---

## 持续集成

这些测试脚本可以集成到CI/CD流程中：

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install jq
        run: sudo apt-get install -y jq
      - name: Run E2E Tests
        env:
          API_KEY_1: ${{ secrets.API_KEY_1 }}
          BASE_URL: ${{ secrets.BASE_URL }}
        run: |
          chmod +x tests/*.sh
          ./tests/e2e_acceptance.sh
          ./tests/api_scope_test.sh
          ./tests/cache_swr_test.sh
```

---

## 贡献指南

添加新测试时，请遵循：

1. 使用bash脚本
2. 包含错误处理（`set -e`）
3. 使用颜色输出
4. 添加详细注释
5. 更新本README

---

## 许可证

与主项目保持一致
