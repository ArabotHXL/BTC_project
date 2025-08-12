# Market Analytics 数据管道状态报告

## 📊 当前配置总结

### 设计的数据收集频率
- **主要收集**: 每30分钟自动收集市场数据
- **检查频率**: 每15分钟检查一次调度任务
- **报告生成**: 每天8:00和20:00自动生成日报

### 实际运行状态
- **状态**: ❌ 后台服务已禁用
- **原因**: 环境变量 `ENABLE_BACKGROUND_SERVICES` 未设置
- **影响**: 数据只在用户访问页面时手动更新

## 🔧 启用自动数据收集

### 方法1: 设置环境变量
```bash
export ENABLE_BACKGROUND_SERVICES=1
```

### 方法2: 在 .replit 配置文件中添加
```
[env]
ENABLE_BACKGROUND_SERVICES = "1"
```

## 📈 数据收集详情

### 收集的数据类型
1. **BTC价格数据** (CoinGecko API)
2. **网络算力** (多源: Minerstat → Blockchain.info → 备用计算)
3. **挖矿难度** (Mempool.space → Blockchain.info)
4. **区块奖励** (当前固定 3.125 BTC)
5. **恐惧贪婪指数** (Alternative.me API)

### 数据源优先级
1. **Bitcoin RPC** (如果可用) - 最高精度
2. **Mempool.space** - 实时性好
3. **Blockchain.info** - 稳定备用
4. **Minerstat** - 算力专用数据

## ⚠️ 当前问题
- 后台自动收集被禁用
- 数据更新依赖用户手动访问
- 可能导致数据时效性问题