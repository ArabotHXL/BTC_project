# Bitcoin Mining Calculator - 分离包下载

## 包信息

1. **核心挖矿计算器** - `btc_mining_calculator_core.tar.gz` (0.2 MB)
   - 基础挖矿收益计算功能
   - 用户认证系统
   - 订阅管理
   - 多语言支持

2. **高级分析平台** - `btc_mining_analytics_advanced.tar.gz` (0.6 MB) 
   - HashInsight Treasury Management
   - CRM系统
   - 高级算法引擎
   - Deribit期权分析
   - 托管业务管理

## 使用说明

### 方案1：独立部署核心包
```bash
tar -xzf btc_mining_calculator_core.tar.gz
cd btc_mining_calculator_core
pip install -r requirements.txt
python main.py
```

### 方案2：完整功能部署
```bash
# 解压两个包到同一目录
tar -xzf btc_mining_calculator_core.tar.gz
tar -xzf btc_mining_analytics_advanced.tar.gz

# 合并功能（可选）
cp -r btc_mining_analytics_advanced/* btc_mining_calculator_core/
cd btc_mining_calculator_core
pip install -r requirements.txt
python main.py
```

生成时间: 2025-09-09 03:15:22
