# 比特币挖矿分析仪表盘 (Bitcoin Mining Analytics Dashboard)

## 项目概述

这是一个企业级的比特币挖矿分析平台，专为矿场运营商和投资者设计。系统提供实时数据收集、高级技术分析、智能交易策略和全面的风险管理功能。

### 核心功能
- **实时数据分析**: 比特币网络数据、价格、算力监控
- **高级技术指标**: RSI、MACD、布林带、移动平均线
- **智能交易算法**: 10模块Phase 3算法引擎 (A-J)
- **投资组合管理**: BTC库存、成本基础、现金覆盖跟踪
- **专业报告**: ARIMA预测、蒙特卡洛模拟
- **多语言支持**: 中文/英语动态切换

## 系统架构

### 后端技术栈
- **Flask**: Web应用框架
- **SQLAlchemy**: ORM数据库操作
- **PostgreSQL**: 生产数据库
- **NumPy/Pandas**: 数据分析和科学计算
- **Chart.js**: 前端图表可视化

### 前端架构
- **Bootstrap 5**: 响应式UI框架
- **Jinja2**: 模板引擎
- **原生JavaScript**: 客户端交互
- **移动优先设计**: 支持320px-1200px+屏幕

### 数据源
- **CoinGecko API**: 实时价格数据
- **Blockchain.info**: 比特币网络统计
- **CoinWarz API**: 挖矿难度和收益数据
- **Mempool.space**: 区块链技术数据

## 部署要求

### 环境变量
复制 `.env.example` 为 `.env` 并配置：
```bash
# 数据库 (生产环境用PostgreSQL，开发用SQLite)
DATABASE_URL=sqlite:///analytics_local.db
# 安全密钥
SESSION_SECRET=your-strong-secret-key
# API密钥
COINWARZ_API_KEY=your_api_key
```

### Python依赖
```bash
pip install -r requirements_fixed.txt
```

主要依赖包括：
- Flask 2.3+ (Web框架)
- SQLAlchemy 2.0+ (ORM)  
- NumPy 1.26+ (数值计算)
- Pandas 2.2+ (数据分析)
- Requests 2.31+ (HTTP客户端)
- psycopg2-binary (PostgreSQL驱动)

### 数据库设置
开发环境使用SQLite（自动创建）：
```bash
# 应用启动时自动创建表
python main.py
```

生产环境使用PostgreSQL：
```bash
# 设置DATABASE_URL为PostgreSQL连接字符串
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

### 快速启动
```bash
# 1. 安装依赖
pip install -r requirements_fixed.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件设置必要的配置

# 3. 启动应用
python main.py
# 或使用Gunicorn (生产环境)
gunicorn main:app --bind 0.0.0.0:5000

# 4. 访问应用
# 本地: http://localhost:5000
# 生产: https://your-domain.com
```

## 高级算法引擎 (Phase 3)

系统集成了10个专业交易模块：

### A. 趋势感知自适应 (Regime-Aware Adaptation)
- 动态识别市场状态（牛市/熊市/震荡）
- 自适应调整交易参数
- 机器学习模型预测趋势转换

### B. 突破衰竭检测 (Breakout Exhaustion Detection)
- 识别虚假突破和真实突破
- 量能分析确认突破有效性
- 动态止损和止盈设置

### C. 支撑阻力共振 (Support/Resistance Confluence)
- 多时间框架支撑阻力分析
- 斐波那契回调整合
- 关键价位强度评分

### D. ATR动态分层 (Adaptive ATR Layering)
- 基于波动性的仓位管理
- 动态调整风险敞口
- 智能分批建仓/平仓

### E. 挖矿周期分析 (Miner Cycle Analysis)
- 矿工行为模式分析
- 挖矿成本与价格关系
- 链上数据指标集成

### F. 形态目标识别 (Pattern Target Recognition)
- 经典技术形态识别
- 自动测算价格目标
- 概率分析和成功率统计

### G. 衍生品压力监测 (Derivatives Pressure Monitoring)
- 期货持仓分析
- 期权gamma压力监测
- 大户持仓变化跟踪

### H. 微观结构优化 (Microstructure Execution Optimization)
- 实时滑点预测
- TWAP执行窗口计算
- 流动性深度评估
- 市场冲击最小化

### I. 智能仓位配置 (Bandit-Sizing Allocation)
- 多臂老虎机算法
- 动态仓位优化
- 风险调整收益最大化

### J. 集成聚合决策 (Ensemble Aggregation Scoring)
- 多模型信号融合
- 权重动态调整
- 置信度评分系统

## 数据管理

### 实时数据收集
- 每15分钟收集市场数据
- 智能缓存和错误恢复
- 多数据源冗余备份

### 历史数据存储
- 优化存储：每日最多10个数据点
- 自动清理过期数据
- 支持数据导出和备份

### 数据质量保证
- 实时数据验证
- 异常值检测和处理
- 数据完整性监控

## 安全特性

### 身份验证
- 邮箱验证系统
- 角色权限管理
- 会话安全保护

### 数据安全
- API密钥加密存储
- 用户输入验证
- SQL注入防护

### 系统安全
- HTTPS强制加密
- CSRF保护
- 安全头部配置

## 监控和日志

### 性能监控
- 系统资源使用率
- API响应时间
- 数据库查询性能

### 错误追踪
- 详细错误日志
- 异常报告系统
- 自动恢复机制

### 业务指标
- 用户活跃度
- 交易信号准确率
- 系统稳定性指标

## 扩展功能

### CRM系统
- 客户管理
- 销售跟踪
- 佣金计算

### 报告生成
- 专业PDF报告
- Excel数据导出
- 自定义仪表板

### 集成接口
- RESTful API
- Webhook通知
- 第三方集成

## 技术支持

### 文档资源
- API文档
- 用户手册
- 开发指南

### 故障排除
- 常见问题解答
- 错误代码参考
- 联系支持团队

---

**版本**: Phase 3 (Complete)
**更新日期**: 2025年8月22日
**开发状态**: 生产就绪

此系统经过完整测试，包含所有必需的模块和配置文件，可直接部署到生产环境。