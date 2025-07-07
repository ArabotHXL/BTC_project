# Bitcoin挖矿计算器系统架构文档
# Bitcoin Mining Calculator System Architecture Documentation

## 系统概览 (System Overview)

Bitcoin挖矿计算器是一个基于Flask的企业级Web应用系统，为矿场运营商和投资者提供精确的挖矿收益分析、客户关系管理和数据分析服务。系统采用多层架构设计，支持实时数据集成、角色权限管理和多语言界面。

## 架构层次 (Architecture Layers)

### 1. 用户层 (User Layer)
**角色权限体系 (Role-based Access Control)**

- **Owner (所有者)** - 最高权限
  - 完全访问所有系统功能
  - 用户访问管理
  - 系统调试和监控
  - 矿场中介业务管理
  - 数据分析仪表盘

- **Admin (管理员)** - 高级管理权限
  - CRM系统完全权限
  - 网络分析访问
  - 用户管理(除Owner权限外)
  - 客户数据管理

- **Mining_site (矿场主)** - 业务操作权限
  - 客户管理(自己创建的)
  - 网络分析访问
  - 挖矿计算器完整功能
  - CRM系统受限访问

- **Manager (经理)** - CRM专用权限
  - CRM系统访问
  - 客户关系管理
  - 商机和交易跟踪

- **Guest (访客)** - 基础权限
  - 基本挖矿计算功能
  - 算法测试工具
  - 电力削减计算器

### 2. 前端界面层 (Frontend Layer)
**技术栈**: Jinja2模板引擎 + Bootstrap 5 + Chart.js + 原生JavaScript

**核心模块**:
- **挖矿计算器** (`templates/index.html`)
  - 10种ASIC矿机型号支持
  - 实时收益计算
  - ROI分析和盈亏平衡点
  - 电力削减场景分析

- **CRM系统** (`templates/crm/`)
  - 客户生命周期管理
  - 商机跟踪和转化
  - 交易记录和佣金计算
  - 活动日志和沟通历史

- **数据分析仪表盘** (`templates/analytics_dashboard.html`)
  - 市场趋势可视化
  - 技术指标分析
  - 投资决策支持
  - 风险评估报告

- **网络分析工具** (`templates/network_history.html`)
  - 历史数据趋势
  - 算力难度分析
  - 收益预测模型

- **多语言支持**
  - 中英文动态切换
  - 业务术语本地化
  - 用户偏好记忆

### 3. Flask应用层 (Application Layer)
**主控制器**: `app.py` - 1900+行代码，统一路由管理

**核心模块**:

#### 认证系统 (`auth.py`)
- 邮箱验证登录
- 会话管理和安全
- 角色权限控制
- 用户访问追踪

#### 挖矿计算引擎 (`mining_calculator.py`)
- 双算法验证机制
- 10种矿机型号数据库
- 电力成本优化分析
- ROI计算和现金流预测

#### CRM业务逻辑 (`crm_routes.py`)
- 客户数据管理
- 销售漏斗追踪
- 业绩报告生成
- 权限隔离控制

#### 数据分析引擎 (`analytics_engine.py`)
- 实时市场数据收集
- 技术指标计算
- 自动化报告生成
- 15分钟数据更新频率

#### 网络数据服务 (`services/network_data_service.py`)
- 自动化数据采集
- 历史快照记录
- 数据质量验证
- API健康监控

#### 翻译系统 (`translations.py`)
- 动态语言切换
- 业务术语管理
- 用户偏好存储

### 4. 数据库层 (Database Layer)
**数据库**: PostgreSQL + SQLAlchemy ORM

**核心表结构**:

#### 用户权限表 (UserAccess)
```sql
- id: 主键
- name: 用户姓名
- email: 邮箱地址
- role: 用户角色
- access_days: 访问天数
- created_at: 创建时间
- last_login: 最后登录
- has_access: 访问状态
```

#### 客户管理表 (Customer)
```sql
- id: 主键
- company_name: 公司名称
- contact_person: 联系人
- email: 邮箱
- phone: 电话
- created_by_id: 创建人ID
- industry: 行业
- tags: 标签
- notes: 备注
```

