# HashInsight Enterprise — 应用总览 / Application Overview

> 企业级比特币矿业智能管理平台
> Enterprise-Grade Bitcoin Mining Intelligence Platform

---

## 目录 / Table of Contents

1. [平台简介 / Platform Introduction](#1-平台简介--platform-introduction)
2. [系统架构 / System Architecture](#2-系统架构--system-architecture)
3. [功能模块详解 / Feature Modules](#3-功能模块详解--feature-modules)
4. [数据流与集成 / Data Flow & Integrations](#4-数据流与集成--data-flow--integrations)
5. [安全体系 / Security Architecture](#5-安全体系--security-architecture)
6. [技术栈 / Technology Stack](#6-技术栈--technology-stack)
7. [项目规模 / Project Scale](#7-项目规模--project-scale)

---

## 1. 平台简介 / Platform Introduction

HashInsight Enterprise 是一个面向比特币矿场业主、托管服务商和矿业投资人的**一站式智能管理平台**，覆盖从投资决策、日常运营、设备管理到财务分析的全链条业务。

**核心价值 / Core Value Proposition:**

- **精准决策** — 双算法交叉验证的收益分析，实时接入市场数据
- **智能运维** — AI 驱动的异常检测、故障诊断和自动执行闭环
- **全链管理** — 从矿机上架到 BTC 入账的完整业务流程
- **企业安全** — SOC2 合规、三级凭证保护、不可篡改审计日志
- **双语支持** — 中文/英文无刷新动态切换

---

## 2. 系统架构 / System Architecture

### 整体架构图 / Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    前端表示层 / Presentation Layer               │
│          Jinja2 + Bootstrap 5 + Chart.js + i18n.js              │
├─────────────────────────────────────────────────────────────────┤
│                    应用层 / Application Layer                    │
│   Flask + Blueprints (50+ blueprints)                           │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│   │ 计算引擎 │ │ 托管服务 │ │ CRM系统  │ │ 控制平面         │  │
│   │Calculator│ │ Hosting  │ │ CRM      │ │ Control Plane    │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│   │ AI闭环   │ │ 边缘采集 │ │ 安全中心 │ │ 财资管理         │  │
│   │ AI Loop  │ │ Edge Col │ │ Security │ │ Treasury         │  │
│   └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    服务层 / Service Layer                        │
│   40+ 专业服务 (异常检测、基线、调度、加密、优化...)            │
├─────────────────────────────────────────────────────────────────┤
│                    数据层 / Data Layer                           │
│   PostgreSQL (87 models) + Redis (Cache + Queue)                │
├─────────────────────────────────────────────────────────────────┤
│                    外部集成 / External Integrations              │
│   CoinGecko · CoinWarz · Blockchain.info · Deribit · Binance   │
│   OKX · Ankr RPC · Gmail SMTP · IP-API · Stripe                │
└─────────────────────────────────────────────────────────────────┘
```

### 设计模式 / Design Patterns

| 模式 | 说明 |
|------|------|
| **Application Factory** | 应用工厂模式，支持多环境配置 |
| **Blueprint Modular** | 50+ Blueprint 模块化路由 |
| **SWR Caching** | Stale-While-Revalidate 缓存策略 |
| **RBAC v2.0** | 基于角色的精细访问控制 |
| **ABAC** | 基于属性的客户隔离 |
| **E2EE** | 设备信封加密 (零知识) |
| **Event-Driven** | 事件驱动的智能系统 |
| **Closed-Loop** | AI 检测→诊断→执行→审计闭环 |

---

## 3. 功能模块详解 / Feature Modules

### 3.1 挖矿收益计算器 / Mining Profitability Calculator

**路径 / Path:** `/calculator`

精准的比特币挖矿收益分析工具。

| 功能 | 说明 |
|------|------|
| 双算法分析 | 两种独立算法交叉验证，结果更可靠 |
| 实时数据接入 | 自动获取 BTC 价格、全网难度、区块奖励 |
| ROI 分析 | 投资回报率、回本周期、盈亏平衡点 |
| 批量计算 | 一次分析多台不同型号矿机的综合收益 |
| 敏感性分析 | 电价、币价、难度变化对收益的影响模拟 |

---

### 3.2 托管服务管理 / Hosting Services

**路径 / Path:** `/hosting`

面向矿场托管运营的全套管理系统。

#### 核心仪表盘
- **运营仪表盘** (`/hosting/dashboard`) — 矿场整体运营状态总览
- **KPI 仪表盘** (`/hosting/kpi`) — 在线率、算力利用率、能效比等关键指标
- **全局状态** (`/hosting/global-status`) — 跨站点全局健康视图
- **事件监控** (`/hosting/events`) — 实时运维事件流

#### 矿机管理
- **矿机列表** (`/hosting/miners`) — 全部矿机的温度、算力、风扇、板卡状态
- **矿机详情** (`/hosting/miner/<id>`) — 单台矿机的详细遥测数据与历史趋势
- **矿机入网向导** (`/hosting/miner-setup`) — 新矿机上架引导

#### 站点管理
- **站点管理** (`/hosting/sites`) — 矿场站点的增删改查
- **站点详情** (`/hosting/site/<id>`) — 单个站点的详细信息与统计
- **站点设置** (`/hosting/site/<id>/settings`) — 站点配置与参数

#### 运维工具
- **自动化规则** (`/hosting/automation`) — 自动化运维规则配置
- **电力削减** (`/hosting/curtailment`) — 智能电力管理调度
- **功耗分析** (`/hosting/power`) — 电力消耗统计与分析

#### 客户门户
- **客户仪表盘** (`/hosting/client`) — 托管客户的自助查看界面
- **客户矿机** (`/hosting/client/miners`) — 客户名下矿机列表
- **客户报告** (`/hosting/client/reports`) — 自动生成的运营报告
- **客户工单** (`/hosting/client/tickets`) — 客户提交与跟踪工单
- **用量统计** (`/hosting/client/usage`) — 电力与资源用量统计
- **告警中心** (`/hosting/client/alerts`) — 客户相关告警通知

#### 品牌管理
- **白标品牌** (`/hosting/branding`) — 客户自定义品牌与界面

---

### 3.3 问题注册与异常检测 / Problem Registry & Anomaly Detection

**API 路径 / Path:** `/hosting/api/sites/<site_id>/...`

全自动矿机健康管理系统，8 步数据管线。

#### 数据管线 (Pipeline)

```
遥测数据 → 特征提取 → EWMA基线 → KMeans模式推断
    → 全舰基线 → 健康规则引擎 → 事件引擎 → 策略引擎
```

#### 服务组件

| 服务 | 功能 |
|------|------|
| BaselineService | EWMA 指数加权移动平均基线 (α=0.1) |
| ModeInferenceService | KMeans 聚类运行模式识别 (k=3) |
| FleetBaselineService | 全舰统计汇总与健康评分 |
| HealthRules | 11 条检测规则 (6 硬规则 + 5 软规则) |
| EventEngine | 事件生命周期管理 (去抖/解决/冷却) |
| DiagnosisFusion | 多证据融合诊断 |
| PolicyEngine | 通知/工单预算分配策略 |
| WeakSupervisor | 弱监督标注与反馈学习 |

#### 健康规则

**硬规则 (P0/P1 — 必须立即处理):**

| 规则代码 | 严重性 | 触发条件 |
|----------|--------|----------|
| `overheat_crit` | P0 | 温度 ≥ 85°C |
| `offline` | P0 | 矿机无响应 |
| `hashrate_zero` | P1 | 算力 = 0 |
| `boards_dead` | P1 | 活跃板卡 = 0 |
| `fan_zero` | P1 | 风扇转速 = 0 |
| `overheat_warn` | P1 | 温度 75°C ~ 85°C |

**软规则 (P2/P3 — 统计偏离检测):**

| 规则代码 | 严重性 | 触发条件 |
|----------|--------|----------|
| `hashrate_degradation` | P2 | z-score < -2.0 |
| `efficiency_degradation` | P2 | z-score > 2.0 |
| `temp_anomaly` | P2 | z-score > 2.5 |
| `fleet_outlier` | P3 | \|z-score\| > 3.0 |
| `boards_degrading` | P3 | 残差 < -0.1 |

#### API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/hosting/api/sites/<id>/health_summary` | 站点健康摘要 |
| GET | `/hosting/api/sites/<id>/problems` | 问题事件列表 (分页/过滤) |
| POST | `/hosting/api/sites/<id>/problems/<id>/suppress` | 抑制告警 |
| POST | `/hosting/api/sites/<id>/problems/<id>/resolve` | 手动关闭 |
| POST | `/hosting/api/sites/<id>/problems/batch_ack` | 批量确认 |

---

### 3.4 边缘采集架构 / Edge Collector Architecture

**路径 / Path:** `/collector`

矿场本地部署的数据采集与远程控制系统。

| 功能 | 说明 |
|------|------|
| Python 边缘采集器 | 部署在矿场本地的数据采集程序 |
| 4 层遥测存储 | raw_24h → live → history_5min → daily |
| API 密钥管理 | 采集器认证与安全通信 |
| 双向指令控制 | 云端远程操控矿机 |
| 告警规则引擎 | 本地告警触发与上报 |
| 部署指南 | 在线部署手册与本地指南 |

---

### 3.5 控制平面 / Control Plane

企业级大规模矿场运营管理系统。

| 功能 | 说明 |
|------|------|
| 区域分区管理 | 按物理位置划分矿机区域 |
| 客户隔离 (ABAC) | 基于属性的访问控制，客户间数据隔离 |
| 双人审批流程 | 关键操作需两人确认 |
| 价格计划版本管理 | 托管费率历史可追溯 |
| 15 分钟电力需量 | 精准电费核算 |
| 区块链式审计 | 不可篡改的操作记录哈希链 |
| 远程命令控制 | 安全的远程矿机操作 |
| 三级凭证保护 | 矿机登录凭证的分层加密 |

---

### 3.6 AI 闭环智能系统 / AI Closed-Loop Intelligence

**路径 / Path:** `/ai`

从检测到执行的全自动智能系统。

#### 闭环流程

```
检测 (Detect) → 诊断 (Diagnose) → 建议 (Recommend)
    → 审批 (Approve) → 执行 (Act) → 审计 (Audit) → 学习 (Learn)
```

| 功能模块 | 说明 |
|----------|------|
| AI 告警诊断 | 智能分析告警根因 |
| AI 工单起草 | 自动生成运维工单内容 |
| AI 削减顾问 | 电力削减策略建议 |
| 自动执行引擎 | 基于多维风险评估的自动操作 |
| 规则自动审批 | 低风险操作自动放行 |

#### 预测分析

| 能力 | 方法 |
|------|------|
| 时间序列预测 | ARIMA 模型 |
| 异常检测 | 统计偏离 + ML |
| 功率优化 | PuLP 线性规划 |
| 故障预测 | XGBoost 机器学习 |
| 智能 ROI 解读 | AI 辅助投资分析 |

---

### 3.7 CRM 客户关系管理 / Customer Relationship Management

**路径 / Path:** `/crm`

完整的矿业客户管理系统。

| 功能 | 说明 |
|------|------|
| 客户管理 | 客户档案、联系人、互动记录 |
| 线索管理 | 潜在客户跟踪与转化 |
| 商机管理 | 销售机会跟踪与漏斗分析 |
| 发票管理 | 账单生成与支付追踪 |
| 资产管理 | 客户名下矿机资产 |
| 经纪人模块 | 佣金管理与经纪人仪表盘 |

---

### 3.8 技术分析平台 / Technical Analysis

**路径 / Path:** `/technical-analysis`, `/deribit`

比特币市场技术分析工具。

| 功能 | 说明 |
|------|------|
| 10+ 技术指标 | 服务端计算的专业指标 |
| 历史价格分析 | BTC 多周期价格走势 |
| 期权数据分析 | Deribit 期权市场数据 |
| 多交易所数据 | Deribit、OKX、Binance |

---

### 3.9 财资管理 / Treasury Management

BTC 资产与财务管理。

| 功能 | 说明 |
|------|------|
| BTC 库存追踪 | 实时 BTC 持有量统计 |
| 成本基础分析 | 挖矿成本 vs 市场价格 |
| 现金覆盖率 | 运营资金充足度分析 |
| 卖出策略模板 | 预设卖出计划 |
| 策略回测 | 历史数据验证策略有效性 |

---

### 3.10 智能电力削减 / Smart Power Curtailment

**路径 / Path:** `/hosting/curtailment`

自动化能源管理调度系统。

| 功能 | 说明 |
|------|------|
| 自动调度 | 电价高峰时段自动降功耗 |
| 削减计划 | 可视化电力削减排程 |
| 收益分析 | 削减带来的成本节省计算 |

---

### 3.11 多格式报告 / Multi-Format Reporting

**路径 / Path:** `/reports`

专业的运营报告生成系统。

| 格式 | 说明 |
|------|------|
| PDF 报告 | 适合打印和归档 |
| Excel 报告 | 适合数据分析和二次处理 |
| PowerPoint 报告 | 适合汇报演示 |
| 角色仪表盘 | 管理员/客户/运维各有专属视图 |

---

### 3.12 用户管理与权限 / User Management & RBAC

**路径 / Path:** `/admin`

| 功能 | 说明 |
|------|------|
| 用户创建与编辑 | 管理员创建和管理用户账户 |
| 角色分配 | 精细的角色权限分配 |
| RBAC v2.0 | 基于角色的多级访问控制 |
| 访问期限管理 | 用户账户有效期设置 |
| 登录记录 | 完整的登录审计日志 |

---

### 3.13 系统监控 / System Monitoring

**路径 / Path:** `/monitor`

| 功能 | 说明 |
|------|------|
| 健康状态 | 系统各组件运行状态 |
| 性能指标 | 响应时间、吞吐量监控 |
| 缓存状态 | Redis 缓存命中率与容量 |
| 告警管理 | 系统级告警配置与查看 |

---

### 3.14 Web3 与区块链集成 / Web3 Integration

**路径 / Path:** `/web3`

| 功能 | 说明 |
|------|------|
| 钱包配置向导 | 安全设置区块链钱包凭证 |
| SLA NFT | 服务级别协议的链上存证 |
| 区块链验证 | 交易与操作的链上验证 |
| BIP32/BIP44 | 自定义 HD 钱包密钥派生 |

---

### 3.15 IP 扫描与矿机发现 / IP Scanner & Miner Discovery

| 功能 | 说明 |
|------|------|
| 网络扫描 | 自动扫描局域网发现矿机 |
| 设备识别 | 自动识别矿机型号与固件 |
| 批量导入 | 扫描结果批量导入系统 |
| IP 加密 | 矿机 IP 地址加密存储 |

---

### 3.16 SOC2 安全合规 / SOC2 Security Compliance

企业级安全合规模块。

| 功能 | 说明 |
|------|------|
| 日志留存 | 操作日志长期保存 |
| 登录安全 | 失败锁定、异常检测 |
| 密码策略 | 强度要求与定期更换 |
| 会话管理 | 超时控制与并发限制 |
| 安全告警 | 异常行为实时告警 |
| 数据访问日志 | 敏感数据访问记录 |
| PII 脱敏 | 个人信息自动脱敏显示 |

---

### 3.17 订阅与计费 / Subscription & Billing

**路径 / Path:** `/billing`

| 功能 | 说明 |
|------|------|
| 套餐管理 | 多级服务套餐选择 |
| Stripe 集成 | 在线支付与订阅管理 |
| 发票生成 | 自动生成账单 |
| 支付历史 | 完整的交易记录 |

---

### 3.18 着陆页 / Landing Page

**路径 / Path:** `/`

企业级首页，展示平台核心能力与实时统计数据。

---

## 4. 数据流与集成 / Data Flow & Integrations

### 外部 API 集成

| 服务 | 用途 | 数据 |
|------|------|------|
| CoinGecko | 加密货币价格 | BTC 实时价格、历史价格 |
| CoinWarz | 挖矿数据 | 难度、区块奖励、收益估算 |
| Blockchain.info | 网络统计 | 全网算力、交易数据 |
| Deribit | 衍生品交易 | 期权数据、波动率 |
| OKX | 交易数据 | 现货与合约市场 |
| Binance | 交易数据 | 价格与交易量 |
| Ankr RPC | 区块链 RPC | 比特币网络交互 |
| IP-API | 地理位置 | IP 地址定位 |
| Gmail SMTP | 邮件服务 | 通知与验证邮件 |
| Stripe | 支付处理 | 订阅与在线支付 |

### 数据缓存策略

```
┌──────────────────────────┐
│   SWR (Stale-While-      │
│   Revalidate) 缓存       │
│                          │
│  1. 返回缓存数据(即时)    │
│  2. 后台异步更新          │
│  3. 下次请求返回新数据    │
└──────────────────────────┘
```

- **智能降级**：API 不可用时自动使用缓存数据
- **批量调用**：合并多个 API 请求减少延迟
- **速率限制**：内置请求频率控制

### 遥测数据存储架构

```
原始数据 (raw_24h)     ←  保留 24 小时，最高精度
     ↓
实时数据 (live)        ←  当前最新状态快照
     ↓
5 分钟历史 (history)   ←  5 分钟粒度汇总
     ↓
每日汇总 (daily)       ←  日级别统计报表
```

---

## 5. 安全体系 / Security Architecture

### 认证与授权

```
                    ┌─────────────┐
                    │  用户认证    │
                    │ Email+密码  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────┴────┐ ┌────┴────┐ ┌────┴────┐
         │ RBAC    │ │ ABAC    │ │ Session │
         │ v2.0    │ │ 客户隔离│ │ 管理    │
         │ 角色权限│ │ 属性控制│ │ 超时控制│
         └─────────┘ └─────────┘ └─────────┘
```

### 加密体系

| 层级 | 技术 | 保护对象 |
|------|------|----------|
| 传输层 | HTTPS/TLS | 所有网络通信 |
| 存储层 | 设备信封加密 (E2EE) | 矿机登录凭证 |
| 应用层 | Werkzeug 哈希 | 用户密码 |
| 网络层 | IP 加密存储 | 矿机 IP 地址 |
| 区块链层 | BIP32/BIP44 | HD 钱包密钥 |

### 审计合规

- **不可篡改审计日志** — 区块链式哈希链，每条记录包含前一条的哈希
- **SOC2 Type II** — 完整的安全控制框架
- **双人审批** — 关键操作需双重确认
- **PII 脱敏** — 个人敏感信息自动遮蔽

---

## 6. 技术栈 / Technology Stack

### 后端 / Backend

| 组件 | 技术 | 版本/说明 |
|------|------|-----------|
| Web 框架 | Flask | Blueprint 模块化 |
| ORM | SQLAlchemy | 数据库抽象层 |
| 数据库 | PostgreSQL | 关系型数据库 |
| 缓存 | Redis | 缓存 + 任务队列 |
| 任务队列 | RQ (Redis Queue) | 异步任务分发 |
| WSGI 服务器 | Gunicorn | 生产部署 |
| 数据分析 | NumPy / Pandas | 数值计算 |
| 时序预测 | Statsmodels (ARIMA) | 趋势预测 |
| 机器学习 | XGBoost | 故障预测 |
| 优化求解 | PuLP | 线性规划 |
| 加密 | cryptography + eth_keys | 安全通信 |
| 迁移工具 | Alembic | 数据库版本管理 |

### 前端 / Frontend

| 组件 | 技术 | 说明 |
|------|------|------|
| 模板引擎 | Jinja2 | 服务端渲染 |
| UI 框架 | Bootstrap 5 | 移动端优先响应式 |
| 图标库 | Bootstrap Icons | 矢量图标 |
| 数据可视化 | Chart.js | 图表与仪表盘 |
| 数字动画 | CountUp.js | 数值滚动效果 |
| 国际化 | i18n.js (自研) | 中英文动态切换 |

### 基础设施 / Infrastructure

| 组件 | 技术 |
|------|------|
| 运行时 | Python 3.11 |
| 部署平台 | Replit |
| 数据库托管 | Neon (PostgreSQL) |

---

## 7. 项目规模 / Project Scale

| 指标 | 数量 |
|------|------|
| Python 代码 | 35,000+ 行 |
| HTML 模板 | 139 个 |
| 数据库模型 | 87 个 |
| Blueprint 路由模块 | 50+ 个 |
| 专业服务 | 40+ 个 |
| 外部 API 集成 | 10 个 |
| 文档文件 | 25+ 个 |

---

*HashInsight Enterprise — 从矿机插电到 BTC 入账，全链条智能管理。*

*HashInsight Enterprise — End-to-end intelligent management, from miner power-on to BTC settlement.*
