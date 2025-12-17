# 🏗️ BTC Mining Calculator - 完整系统架构文档
# Complete System Architecture Documentation

> **企业级比特币挖矿分析平台 - 完整技术架构映射**  
> **Enterprise-grade Bitcoin Mining Analytics Platform - Complete Technical Architecture**

> **📋 文档验证状态**: ✅ 已通过完整代码验证（2025-10-09）  
> **🔍 验证方法**: 基于app.py实际代码、blueprint定义文件、路由文件的逐一核对

## ⚠️ 重要说明：Blueprint架构验证结果

**验证完成日期**: 2025-10-09  
**验证范围**: 所有Flask Blueprint注册、URL前缀、路由定义

### 关键发现

1. **✅ Analytics Blueprint验证结果**:
   - **实际URL前缀**: `/api/analytics` (routes/analytics_routes.py:15)
   - **文档状态**: 正确
   - **注意**: 之前的修订任务描述声称应为 `/analytics`，但这是错误的

2. **✅ Blueprint总数**: 20个活跃blueprints
   - 基础blueprints: 18个
   - 条件性blueprints: 2个 (billing_bp, deribit_advanced_bp)
   - **已禁用**: broker blueprint (DISABLED: Gold flow module)

3. **✅ 特殊URL前缀情况**:
   - `batch_calculator_bp`: 无url_prefix，路由为 `/batch-calculator`
   - `deribit_bp`: 无url_prefix，路由为 `/deribit`
   - `sla_nft_bp`: 无url_prefix，路由为 `/api/sla/*`

---

## 📋 目录 | Table of Contents