#### 市场分析表 (MarketAnalytics)
```sql
- id: 主键
- timestamp: 时间戳
- btc_price: BTC价格
- network_hashrate: 网络算力
- network_difficulty: 网络难度
- fear_greed_index: 恐惧贪婪指数
- price_change_24h: 24小时涨跌
```

#### 网络快照表 (NetworkSnapshot)
```sql
- id: 主键
- timestamp: 记录时间
- btc_price: BTC价格
- network_hashrate: 网络算力
- difficulty: 难度
- block_reward: 区块奖励
- calculation_context: 计算上下文
```

### 5. 外部API层 (External APIs)
**智能多源数据策略**

#### 主要数据源 - CoinWarz API
- **功能**: 专业挖矿数据服务
- **数据**: SHA-256算法收益对比
- **限制**: 1000次/月调用
- **状态**: 732次剩余

#### 备用数据源 - CoinGecko API
- **功能**: 加密货币价格数据
- **数据**: 实时BTC价格、市场数据
- **特点**: 高可用性、快速响应

#### 网络数据源 - Blockchain.info API
- **功能**: Bitcoin网络统计
- **数据**: 网络难度、区块信息
- **用途**: 算力计算验证

#### 算力数据源 - Minerstat API
- **功能**: 挖矿网络数据
- **数据**: 实时网络算力
- **当前**: 947.69 EH/s

### 6. 基础设施层 (Infrastructure Layer)

#### Web服务器
- **Gunicorn WSGI**: 生产环境应用服务器
- **端口配置**: 0.0.0.0:5000 (公网访问)
- **进程管理**: 自动重启和负载均衡

#### 数据库连接
- **SQLAlchemy ORM**: 对象关系映射
- **连接池**: 300秒回收周期
- **健康检查**: pre_ping=True

#### 定时任务系统
- **统一数据管道**: 30分钟采集频率
- **分析引擎**: 15分钟数据更新
- **报告生成**: 每日00:00自动生成

#### 数据流管理
- **实时更新**: WebSocket连接
- **缓存策略**: 价格数据5分钟缓存
- **容错机制**: 多源API智能切换

## 数据流架构 (Data Flow Architecture)

### 1. 用户请求流程
```
用户输入 → 权限验证 → 路由分发 → 业务逻辑 → 数据处理 → 结果返回
```

### 2. 数据采集流程
```
定时触发 → 多API调用 → 数据验证 → 数据库存储 → 实时推送
```

### 3. 计算引擎流程
```
参数输入 → 实时数据获取 → 双算法计算 → 结果验证 → 快照记录 → 可视化展示
```

## 系统特性 (System Features)

### 高可用性设计
- **多源API冗余**: 99.9%数据可用性
- **自动故障转移**: 智能数据源切换
- **连接池管理**: 数据库连接优化

### 安全性保障
- **角色权限控制**: 五级权限体系
- **会话安全**: 加密cookie管理
- **数据隔离**: 用户数据权限分离

### 性能优化
- **数据缓存**: 减少API调用频率
- **分页查询**: 大数据集处理优化
- **异步任务**: 后台数据采集

### 扩展性架构
- **模块化设计**: 独立业务模块
- **API标准化**: RESTful接口设计
- **数据库分表**: 支持大规模数据

## 监控和维护 (Monitoring & Maintenance)

### 系统监控
- **API健康检查**: 实时状态监控
- **数据库性能**: 查询优化分析
- **用户活动**: 登录行为追踪

### 错误处理
- **日志记录**: 详细错误日志
- **异常恢复**: 自动重试机制
- **用户反馈**: 友好错误提示

### 备份策略
- **数据备份**: 定期数据库备份
- **代码版本**: Git版本控制
- **配置管理**: 环境变量管理

---

## 部署说明 (Deployment Notes)

### 环境要求
- Python 3.9+
- PostgreSQL 12+
- 2GB+ RAM
- 网络连接 (API访问)

### 关键配置
- `DATABASE_URL`: PostgreSQL连接字符串
- `SESSION_SECRET`: 会话加密密钥
- API密钥: CoinWarz, CoinGecko等

### 生产优化
- 启用Gunicorn多进程
- 配置反向代理 (Nginx)
- 设置SSL证书
- 监控系统资源使用

此系统架构确保了Bitcoin挖矿计算器的高性能、高可用性和可扩展性，为用户提供企业级的挖矿分析服务。