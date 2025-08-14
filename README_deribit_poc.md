# Deribit期权交易数据分析POC

这是一个使用Deribit Public API采集和分析期权交易数据的概念验证(POC)系统。

## 功能特性

- ✅ **实时数据采集**: 从Deribit Public API获取最新的期权交易数据
- ✅ **价格区间分析**: 将交易按价格区间分组，统计交易量分布
- ✅ **数据存储**: 使用SQLite数据库持久化存储交易数据
- ✅ **定时采集**: 支持定时自动采集数据
- ✅ **分析报告**: 生成详细的交易分析报告
- ✅ **多合约支持**: 支持分析不同的期权合约

## 安装依赖

```bash
pip install -r requirements_deribit_poc.txt
```

## 使用方法

### 1. 测试API连接

```bash
python test_deribit_poc.py
```

### 2. 列出活跃期权合约

```bash
python deribit_options_poc.py --list
```

### 3. 分析特定合约

```bash
python deribit_options_poc.py --instrument BTC-27DEC24-100000-C
```

### 4. 启动定时采集 (每15分钟)

```bash
python deribit_options_poc.py --schedule 15
```

## API端点说明

### 主要使用的Deribit API端点：

1. **`public/get_instruments`**: 获取可用的期权合约列表
2. **`public/get_last_trades_by_instrument`**: 获取指定合约的最新交易数据
3. **`public/ticker`**: 获取合约的实时行情数据
4. **`public/get_time`**: 获取服务器时间

### 数据结构

#### 交易数据 (TradeData)
```python
@dataclass
class TradeData:
    trade_id: str           # 交易ID
    timestamp: int          # 时间戳
    price: float           # 交易价格
    amount: float          # 交易数量
    direction: str         # 买卖方向 (buy/sell)
    instrument_name: str   # 合约名称
    index_price: float     # 指数价格
    mark_price: float      # 标记价格
```

#### 价格区间分析 (PriceRangeAnalysis)
```python
@dataclass
class PriceRangeAnalysis:
    price_range: str       # 价格区间范围
    trade_count: int       # 交易笔数
    total_volume: float    # 总交易量
    avg_price: float       # 平均价格
    percentage: float      # 占总量百分比
```

## 分析报告示例

```
============================================================
Deribit期权交易分析报告
============================================================
合约名称: BTC-27DEC24-100000-C
分析时间: 2025-08-14 23:54:12
总交易数: 156
总交易量: 12.5640
平均价格: $1,245.67

价格区间分析:
价格区间               交易数    交易量        占比     均价
------------------------------------------------------------
$1200.00-$1250.00     45       4.2150       33.55%   $1,225.34
$1250.00-$1300.00     38       3.1250       24.87%   $1,275.89
$1150.00-$1200.00     29       2.4560       19.55%   $1,178.45
...
============================================================
```

## 数据库结构

### trades表
存储原始交易数据：
- trade_id (主键)
- timestamp (时间戳)
- price (价格)
- amount (数量)
- direction (方向)
- instrument_name (合约名)
- index_price (指数价格)
- mark_price (标记价格)
- collected_at (采集时间)

### price_range_analysis表
存储价格区间分析结果：
- id (主键)
- instrument_name (合约名)
- analysis_time (分析时间)
- price_range (价格区间)
- trade_count (交易数)
- total_volume (总量)
- avg_price (均价)
- percentage (占比)

## 注意事项

1. **API限制**: Deribit Public API有频率限制，请合理设置采集间隔
2. **数据准确性**: 此POC仅用于演示，生产环境需要更多错误处理
3. **存储空间**: 长时间运行会积累大量数据，注意磁盘空间
4. **网络稳定性**: 确保网络连接稳定，API可能偶尔超时

## 扩展功能建议

- [ ] 添加WebSocket实时数据流
- [ ] 支持多币种期权分析
- [ ] 集成可视化图表
- [ ] 添加异常报警机制
- [ ] 支持CSV数据导出
- [ ] 增加更多统计指标

## 技术架构

```
DeribitAnalysisPOC
├── DeribitDataCollector    # API数据采集
├── DataStorage            # 数据存储管理
├── PriceRangeAnalyzer     # 价格区间分析
└── 定时任务调度           # Schedule管理
```

这个POC展示了如何使用Deribit Public API构建交易数据分析系统的基础框架。