1. [系统概览 | System Overview](#系统概览)
2. [核心架构 | Core Architecture](#核心架构)
3. [业务模块映射 | Business Modules](#业务模块映射)
4. [数据库架构 | Database Architecture](#数据库架构)
5. [API端点映射 | API Endpoints](#api端点映射)
6. [外部集成 | External Integrations](#外部集成)
7. [缓存策略 | Caching Strategy](#缓存策略)
8. [CDC事件平台 | CDC Event Platform](#cdc事件平台)
9. [数据流向 | Data Flow](#数据流向)
10. [技术栈 | Technology Stack](#技术栈)

---

## 🎯 系统概览 | System Overview

### 平台定位
BTC Mining Calculator是一个企业级Web应用，专注于比特币挖矿盈利分析，服务矿场业主及其客户。提供实时数据集成、双算法验证、多语言支持（中英文）和强大的基于角色的访问控制。

### 核心目标
- ✅ **实时数据集成** - 多源API聚合，智能降级
- ✅ **双算法验证** - 挖矿盈利性分析的双重计算引擎
- ✅ **多语言支持** - 中文/英文动态切换
- ✅ **企业级安全** - RBAC权限控制，会话管理
- ✅ **高性能缓存** - Redis + SWR策略，P95 < 3s
- ✅ **事件驱动** - CDC架构，实时数据同步

### 关键指标

> **免责声明**: 以下指标来自设计目标和CDC平台README的参考值，实际性能需根据部署环境、负载和硬件配置进行实际测量。

| 指标 | 设计目标 |
|------|---------|
| P95 Write-to-Visible延迟 | <3s |
| Outbox-to-Kafka延迟 (P50) | <500ms |
| Consumer处理延迟 (P95) | <1s |
| 吞吐量 (峰值) | >1000 events/s |
| DLQ错误率 | <0.1% |

---

## 🏗️ 核心架构 | Core Architecture

### 前端架构
- **模板引擎**: Jinja2 + Bootstrap 5 (暗色主题，金色点缀)
- **UI框架**: Bootstrap CSS, Bootstrap Icons, Chart.js
- **响应式设计**: Mobile-first
- **多语言**: 动态中英文切换

### 后端架构
- **Web框架**: Flask (Blueprint模块化路由)
- **模块化架构**: 10个独立模块，通过数据库通信
- **认证系统**: 自定义邮箱认证 + 角色管理
- **API集成**: 多源数据聚合，智能fallback
- **后台服务**: 调度器自动数据收集
- **计算引擎**: 双算法系统，支持42+矿机型号
- **技术分析**: 服务端计算RSI, MACD, SMA, EMA, Bollinger Bands
- **权限控制**: 高级装饰器 + RBAC权限矩阵
- **报告生成**: ARIMA预测 + Monte Carlo模拟
- **缓存系统**: Redis + SWR策略
- **部署优化**: 快速启动，轻量健康检查

### 数据库架构
- **主数据库**: PostgreSQL (Neon托管)
- **ORM**: SQLAlchemy with DeclarativeBase
- **连接管理**: 连接池 + 自动重连 + 健康监控
- **数据模型**: 50+ 表，包括用户、客户、挖矿数据、网络快照
- **优化**: 每日最多10个数据点，自动清理策略

---

## 📦 业务模块映射 | Business Modules

### 核心业务模块（实际注册的Blueprints）

> **说明**: 以下为app.py中实际注册的Flask Blueprints及其URL前缀。总计**20个活跃blueprints**（含条件性注册）

| 模块名 | URL前缀 | 实际路由示例 | 主要功能 | Blueprint名称 | 注册位置 |
|--------|---------|-------------|----------|--------------|---------|
| **CRM** | `/crm` | `/crm/`, `/crm/customers` | 客户管理、线索跟踪、交易管理 | `crm_bp` | app.py:3713 (via init_crm_routes) |
| **Hosting** | `/hosting` | `/hosting/`, `/hosting/sites` | 托管服务、站点管理、矿机监控 | `hosting_bp` | app.py:3721 |
| **Client** | `/client` | `/client/`, `/client/dashboard` | 客户端视图、资产概览、账单 | `client_bp` | app.py:3729 |
| **Batch Calculator** | *(无前缀)* | `/batch-calculator`, `/api/batch-calculate` | 批量计算、数据导入、Excel导出 | `batch_calculator_bp` | app.py:5922 |
| **Batch Import** | `/batch` | `/batch/upload`, `/batch/template` | CSV批量数据导入 | `batch_import_bp` | app.py:5963 |
| **Analytics** | `/api/analytics` | `/api/analytics/roi-heatmap` | 技术分析、ROI热力图、市场数据 | `analytics_bp` | app.py:5979 |
| **Trust** | `/trust` | `/trust/`, `/trust/verify` | 信任中心、透明度验证 | `trust_bp` | app.py:5987 |
| **Miner Management** | `/admin/miners` | `/admin/miners/`, `/admin/miners/add` | 矿机管理、型号维护 | `miner_bp` | app.py:5930 |
| **Miner Import** | `/api/miners` | `/api/miners/import` | 矿机数据导入API | `miner_import_bp` | app.py:5971 |
| **Billing** | `/billing` | `/billing/subscribe`, `/billing/payment` | 加密货币支付、订阅管理 | `billing_bp` | app.py:5913 (条件性) |
| **Deribit** | *(无前缀)* | `/deribit`, `/api/deribit/options-data` | Deribit衍生品数据分析 | `deribit_bp` | app.py:5938 |
| **Deribit Advanced** | *(无前缀)* | (高级分析路由) | Deribit高级分析包 | `deribit_advanced_bp` | app.py:5943 (条件性) |
| **SLA NFT** | *(无前缀)* | `/api/sla/certificates` | SLA证书NFT管理 | `sla_nft_bp` | app.py:5955 |

#### Intelligence Layer (智能层子模块)

| 模块名 | URL前缀 | 实际路由示例 | 主要功能 | Blueprint名称 | 注册位置 |
|--------|---------|-------------|----------|--------------|---------|
| **Forecast** | `/api/intelligence/forecast` | `/api/intelligence/forecast/btc-price` | BTC价格预测、难度预测 | `forecast_bp` | app.py:6001 |
| **Optimize** | `/api/intelligence/optimize` | `/api/intelligence/optimize/power` | 停电优化、线性规划 | `optimize_bp` | app.py:6002 |
| **Explain** | `/api/intelligence/explain` | `/api/intelligence/explain/roi` | ROI解释器、推荐系统 | `explain_bp` | app.py:6003 |
| **Health** | `/api/intelligence` | `/api/intelligence/health` | 智能层健康检查、SLO监控 | `health_bp` | app.py:6004 |

#### API层集成模块

| 模块名 | URL前缀 | 实际路由示例 | 主要功能 | Blueprint名称 | 注册位置 |
|--------|---------|-------------|----------|--------------|---------|
| **Web3 SLA** | `/api/web3/sla` | `/api/web3/sla/mint` | SLA NFT铸造、区块链验证 | `web3_sla_bp` | app.py:6018 |
| **Treasury Execute** | `/api/treasury-exec` | `/api/treasury-exec/sell` | 财资交易执行 | `treasury_execute_bp` | app.py:6019 |
| **CRM Integration** | `/api/crm-integration` | `/api/crm-integration/sync` | CRM外部集成API | `crm_integration_bp` | app.py:6020 |

#### 🔍 Blueprint注册验证说明

**总计**: 20个活跃blueprints（基础18个 + 2个条件性：billing_bp, deribit_advanced_bp）

**关键发现**:
- ✅ **analytics_bp**: 实际使用 `/api/analytics` 前缀（routes/analytics_routes.py:15）
- ✅ **crm_bp**: 通过 `init_crm_routes(app)` 函数注册，前缀 `/crm`（crm_routes.py:748）
- ✅ **batch_calculator_bp**: 无url_prefix，路由直接定义为 `/batch-calculator`
- ✅ **deribit_bp**: 无url_prefix，路由直接定义为 `/deribit`
- ✅ **sla_nft_bp**: 无url_prefix，路由直接定义为 `/api/sla/*`
- ❌ **broker blueprint**: 已禁用（DISABLED: Gold flow module），未实际注册

**注册方式**:
1. 直接注册: `app.register_blueprint(bp, url_prefix='...')` - 大多数blueprint
2. 函数注册: `init_crm_routes(app)` - crm_bp
3. 条件注册: 通过 `SUBSCRIPTION_ENABLED` 等配置控制 - billing_bp, deribit_advanced_bp
4. 模块化注册: `register_modules(app)` - 仅calculator_bp当前启用

### 模块详细功能

#### 1️⃣ Calculator Module (挖矿计算器)
- **核心功能**:
  - 双算法挖矿盈利计算
  - 支持42+ ASIC矿机型号
  - 实时BTC价格、难度、算力
  - ROI分析、停电影响计算
  - 算力衰减模拟
- **关键端点**:
  - `POST /api/calculate` - 主计算API
  - `GET /api/user-miners` - 获取用户矿机配置
  - `POST /api/user-miners` - 保存矿机配置

#### 2️⃣ Analytics Module (技术分析)
- **核心功能**:
  - 技术指标计算 (RSI, MACD, SMA, EMA, Bollinger Bands)
  - 历史数据回放
  - ROI热力图
  - 停电模拟
- **关键端点**:
  - `POST /api/analytics/roi-heatmap`
  - `POST /api/analytics/historical-replay`
  - `GET /api/technical-indicators`
  - `GET /api/market-data`

#### 3️⃣ CRM Module (客户关系管理)
- **核心功能**:
  - 客户生命周期管理
  - 线索/交易跟踪
  - 佣金管理
  - 发票系统
  - 资产设备跟踪
  - 活动日志
- **数据模型**:
  - `Customer` - 公司信息、联系人、挖矿容量
  - `Lead` - 潜在机会 (NEW → CONTACTED → QUALIFIED → WON/LOST)
  - `Deal` - 交易项目、价值跟踪
  - `Invoice` - 账单 (draft → sent → paid/overdue)
  - `Asset` - 设备跟踪
  - `Activity` - 交互历史

#### 4️⃣ Hosting Module (托管服务)
- **核心功能**:
  - 托管站点管理
  - 矿机部署监控
  - 遥测数据收集
  - SLA模板管理
  - 事故工单系统
- **数据模型**:
  - `HostingSite` - 托管站点 (容量、电价、状态)
  - `HostingMiner` - 托管矿机
  - `MinerTelemetry` - 矿机遥测数据
  - `HostingIncident` - 事故记录
  - `HostingTicket` - 工单系统

#### 5️⃣ Intelligence Layer (智能层)
- **核心功能**:
  - BTC价格预测 (ARIMA)
  - 网络难度预测
  - 停电优化 (线性规划)
  - ROI解释器
  - 异常检测
- **模块**:
  - `Forecast` - 时间序列预测
  - `Anomaly Detection` - 异常检测
  - `Power Optimizer` - 停电优化
  - `ROI Explainer` - ROI解释

#### 6️⃣ Treasury Module (财资管理)
- **核心功能**:
  - BTC持仓管理
  - 卖币策略模板
  - 10个信号聚合模块
  - 回测引擎
  - 订单执行优化
- **信号模块**:
  - 技术指标信号
  - 情绪分析
  - 链上数据
  - 衍生品数据

#### 7️⃣ Web3 Module (区块链集成)
- **核心功能**:
  - SLA NFT铸造
  - IPFS数据存储
  - 区块链数据验证
  - Base L2集成
- **智能合约**:
  - `SLANFTCertificate.sol` - SLA证书NFT

#### 8️⃣ Batch Module (批量处理)
- **核心功能**:
  - CSV批量导入
  - Excel数据导出
  - 批量计算优化
  - 错误报告下载

#### 9️⃣ Client Module (客户端)
- **核心功能**:
  - 客户仪表盘
  - 资产概览
  - 账单查看
  - 工单提交

---

## 🗄️ 数据库架构 | Database Architecture

### 数据库表映射 (50+ 表)

#### 核心业务表

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `user_access` | 用户账户 | email, password_hash, role, has_access |
| `miner_models` | 矿机型号库 | model_name, hashrate_th, power_w, efficiency |
| `user_miners` | 用户矿机配置 | user_id, miner_model_id, quantity |
| `network_snapshots` | 网络历史数据 | btc_price, difficulty, hashrate, recorded_at |
| `market_analytics` | 市场分析数据 | btc_price, network_hashrate, fear_greed_index |
| `login_records` | 登录记录 | user_id, login_time, ip_address |

#### CRM系统表

| 表名 | 用途 | 状态枚举 |
|------|------|----------|
| `crm_customers` | 客户信息 | - |
| `crm_contacts` | 联系人 | - |
| `crm_leads` | 销售线索 | NEW, CONTACTED, QUALIFIED, NEGOTIATION, WON, LOST |
| `crm_deals` | 交易记录 | DRAFT, PENDING, APPROVED, SIGNED, COMPLETED, CANCELED |
| `crm_invoices` | 发票 | DRAFT, SENT, PAID, OVERDUE, CANCELLED |
| `crm_assets` | 资产设备 | - |
| `crm_activities` | 客户活动 | - |
| `commission_records` | 佣金记录 | - |

#### 托管服务表

| 表名 | 用途 | 字段 |
|------|------|------|
| `hosting_sites` | 托管站点 | name, location, capacity_mw, electricity_rate, status |
| `hosting_miners` | 托管矿机 | site_id, client_id, serial_number, model, status |
| `miner_telemetry` | 矿机遥测 | miner_id, hashrate_actual, temp, uptime |
| `hosting_incidents` | 事故记录 | site_id, severity, description, resolved |
| `hosting_tickets` | 工单系统 | client_id, type, priority, status |
| `hosting_bills` | 账单管理 | client_id, amount, status, due_date |
| `hosting_contracts` | 托管合同 | client_id, site_id, sla_template_id |
| `sla_templates` | SLA模板 | name, uptime_guarantee, response_time |
| `hosted_devices` | 托管设备 | device_serial, hashrate, power, hosting_fee |

#### 区块链 & SLA表

| 表名 | 用途 |
|------|------|
| `blockchain_records` | 区块链记录 |
| `sla_metrics` | SLA指标 |
| `sla_certificate_records` | SLA证书NFT |
| `monthly_reports` | 月度报告 |
| `system_performance_logs` | 性能日志 |

#### 订阅 & 支付表

| 表名 | 用途 | 字段 |
|------|------|------|
| `subscription_plans` | 订阅计划 | name, plan_type, price_monthly, max_miners |
| `user_subscriptions` | 用户订阅 | user_id, plan_id, status, expires_at |
| `payments` | 支付记录 | subscription_id, amount, currency, status, crypto_currency, tx_hash |
| `api_usage` | API使用统计 | user_id, endpoint, calls_count, date |

#### 智能层表

| 表名 | 用途 |
|------|------|
| `forecast_daily` | 每日预测 |
| `ops_schedule` | 运营排程 |
| `treasury_positions` | 财资持仓 |
| `treasury_strategies` | 卖币策略 |
| `treasury_signals` | 交易信号 |
| `backtest_results` | 回测结果 |

#### CDC事件表

| 表名 | 用途 | 字段 |
|------|------|------|
| `event_outbox` | 事务性发件箱 | event_id, event_type, payload, status |
| `event_inbox` | 消费者收件箱 | event_id, consumer_group, processed_at |
| `event_dlq` | 死信队列 | event_id, error_message, retry_count |
| `api_idempotency_records` | API幂等记录 | request_id, response, expires_at |

#### 调度器表

| 表名 | 用途 |
|------|------|
| `scheduler_leader_lock` | 调度器领导者锁 |

---

## 🔌 API端点映射 | API Endpoints

### 认证 & 用户管理

```http
POST   /api/auth/login          # 用户登录
POST   /api/auth/register       # 用户注册
POST   /api/auth/refresh        # 刷新令牌
POST   /api/auth/logout         # 登出
GET    /api/auth/me             # 获取当前用户
GET    /verify-email/:token     # 邮箱验证

# 管理员端点
GET    /admin/user_access                # 用户列表
POST   /admin/user_access/add            # 添加用户
PUT    /admin/user_access/edit/:id       # 编辑用户
POST   /admin/user_access/revoke/:id     # 撤销访问
GET    /admin/login_records              # 登录历史
```

### 核心计算API

```http
POST   /api/calculate                    # 主计算API (app.py:6189)
GET    /api/user-miners                  # 获取用户矿机
POST   /api/user-miners                  # 保存矿机配置
POST   /batch/api/upload                 # 上传CSV批量导入
GET    /api/miners/import                # 矿机导入接口
```

### 网络 & 市场数据

```http
GET    /api/btc-price                    # BTC实时价格
GET    /api/network-stats                # 网络统计
GET    /api/network-data                 # 网络数据
GET    /api/market-data                  # 市场数据
GET    /api/technical-indicators         # 技术指标
```

### Analytics API

```http
POST   /api/analytics/roi-heatmap            # ROI热力图
POST   /api/analytics/historical-replay      # 历史回放
POST   /api/analytics/curtailment-simulation # 停电模拟
GET    /api/analytics/data                   # 统一分析数据
GET    /api/price-trend                      # 价格趋势
GET    /api/difficulty-trend                 # 难度趋势
GET    /api/hashrate-analysis                # 算力分析
```

### Intelligence Layer API

```http
# 预测
GET    /api/intelligence/forecast/:user_id           # 获取预测
POST   /api/intelligence/forecast/:user_id/refresh   # 刷新预测

# 优化
POST   /api/intelligence/optimize/curtailment        # 停电优化请求
GET    /api/intelligence/optimize/:user_id/:date     # 获取优化排程

# 解释器
GET    /api/intelligence/explain/roi/:user_id                # ROI解释
GET    /api/intelligence/explain/roi/:user_id/change         # ROI变化分析
GET    /api/intelligence/explain/roi/:user_id/recommendations # 获取建议

# 健康检查
GET    /api/intelligence/health              # 智能层健康状态
GET    /api/intelligence/health/slo          # SLO指标
```

### CRM API

```http
# 客户
GET    /crm/customers                # 客户列表
POST   /crm/customers/add            # 添加客户
PUT    /crm/customers/:id            # 更新客户
GET    /crm/customers/view/:id       # 客户详情

# 线索
GET    /api/leads                    # 线索列表 (支持过滤)
POST   /api/leads                    # 创建线索
PUT    /api/leads/:id                # 更新线索
POST   /api/leads/:id/convert        # 转换为交易

# 交易
GET    /api/deals                    # 交易列表
PUT    /api/deals/:id/stage          # 更新交易阶段

# 发票
GET    /api/invoices                 # 发票列表
POST   /api/invoices                 # 创建发票

# 支付
GET    /api/payments                 # 支付列表
POST   /api/payments                 # 记录支付
GET    /api/payments/:id/status      # 支付状态

# 资产
GET    /api/assets                   # 资产列表
POST   /api/assets/batch-import      # 批量导入
PATCH  /api/assets/:id/status        # 更新状态
```

### Hosting API

```http
GET    /hosting/status/:site_slug            # 公开站点状态
GET    /hosting/api/overview                 # 托管概览
GET    /hosting/api/sites                    # 站点列表
POST   /hosting/api/sites                    # 创建站点
GET    /hosting/api/miners                   # 矿机列表
POST   /hosting/api/miners                   # 部署矿机
GET    /hosting/api/usage/preview            # 使用记录预览
```

### Treasury API

```http
GET    /api/treasury/overview                # 财资概览
GET    /api/treasury/signals                 # 交易信号
GET    /api/treasury/advanced-signals        # 高级信号
POST   /api/treasury-exec/execute            # 执行交易
```

### Blockchain & SLA NFT API

```http
POST   /api/blockchain/verify-data           # 验证区块链数据
POST   /api/sla/mint-certificate             # 铸造SLA证书NFT
GET    /api/blockchain/status                # 区块链状态
GET    /api/ipfs/browser                     # IPFS浏览器
POST   /api/transparency/audit               # 透明度审计
POST   /api/web3/sla/mint-request            # Web3 SLA NFT铸造请求
```

### CRM Integration API

```http
POST   /api/crm-integration/sync/customer    # 同步客户数据
POST   /api/crm-integration/sync/lead        # 同步销售线索
POST   /api/crm-integration/sync/deal        # 同步交易数据
```

### 健康检查

```http
GET    /health                               # 基本健康检查
GET    /ready                                # 就绪探针
GET    /alive                                # 存活探针
GET    /api/health                           # API健康检查
```

---

## 🌐 外部集成 | External Integrations

### 数据源API

| 服务 | 用途 | 轮询频率 | 缓存TTL |
|------|------|----------|---------|
| **CoinGecko** | BTC实时价格 | 按需 | 60秒 |
| **Blockchain.info** | 网络统计 (难度、算力) | 10分钟 | 10分钟 |
| **CoinWarz** | 多币种挖矿数据 | 按需 | 15分钟 |
| **Alternative.me** | 恐惧贪婪指数 | 1小时 | 1小时 |
| **Ankr RPC** | Bitcoin区块链RPC | 实时 | 60秒 |

### 交易所API (衍生品数据)

| 交易所 | 用途 | 连接方式 | 数据类型 |
|--------|------|----------|----------|
| **Deribit** | 资金费率、持仓量、期权数据 | WebSocket + REST | 衍生品 |
| **OKX** | 衍生品数据、市场深度 | WebSocket | 衍生品 |
| **Binance** | 市场数据、价格趋势 | REST API | 现货/衍生品 |

### 基础设施服务

| 服务 | 用途 | 连接URL | 配置 |
|------|------|---------|------|
| **PostgreSQL** | 主数据库 | `DATABASE_URL` | Neon托管 |
| **Redis** | 缓存 & 分布式锁 | `REDIS_URL` (端口6379) | 本地/云 |
| **Kafka** | 事件流 | `localhost:9092` | CDC平台 |
| **Debezium** | CDC捕获 | `localhost:8083` | 连接器 |

### 第三方集成

| 服务 | 用途 | 配置 |
|------|------|------|
| **SendGrid** | 邮件发送 | API Key |
| **Pinata/IPFS** | NFT元数据存储 | API Key + Gateway |
| **Base L2 (Sepolia)** | 智能合约部署 | RPC URL + Private Key |
| **Stripe** | 支付处理 | Webhook + API Key |

---

## ⚡ 缓存策略 | Caching Strategy

### Redis缓存键模式

#### 实时数据 (TTL: 5-60秒)
```python
"btc_price"                           # BTC价格
"network_hashrate"                    # 网络算力
"network_difficulty"                  # 网络难度
"fear_greed_index"                    # 恐惧贪婪指数
```

#### 矿机数据 (TTL: 1小时)
```python
"miner_specs:{model_id}"              # 矿机规格
"miner_models"                        # 所有型号
"miner_inventory:{user_id}"           # 用户矿机清单
```

#### 计算结果 (TTL: 5分钟)
```python
"calculation:{user_id}:{params_hash}" # 计算结果缓存
"batch_result:{job_id}"               # 批量计算结果
```

#### 分析数据 (TTL: 5分钟-1小时)
```python
"technical_indicators"                # 技术指标
"market_analytics"                    # 市场分析
"price_trend:{timeframe}"             # 价格趋势
"difficulty_trend:{timeframe}"        # 难度趋势
```

#### Intelligence Layer (TTL: 30分钟)
```python
"intelligence:forecast:{user_id}"                 # 预测数据
"intelligence:ops_schedule:{user_id}:{date}"      # 优化排程
"intelligence:roi_explain:{user_id}"              # ROI解释
```

#### 用户数据 (TTL: 30分钟)
```python
"user_plan:{user_id}"                 # 用户订阅计划
"user_stats:{user_id}"                # 用户统计
"user_portfolio:{user_id}"            # 用户投资组合
```

### 分布式锁模式

#### 调度器领导者锁
```python
"blockchain_scheduler_leader"         # TTL: 60秒
"event_scheduler_lock"                # 可配置TTL
"data_collector_lock"                 # TTL: 300秒
```

#### 任务级锁
```python
"lock:recalc:user:{user_id}"          # TTL: 300秒
"lock:refresh:{user_id}"              # TTL: 60秒
"lock:forecast:{user_id}"             # TTL: 120秒
```

#### CDC平台锁
```python
"lock:user:{user_id}:portfolio"       # TTL: 60秒
"lock:outbox:publish"                 # TTL: 30秒
```

### 缓存策略

#### Stale-While-Revalidate (SWR)
```python
# 返回缓存数据 + 后台异步刷新
def get_with_swr(key, fetch_fn, ttl=300):
    cached = redis.get(key)
    if cached:
        # 后台异步刷新
        if redis.ttl(key) < ttl / 2:
            background_refresh(key, fetch_fn, ttl)
        return cached
    return fetch_and_cache(key, fetch_fn, ttl)
```

---

## 🔄 CDC事件平台 | CDC Event Platform

### 架构概览

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│   Main App  │─────>│ Transactional│─────>│  Debezium   │─────>│    Kafka     │
│  (Flask)    │      │    Outbox    │      │  Connector  │      │   Topics     │
└─────────────┘      └──────────────┘      └─────────────┘      └──────────────┘
                              │                                          │
                              │                                          │
                              ▼                                          ▼
                     ┌─────────────────┐                    ┌──────────────────┐
                     │   PostgreSQL    │                    │    Consumers     │
                     │  (WAL Logical)  │                    │  - Portfolio     │
                     │  + RLS Policies │                    │  - Intelligence  │
                     └─────────────────┘                    │  - CRM Sync      │
                                                            └──────────────────┘
```

### 核心组件

#### 1. Transactional Outbox (事务性发件箱)
> **实现**: `cdc-platform/core/infra/outbox.py` - `OutboxPublisher`类

- **模式**: 在同一数据库事务中写入业务数据和事件
- **表**: `event_outbox`
- **字段**: id, kind, user_id, tenant_id, entity_id, payload (JSONB), idempotency_key, created_at, processed
- **幂等性**: 使用`idempotency_key`防止重复事件 (ON CONFLICT DO NOTHING)
- **路由**: 按kind字段路由到不同Kafka主题

#### 2. Debezium CDC
- **作用**: 从PostgreSQL WAL捕获变更
- **连接器**: `hashinsight-outbox`
- **SMT**: EventRouter转换器
- **配置**:
  ```json
  {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "plugin.name": "pgoutput",
    "publication.autocreate.mode": "filtered",
    "table.include.list": "public.event_outbox"
  }
  ```

#### 3. Kafka Topics
- `events.miner` - 矿机相关事件
- `events.treasury` - 财资操作事件
- `events.ops` - 运营事件
- `events.crm` - CRM事件
- `events.dlq` - 死信队列

#### 4. Event Consumers

> **说明**: 基于cdc-platform/workers目录的实际实现

| 消费者 | 文件路径 | Consumer Group | 订阅主题 | 功能 |
|--------|---------|---------------|----------|------|
| **Portfolio Consumer** | `workers/portfolio_consumer.py` | `portfolio-recalc-group` | `events.miner` | 投资组合重算 |
| **Intelligence Consumer** | `workers/intel_consumer.py` | `intel-group` | `events.miner`, `events.ops` | 预测&优化触发 |

#### 5. Inbox Idempotency (幂等保证)
> **实现**: 基于CDC平台migrations/002_inbox_idempotency.sql

- **表**: `event_inbox`
- **字段**: event_id, consumer_group, processed_at
- **机制**: 
  ```python
  # 消费前检查（基于实际实现）
  # 1. 查询event_inbox表检查是否已处理
  SELECT EXISTS(SELECT 1 FROM event_inbox 
                WHERE event_id = :id AND consumer_group = :group)
  
  # 2. 如果未处理，执行业务逻辑
  process_event(event)
  
  # 3. 插入inbox记录（原子性保证）
  INSERT INTO event_inbox (event_id, consumer_group, processed_at)
  VALUES (:event_id, :consumer_group, NOW())
  ```

#### 6. Dead Letter Queue (DLQ)
> **实现**: 基于CDC平台migrations和replay脚本

- **表**: `event_dlq`
- **字段**: event_id, kind, user_id, payload, error_message, retry_count, failed_at, replayed_at (migration 005)
- **触发**: 处理失败后写入DLQ
- **重放脚本**: `cdc-platform/scripts/replay_dlq.py`
  - `stats`: 查看DLQ统计
  - `replay --hours N --dry-run`: 模拟重放
  - `replay --hours N --limit M`: 实际重放

### 事件流示例

#### 1. 矿机配置更新流程
```
1. 用户更新矿机配置
   ↓
2. Flask API写入user_miners表 + event_outbox表 (同一事务)
   ↓
3. Debezium捕获WAL变更
   ↓
4. 发布到Kafka events.miner主题
   ↓
5. Portfolio Consumer消费
   ↓
6. 检查inbox幂等
   ↓
7. 重算ROI并更新数据库
   ↓
8. 失败 → DLQ (可重放)
```

#### 2. 停电优化流程
```
1. 用户提交停电优化请求
   ↓
2. Intelligence API创建事件
   ↓
3. 发布到events.ops
   ↓
4. Power Optimizer Consumer消费
   ↓
5. 线性规划求解
   ↓
6. 保存到ops_schedule表
   ↓
7. 通知用户 (WebSocket/邮件)
```

### 监控 & 运维

#### Health Check API
```bash
curl http://localhost:5000/api/health | jq
```

**关键指标**:
- `checks.database.response_time_ms` - 数据库响应时间
- `checks.outbox.backlog` - Outbox积压
- `checks.kafka_consumer.total_lag` - 消费者延迟
- `checks.dlq.count` - DLQ事件数

#### Kafka Consumer Lag监控
```bash
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group portfolio-recalc-group \
  --describe
```

#### DLQ重放
```bash
# 查看DLQ统计
python scripts/replay_dlq.py stats

# 重放最近6小时的失败事件 (dry run)
python scripts/replay_dlq.py replay --hours 6 --dry-run

# 实际重放
python scripts/replay_dlq.py replay --hours 6 --limit 100
```

---

## 📊 数据流向 | Data Flow

### 1. 主计算流程

```
用户输入参数 (矿机型号、电价、数量)
         ↓
   POST /api/calculate
         ↓
  查询miner_models表 (矿机规格)
         ↓
  查询network_snapshots表 (网络数据)
         ↓
  调用CoinGecko API (实时BTC价格)
         ↓
  双算法计算 (Python)
    - Algorithm 1: 基础盈利计算
    - Algorithm 2: 高级模型 (停电、衰减)
         ↓
  Redis缓存结果 (TTL 5分钟)
         ↓
  返回JSON响应
    {
      daily_revenue,
      daily_cost,
      daily_profit,
      roi_days,
      chart_data
    }
```

### 2. 智能预测流程

```
用户请求预测
         ↓
GET /api/intelligence/forecast/{user_id}
         ↓
  检查Redis缓存 (TTL 30分钟)
         ↓
  缓存未命中 → 查询forecast_daily表
         ↓
  数据过期/不存在 → 触发ARIMA模型计算
    - 从network_snapshots获取90天历史数据
    - 训练ARIMA(1,1,1)模型
    - 生成7天预测 + 置信区间
         ↓
  保存到forecast_daily表
         ↓
  发布CDC事件 → Kafka (events.miner)
         ↓
  缓存结果到Redis
         ↓
  返回预测结果
    {
      predictions: [{date, price, lower_bound, upper_bound}],
      rmse, mae, model_params
    }
```

### 3. CDC事件流 (完整链路)

```
业务操作 (如更新矿机配置)
         ↓
  BEGIN TRANSACTION
         ↓
  UPDATE user_miners SET quantity = 5 WHERE id = 123
         ↓
  INSERT INTO event_outbox (event_type, payload)
    VALUES ('miner.portfolio_updated', {...})
         ↓
  COMMIT TRANSACTION
         ↓
Debezium捕获WAL变更 (< 200ms)
         ↓
  发布到Kafka主题: events.miner
         ↓
Portfolio Consumer消费 (Consumer Group: portfolio-recalc-group)
         ↓
  检查event_inbox (幂等性)
    - 如果event_id已存在 → 跳过
         ↓
  获取分布式锁: lock:user:{user_id}:portfolio
         ↓
  执行业务逻辑:
    1. 查询用户所有矿机
    2. 获取最新网络数据
    3. 重算ROI
    4. 更新用户仪表盘
         ↓
  INSERT INTO event_inbox (event_id, consumer_group)
         ↓
  释放分布式锁
         ↓
  处理成功 → ACK Kafka消息
         ↓
处理失败 (重试3次后)
         ↓
  INSERT INTO event_dlq (event_id, error_message, retry_count)
         ↓
  可通过scripts/replay_dlq.py重放
```

### 4. 停电优化流程

```
用户提交停电优化请求
         ↓
POST /api/intelligence/optimize/curtailment
  {
    user_id, curtailment_hours, target_date
  }
         ↓
  验证用户权限 (OPS_PLAN)
         ↓
  查询用户矿机配置
         ↓
  构建线性规划模型 (PuLP)
    目标: 最大化收益
    约束:
      - 停电小时数限制
      - 矿机功率限制
      - 网络难度
         ↓
  求解优化问题
         ↓
  保存到ops_schedule表
         ↓
  发布CDC事件 → events.ops
         ↓
  返回优化结果
    {
      schedule: [{hour, active_miners, profit}],
      total_profit, curtailment_impact
    }
```

### 5. 数据收集流程 (调度器)

```
启动时: 调度器领导者选举
         ↓
  acquire_lock('blockchain_scheduler_leader', ttl=60s)
         ↓
  成功获取锁 → 启动调度任务
         ↓
定时任务 (每10分钟)
         ↓
  并行调用外部API:
    - CoinGecko (BTC价格)
    - Blockchain.info (难度、算力)
    - Alternative.me (恐惧贪婪指数)
         ↓
  数据验证 & 清洗
         ↓
  INSERT INTO network_snapshots (btc_price, difficulty, ...)
         ↓
  Redis缓存刷新
    - btc_price (TTL 60s)
    - network_hashrate (TTL 60s)
    - fear_greed_index (TTL 3600s)
         ↓
  发布CDC事件 → events.miner
         ↓
  触发依赖Consumer:
    - Portfolio Recalc
    - Intelligence Forecast
```

---

## 🎯 技术栈 | Technology Stack

### 后端技术栈

#### Web框架
- **Flask** 3.0+ - Web应用框架
- **Gunicorn** - 生产WSGI服务器
- **Werkzeug** - WSGI工具库 (密码哈希)

#### 数据库 & ORM
- **PostgreSQL** 15+ - 主数据库 (Neon托管)
- **SQLAlchemy** 2.0+ - ORM
- **Psycopg2** - PostgreSQL适配器

#### 缓存 & 消息队列
- **Redis** 7+ - 缓存 & 分布式锁
- **Kafka** 3.6+ - 事件流
- **Debezium** 2.5+ - CDC连接器
- **RQ (Redis Queue)** - 任务队列

#### AI/ML
- **NumPy** - 数值计算
- **Pandas** - 数据分析
- **statsmodels** - ARIMA时间序列预测
- **XGBoost** - 高级预测模型
- **PuLP** - 线性规划优化
- **scikit-learn** - 机器学习工具

#### 区块链
- **Web3.py** - 以太坊交互
- **eth-account** - 账户管理
- **Base L2** - Layer 2网络

#### 外部API客户端
- **requests** - HTTP客户端
- **aiohttp** - 异步HTTP
- **websocket-client** - WebSocket客户端

#### 监控 & 日志
- **logging** - Python标准日志
- **psutil** - 系统监控

### 前端技术栈

#### 模板 & UI
- **Jinja2** - 模板引擎
- **Bootstrap 5** - UI框架 (暗色主题)
- **Bootstrap Icons** - 图标库
- **Chart.js** - 数据可视化
- **Feather Icons** - SVG图标

#### JavaScript
- **Vanilla JS** - 无框架，轻量级
- **Fetch API** - AJAX请求

### DevOps & 部署

#### 容器化
- **Docker** - 容器化
- **Docker Compose** - 多服务编排

#### CI/CD
- **GitHub Actions** - 自动化CI/CD
- **7阶段流水线**:
  1. Lint & Format Check
  2. Unit Tests
  3. Integration Tests
  4. Docker Build
  5. Security Scan
  6. Deploy to Staging
  7. Deploy to Production

#### 监控 & 告警
- **Prometheus** (计划) - 指标收集
- **Grafana** (计划) - 可视化
- **自定义健康检查** - `/health`, `/ready`, `/alive`

### 第三方服务

#### 数据源
- **CoinGecko API** - 加密货币价格
- **Blockchain.info API** - 比特币网络数据
- **CoinWarz API** - 挖矿数据
- **Alternative.me API** - 恐惧贪婪指数
- **Ankr RPC** - 免费Bitcoin RPC

#### 交易所
- **Deribit API** - 衍生品数据
- **OKX API** - 交易数据
- **Binance API** - 市场数据

#### 通信 & 存储
- **SendGrid** - 邮件服务
- **Pinata** - IPFS网关
- **Gmail SMTP** - 邮件发送

#### 支付
- **Stripe** - 传统支付
- **加密货币支付** - BTC, ETH, USDC, USDT

---

## 📈 性能优化

### 缓存优化
- **多级缓存**: 内存 + Redis
- **SWR策略**: Stale-While-Revalidate
- **智能预热**: 启动时加载热数据
- **TTL分层**: 5秒 ~ 1小时

### 数据库优化
- **连接池**: SQLAlchemy连接池
- **索引优化**: 关键字段索引
- **查询优化**: N+1问题解决
- **数据清理**: 自动清理过期数据 (每日10个数据点上限)

### API优化
- **批量处理**: 批量计算优化
- **异步任务**: RQ后台任务
- **请求限流**: Rate limiting
- **响应压缩**: Gzip

### CDC性能
- **Outbox轮询**: 200ms间隔
- **批量发布**: 单次最多100条
- **分区策略**: 按user_id分区
- **消费者扩展**: 水平扩展支持

---

## 🔒 安全 & 合规

### 认证 & 授权
- **会话管理**: Flask session (httpOnly, Secure, SameSite=None, Partitioned)
- **密码加密**: Werkzeug PBKDF2 (默认)
- **CSRF保护**: 自定义CSRF token
- **RBAC**: 角色权限矩阵

### 数据安全
- **PostgreSQL RLS**: Row-Level Security
- **多租户隔离**: Tenant-scoped查询
- **API密钥轮换**: 自动密钥管理
- **审计日志**: 操作日志记录

### 支付合规
- **AML检查**: Anti-Money Laundering
- **KYC验证**: Know Your Customer
- **风险评分**: 交易风险评估
- **合规审计**: Compliance tracking

---

## 🚀 部署架构

### 生产环境

```
┌─────────────────────────────────────────────────┐
│                  Load Balancer                  │
└─────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │ Flask   │    │ Flask   │    │ Flask   │
   │ Worker1 │    │ Worker2 │    │ Worker3 │
   └─────────┘    └─────────┘    └─────────┘
        │               │               │
        └───────────────┼───────────────┘
                        ▼
              ┌──────────────────┐
              │   PostgreSQL     │
              │   (Neon/RDS)     │
              └──────────────────┘
                        ▼
              ┌──────────────────┐
              │      Redis       │
              │   (ElastiCache)  │
              └──────────────────┘
                        ▼
              ┌──────────────────┐
              │   Kafka Cluster  │
              │  (3 Brokers)     │
              └──────────────────┘
```

### Docker Compose配置

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: hashinsight
      POSTGRES_USER: hashinsight
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
  
  zookeeper:
    image: confluentinc/cp-zookeeper:latest
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
  
  kafka:
    image: confluentinc/cp-kafka:latest
    depends_on:
      - zookeeper
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
  
  debezium:
    image: debezium/connect:2.5
    depends_on:
      - kafka
      - postgres
    environment:
      BOOTSTRAP_SERVERS: kafka:9092
      GROUP_ID: 1
      CONFIG_STORAGE_TOPIC: debezium_configs
  
  app:
    build: .
    command: gunicorn --bind 0.0.0.0:5000 --workers 4 main:app
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: redis://redis:6379/0
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
  
  portfolio-consumer:
    build: .
    command: python intelligence/workers/portfolio_consumer.py
    depends_on:
      - kafka
      - postgres
```

---

## 📊 监控指标

### SLO目标

| 指标 | 设计目标 |
|------|---------|
| API可用性 | 99.95% |
| P95响应时间 | <250ms |
| P99响应时间 | <500ms |
| Write-to-Visible延迟 (P95) | <3s |
| 数据库连接池利用率 | <80% |
| Redis命中率 | >90% |

> **说明**: 以上为设计目标，实际性能指标需通过监控系统测量

### 关键指标

#### 应用层
- 请求吞吐量 (req/s)
- 响应时间分布 (P50/P95/P99)
- 错误率 (4xx/5xx)
- 慢端点追踪

#### 数据库
- 连接池状态
- 查询执行时间
- 慢查询日志
- 死锁检测

#### 缓存
- 命中率
- 驱逐率
- 内存使用
- 连接数

#### CDC平台
- Outbox积压
- Kafka消费者延迟
- DLQ事件数
- 重放成功率

---

## 🔧 运维工具

### 健康检查
```bash
# 基本健康检查
curl http://localhost:5000/health

# API健康检查 (详细)
curl http://localhost:5000/api/health | jq

# SLO指标
curl http://localhost:5000/api/intelligence/health/slo | jq
```

### CDC运维
```bash
# DLQ统计
python scripts/replay_dlq.py stats

# DLQ重放 (dry run)
python scripts/replay_dlq.py replay --hours 6 --dry-run

# DLQ重放 (实际)
python scripts/replay_dlq.py replay --hours 6 --limit 100

# Kafka消费者状态
kafka-consumer-groups --bootstrap-server localhost:9092 \
  --group portfolio-recalc-group \
  --describe
```

### 数据库维护
```bash
# 数据库连接测试
python -c "from database_health import db_health_manager; \
  print(db_health_manager.check_database_connection(os.environ['DATABASE_URL']))"

# 执行SQL (开发环境)
flask db execute "SELECT COUNT(*) FROM network_snapshots WHERE recorded_at > NOW() - INTERVAL '7 days'"
```

### 缓存管理
```bash
# 清空特定模式缓存
redis-cli KEYS "intelligence:*" | xargs redis-cli DEL

# 查看缓存统计
redis-cli INFO stats
```

---

## 📚 文档索引

### 架构文档
- `ARCHITECTURE.md` - 系统架构概览
- `cdc-platform/README.md` - CDC平台完整文档
- `cdc-platform/docs/CDC_COMPLETE_ARCHITECTURE.md` - CDC深度技术文档
- `DEPLOYMENT.md` - 部署指南

### API文档
- `crm-saas-node/docs/openapi.yaml` - OpenAPI规范
- `crm-saas-node/docs/API_EXAMPLES.md` - API使用示例
- `module_communication/documentation/API_DOCUMENTATION.md` - 模块通信API

### 业务文档
- `PRODUCT_INTRODUCTION.md` - 产品介绍
- `OPERATIONS_MANUAL.md` - 运营手册
- `智能层使用指南.md` - Intelligence Layer使用指南
- `矿机批量导入使用教程.md` - 批量导入教程

### 技术白皮书
- `BENCHMARK_WHITEPAPER_EN.md` - 计算基准白皮书
- `DATA_SOURCE_RELIABILITY_EN.md` - 数据源可靠性分析
- `SECURITY_COMPLIANCE_EVIDENCE_INDEX_EN.md` - 安全合规证据

---

## 🤝 贡献指南

### Git工作流
```bash
# 1. Fork仓库
# 2. 创建特性分支
git checkout -b feature/amazing-feature

# 3. 提交更改 (遵循Conventional Commits)
git commit -m "feat: add amazing feature"

# 4. 推送到分支
git push origin feature/amazing-feature

# 5. 创建Pull Request
```

### 代码规范
- **Python**: PEP 8, Black格式化
- **JavaScript**: ESLint, Prettier
- **SQL**: 使用参数化查询防止注入
- **Commit**: Conventional Commits格式

---

## 📞 支持与联系

### 技术支持
- **文档**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/hxl2022hao/hashinsight/issues)
- **Email**: hxl2022hao@gmail.com

### 紧急联系
- **生产故障**: 联系DevOps团队
- **安全问题**: security@hashinsight.net
- **数据问题**: 联系DBA团队

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**Built with ❤️ by the HashInsight Team**

*最后更新: 2025年10月*
