# HashInsight 平台运维手册
## Operations Manual for HashInsight Platform

**文档版本:** v2.0  
**更新日期:** 2025-10-03  
**维护团队:** HashInsight Platform Operations Team  
**分类:** INTERNAL - CONFIDENTIAL

---

## 📋 目录

1. [系统架构概览](#第1章系统架构概览)
2. [环境配置清单](#第2章环境配置清单)
3. [部署运维指南](#第3章部署运维指南)
4. [监控与告警](#第4章监控与告警)
5. [备份与恢复](#第5章备份与恢复)
6. [安全运维规范](#第6章安全运维规范)
7. [故障排查手册](#第7章故障排查手册)
8. [日常运维操作](#第8章日常运维操作)
9. [性能优化指南](#第9章性能优化指南)
10. [应急响应手册](#第10章应急响应手册)
11. [附录](#附录)

---

## 第1章：系统架构概览

### 1.1 技术栈

HashInsight 是一个企业级比特币挖矿管理平台，采用现代化技术栈：

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| **Web框架** | Flask | 3.0+ | Python Web应用框架 |
| **WSGI服务器** | Gunicorn | 21.0+ | 生产级HTTP服务器 |
| **数据库** | PostgreSQL | 15+ | 主数据存储 (Neon托管) |
| **缓存** | Redis / 内存缓存 | 7.0+ | 性能优化缓存层 |
| **区块链** | Web3.py + Base L2 | - | 区块链集成 |
| **加密** | Cryptography | 41.0+ | 企业级加密 |

### 1.2 模块架构

系统采用**完全页面隔离架构**，各模块独立部署：

```
HashInsight Platform
├── Core Application (main.py + app.py)
│   ├── Authentication & Authorization
│   ├── Session Management
│   └── Security Middleware
│
├── Mining Management Module
│   ├── Miner Dashboard
│   ├── Batch Calculator
│   └── Analytics Engine
│
├── CRM & Client Module
│   ├── Customer Management
│   ├── Billing System
│   └── Subscription Management
│
├── Blockchain Integration Module
│   ├── SLA NFT Management
│   ├── Verifiable Computing
│   └── Trust Reconciliation
│
└── Admin & Analytics Module
    ├── Market Data Analysis
    ├── Performance Monitoring
    └── Reporting System
```

### 1.3 企业级改造成果

#### 🔐 安全增强
- **KMS密钥管理**: 支持 AWS KMS、GCP KMS、Azure Key Vault
- **mTLS双向认证**: 客户端证书验证、CRL/OCSP检查
- **API密钥系统**: 基于 `hsi_dev_key_*` 格式的安全密钥
- **WireGuard VPN**: 企业级专网隔离
- **审计日志**: SOC 2 / PCI DSS / GDPR 合规

#### 📊 SLO监控
- **可用性**: ≥99.95% (错误预算 ≤21.6分钟/月)
- **延迟**: p95 ≤250ms
- **错误率**: ≤0.1%
- **Prometheus指标**: 全方位性能监控
- **熔断器**: 防止级联故障

#### ⚡ 性能优化
- **Request Coalescing**: 9.8倍性能提升
- **多级缓存**: Redis + 内存缓存
- **连接池**: PostgreSQL连接优化
- **批量处理**: 支持5000+矿机并发导入

### 1.4 部署拓扑

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
│                  (Replit/Cloud Provider)                │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼─────────┐         ┌─────────▼────────┐
│  Gunicorn       │         │  Gunicorn        │
│  Worker 1       │         │  Worker 2        │
│  Port 5000      │         │  Port 5000       │
└───────┬─────────┘         └─────────┬────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼─────────┐         ┌─────────▼────────┐
│  PostgreSQL     │         │  Redis Cache     │
│  (Neon Hosted)  │         │  (Optional)      │
└─────────────────┘         └──────────────────┘
```

---

## 第2章：环境配置清单

### 2.1 必需环境变量

这些环境变量**必须**设置，否则系统无法启动：

| 变量名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `DATABASE_URL` | String | PostgreSQL连接字符串 | `postgresql://user:pass@host:5432/db` |
| `SESSION_SECRET` | String | Flask会话密钥 (≥32字符) | `your-secure-random-secret-key-here` |
| `ENCRYPTION_PASSWORD` | String | 数据加密主密钥 (≥32字符) | `encryption-master-key-32-chars-min` |

#### 配置示例

```bash
# .env 文件示例
DATABASE_URL=postgresql://hashinsight_user:secure_password@neon-host.us-east-1.aws.neon.tech:5432/hashinsight_db
SESSION_SECRET=generate_with_python_secrets_token_urlsafe_32
ENCRYPTION_PASSWORD=generate_with_python_secrets_token_urlsafe_32
```

#### 生成安全密钥

```python
# 使用Python生成安全随机密钥
import secrets
print(f"SESSION_SECRET={secrets.token_urlsafe(32)}")
print(f"ENCRYPTION_PASSWORD={secrets.token_urlsafe(32)}")
```

### 2.2 区块链集成配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `BLOCKCHAIN_ENABLED` | Boolean | `false` | 启用区块链功能 |
| `BLOCKCHAIN_PRIVATE_KEY` | String | - | 以太坊私钥 (0x开头) |
| `BLOCKCHAIN_NETWORK` | String | `base-sepolia` | 区块链网络 |
| `BASE_RPC_URL` | String | `https://sepolia.base.org` | Base L2 RPC端点 |

```bash
# 区块链配置示例
BLOCKCHAIN_ENABLED=true
BLOCKCHAIN_PRIVATE_KEY=0x1234567890abcdef...
BLOCKCHAIN_NETWORK=base-sepolia
```

### 2.3 备份系统配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `BACKUP_DIR` | String | `/tmp/backups` | 备份存储目录 |
| `BACKUP_ENCRYPTION_KEY` | String | - | 备份加密密钥 |
| `BACKUP_RETENTION_DAYS` | Integer | `30` | 备份保留天数 |
| `BACKUP_STORAGE_TYPE` | String | `local` | 远程存储类型 (s3/azure/gcs) |
| `BACKUP_STORAGE_BUCKET` | String | - | 远程存储桶名称 |

```bash
# AWS S3 备份配置
BACKUP_DIR=/var/backups/hashinsight
BACKUP_ENCRYPTION_KEY=backup-encryption-key-32-chars
BACKUP_RETENTION_DAYS=30
BACKUP_STORAGE_TYPE=s3
BACKUP_STORAGE_BUCKET=hashinsight-backups
BACKUP_STORAGE_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxx
```

### 2.4 KMS密钥管理配置

#### AWS KMS

```bash
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789:key/xxxxx
AWS_KMS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxx
```

#### GCP KMS

```bash
GCP_KMS_PROJECT_ID=hashinsight-prod
GCP_KMS_LOCATION=us-east1
GCP_KMS_KEYRING=hashinsight-keyring
GCP_KMS_KEY_ID=encryption-key
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

#### Azure Key Vault

```bash
AZURE_KEY_VAULT_URL=https://hashinsight-vault.vault.azure.net/
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_SECRET=xxxxxxxxxx
```

### 2.5 监控和性能配置

| 变量名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `ENABLE_BACKGROUND_SERVICES` | Boolean | `false` | 启用后台数据采集（需显式设置为'1'才启用） |
| `PROMETHEUS_PORT` | Integer | `9090` | Prometheus导出端口 |
| `SLO_MEASUREMENT_WINDOW` | Integer | `30` | SLO测量窗口(分钟) |

**注意**: `FAST_STARTUP` 模式在 `main.py` 中硬编码实现，不通过环境变量配置。详见第3.4节。

### 2.6 外部API配置

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `COINWARZ_API_KEY` | CoinWarz挖矿数据API | https://www.coinwarz.com/api |
| `COINGECKO_API_KEY` | CoinGecko价格API | https://www.coingecko.com/api |
| `SENDGRID_API_KEY` | SendGrid邮件服务 | https://sendgrid.com |

### 2.7 配置文件位置

```
HashInsight/
├── config.py                    # 主配置文件 (单一数据源)
├── .env                         # 环境变量 (不提交到Git)
├── .env.example                 # 环境变量模板
└── replit.md                   # 系统架构文档
```

### 2.8 配置验证

```bash
# 检查必需环境变量
python -c "
import os
required = ['DATABASE_URL', 'SESSION_SECRET', 'ENCRYPTION_PASSWORD']
missing = [v for v in required if not os.getenv(v)]
if missing:
    print(f'❌ Missing: {missing}')
    exit(1)
print('✅ All required variables set')
"
```

---

## 第3章：部署运维指南

### 3.1 启动命令

#### 标准启动 (生产环境)

```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

#### 参数说明

| 参数 | 说明 |
|------|------|
| `--bind 0.0.0.0:5000` | 绑定所有网络接口，端口5000 (Replit必需) |
| `--reuse-port` | 允许多个worker绑定同一端口 |
| `--reload` | 代码变更时自动重载 (开发环境) |
| `--workers 4` | Worker进程数 (CPU核心数×2+1) |
| `--timeout 120` | Worker超时时间(秒) |

#### 生产环境完整启动

```bash
gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --timeout 120 \
  --max-requests 1000 \
  --max-requests-jitter 50 \
  --access-logfile - \
  --error-logfile - \
  --log-level info \
  --preload \
  main:app
```

### 3.2 端口配置

**⚠️ 重要**: 前端应用**必须**绑定到端口 5000

```bash
# 检查端口占用
lsof -i :5000

# 强制杀死占用进程
kill -9 $(lsof -t -i:5000)
```

### 3.3 健康检查

系统提供健康检查端点用于监控：

```bash
# 基本健康检查
curl http://localhost:5000/health

# 详细健康检查 (包含数据库状态)
curl http://localhost:5000/health/detailed

# 预期响应
{
  "status": "healthy",
  "timestamp": "2025-10-03T12:00:00Z",
  "database": "connected",
  "cache": "available",
  "version": "2.0.0"
}
```

### 3.4 Fast Startup 模式

HashInsight 的快速启动模式是在 **`main.py` 中硬编码实现的内置行为**，不通过 `config.py` 配置管理。

#### 实现位置

```python
# main.py 中的硬编码实现
fast_startup = os.environ.get("FAST_STARTUP", "1").lower() in ("1", "true", "yes")  # 默认启用
skip_db_check = os.environ.get("SKIP_DATABASE_HEALTH_CHECK", "1").lower() in ("1", "true", "yes")  # 默认启用
```

#### 控制方式（可选环境变量）

虽然这些变量不在 `config.py` 中定义，但可以通过环境变量临时调整：

```bash
# 启用快速启动 (默认行为，无需设置)
export FAST_STARTUP=1
export SKIP_DATABASE_HEALTH_CHECK=1

# 禁用快速启动 (完整初始化)
export FAST_STARTUP=0
export SKIP_DATABASE_HEALTH_CHECK=0
```

**⚠️ 重要说明**：
- 这些变量**不在 `config.py` 单一数据源**中定义
- 它们是 `main.py` 启动脚本的临时控制开关
- 生产环境配置应通过 `config.py` 管理

#### Fast Startup 行为

当启用时（默认）：
1. 主应用立即启动 (2-3秒)
2. 后台服务延迟5秒启动（如果 `ENABLE_BACKGROUND_SERVICES=1`）
3. 数据库健康检查跳过
4. 适合CI/CD快速部署

当禁用时：
1. 完整数据库健康检查
2. 同步启动所有服务
3. 启动时间较长（10-15秒）
4. 适合生产环境初次部署

### 3.5 数据库迁移

**⚠️ 重要**: 系统使用ORM自动迁移，**避免手动SQL操作**

```bash
# 数据库会在应用启动时自动创建表
# 参见 app.py 中的 db.create_all()

# 如需手动触发迁移
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 3.6 滚动发布策略

#### 灰度发布流程

```bash
# Step 1: 部署新版本到Canary实例
# 仅1个worker运行新版本
gunicorn --bind 0.0.0.0:5001 --workers 1 main:app

# Step 2: 监控Canary实例 (5-10分钟)
watch -n 5 'curl -s http://localhost:5001/health | jq'

# Step 3: 逐步切换流量
# 使用负载均衡器调整权重: old(90%) -> new(10%)
# 观察错误率和延迟

# Step 4: 全量切换
# old(0%) -> new(100%)
killall -9 gunicorn  # 停止旧版本
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app  # 启动新版本
```

### 3.7 优雅停机

```bash
# 发送SIGTERM信号 (优雅停机)
kill -TERM $(cat /var/run/gunicorn.pid)

# 等待30秒处理现有请求
sleep 30

# 强制停止 (如果仍在运行)
kill -KILL $(cat /var/run/gunicorn.pid)
```

### 3.8 日志管理

```bash
# 启动时启用结构化日志
export LOG_LEVEL=INFO
export LOG_FORMAT=json

# 查看实时日志
tail -f /var/log/hashinsight/app.log

# 查看错误日志
grep ERROR /var/log/hashinsight/app.log | tail -20

# Replit环境日志
# 日志输出到标准输出，通过Replit Console查看
```

### 3.9 部署检查清单

- [ ] 环境变量已配置 (DATABASE_URL, SESSION_SECRET, ENCRYPTION_PASSWORD)
- [ ] 数据库连接正常
- [ ] 端口5000可用
- [ ] 健康检查端点返回200
- [ ] 审计日志目录可写 (`logs/audit.jsonl`)
- [ ] 备份目录已创建
- [ ] SSL证书有效 (如启用mTLS)
- [ ] KMS密钥可访问 (如启用)
- [ ] Prometheus指标可访问 (`:9090/metrics`)

---

## 第4章：监控与告警

### 4.1 SLO定义

HashInsight 遵循严格的SLO标准：

#### 可用性 SLO

| 指标 | 目标 | 错误预算 | 测量周期 |
|------|------|----------|----------|
| 可用性 | ≥99.95% | ≤21.6分钟/月 | 30天滚动 |
| 成功率 | ≥99.9% | ≤43.2分钟/月 | 30天滚动 |

#### 延迟 SLO

| 百分位 | 目标 | 测量窗口 |
|--------|------|----------|
| P50 | ≤100ms | 5分钟 |
| P95 | ≤250ms | 5分钟 |
| P99 | ≤500ms | 5分钟 |

#### 错误率 SLO

| 类型 | 目标 | 阈值 |
|------|------|------|
| 4xx错误 | ≤1% | 警告 |
| 5xx错误 | ≤0.1% | 严重 |

### 4.2 Prometheus 指标

#### 系统指标导出

```python
# monitoring/prometheus_exporter.py
from prometheus_client import Counter, Histogram, Gauge

# 请求计数
request_count = Counter(
    'hashinsight_requests_total',
    'Total request count',
    ['method', 'endpoint', 'status']
)

# 请求延迟
request_latency = Histogram(
    'hashinsight_request_latency_seconds',
    'Request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

# 缓存命中率
cache_hit_rate = Gauge(
    'hashinsight_cache_hit_rate',
    'Cache hit rate percentage'
)

# 数据库查询时间
db_query_duration = Histogram(
    'hashinsight_db_query_duration_seconds',
    'Database query duration',
    ['query_type'],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5, 1.0]
)

# SLO合规性
slo_compliance = Gauge(
    'hashinsight_slo_compliance',
    'SLO compliance percentage',
    ['slo_type']
)
```

#### 指标访问

```bash
# 查看Prometheus指标
curl http://localhost:9090/metrics

# 示例输出
# HELP hashinsight_requests_total Total request count
# TYPE hashinsight_requests_total counter
hashinsight_requests_total{method="GET",endpoint="/dashboard",status="200"} 1234

# HELP hashinsight_request_latency_seconds Request latency
# TYPE hashinsight_request_latency_seconds histogram
hashinsight_request_latency_seconds_bucket{method="GET",endpoint="/api/miners",le="0.1"} 450
hashinsight_request_latency_seconds_bucket{method="GET",endpoint="/api/miners",le="0.25"} 480
```

### 4.3 Grafana 仪表板

#### 核心监控面板

```json
{
  "dashboard": {
    "title": "HashInsight Production Monitoring",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [{
          "expr": "rate(hashinsight_requests_total[5m])"
        }]
      },
      {
        "title": "P95 Latency",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(hashinsight_request_latency_seconds_bucket[5m]))"
        }]
      },
      {
        "title": "Error Rate",
        "targets": [{
          "expr": "rate(hashinsight_requests_total{status=~\"5..\"}[5m]) / rate(hashinsight_requests_total[5m])"
        }]
      },
      {
        "title": "SLO Compliance",
        "targets": [{
          "expr": "hashinsight_slo_compliance"
        }]
      }
    ]
  }
}
```

### 4.4 告警规则

#### Prometheus 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: hashinsight_alerts
    interval: 30s
    rules:
      # 可用性告警
      - alert: HighErrorRate
        expr: |
          rate(hashinsight_requests_total{status=~"5.."}[5m]) 
          / rate(hashinsight_requests_total[5m]) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High 5xx error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"

      # 延迟告警
      - alert: HighLatency
        expr: |
          histogram_quantile(0.95, 
            rate(hashinsight_request_latency_seconds_bucket[5m])
          ) > 0.25
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "P95 latency exceeds SLO"
          description: "P95 latency is {{ $value }}s (SLO: 0.25s)"

      # SLO错误预算告警
      - alert: ErrorBudgetExhausted
        expr: hashinsight_slo_error_budget_remaining < 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "SLO error budget nearly exhausted"
          description: "Only {{ $value | humanizePercentage }} budget remaining"

      # 数据库连接告警
      - alert: DatabaseConnectionFailure
        expr: hashinsight_db_connection_status == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Unable to connect to PostgreSQL"

      # 缓存命中率告警
      - alert: LowCacheHitRate
        expr: hashinsight_cache_hit_rate < 50
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low cache hit rate"
          description: "Cache hit rate is {{ $value }}%"
```

### 4.5 熔断器配置

HashInsight使用熔断器模式防止级联故障：

```python
# monitoring/circuit_breaker.py
from monitoring.circuit_breaker import CircuitBreaker, circuit_breaker

# 数据库查询熔断器
db_breaker = CircuitBreaker(
    failure_threshold=5,      # 连续失败5次触发
    recovery_timeout=60,      # 60秒后尝试恢复
    name="database_queries"
)

# API调用熔断器
@circuit_breaker(
    failure_threshold=3,
    recovery_timeout=30,
    name="external_api"
)
def call_external_api():
    response = requests.get("https://api.coinwarz.com/...")
    return response.json()
```

#### 熔断器状态监控

```bash
# 查看熔断器状态
curl http://localhost:5000/api/circuit-breakers

# 响应示例
{
  "database_queries": {
    "state": "closed",
    "failure_count": 0,
    "total_calls": 1234,
    "success_rate": "99.8%"
  },
  "external_api": {
    "state": "half_open",
    "failure_count": 3,
    "total_calls": 456,
    "success_rate": "95.2%"
  }
}
```

### 4.6 告警通知

#### Slack 集成

```bash
# 环境变量配置
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00/B00/xxxxx
ALERT_SLACK_CHANNEL=#hashinsight-alerts
```

#### PagerDuty 集成

```bash
PAGERDUTY_API_KEY=xxxxx
PAGERDUTY_SERVICE_KEY=xxxxx
```

### 4.7 监控检查清单

- [ ] Prometheus正在抓取指标 (`:9090/targets`)
- [ ] Grafana仪表板显示数据
- [ ] 告警规则已加载
- [ ] Slack/PagerDuty通知正常
- [ ] SLO监控面板显示绿色
- [ ] 熔断器状态正常

---

## 第5章：备份与恢复

### 5.1 自动备份策略

HashInsight 使用 `backup/backup_manager.py` 进行自动化备份：

#### 备份特性

- ✅ **PostgreSQL完整备份** (pg_dump)
- ✅ **AES-256加密** (备份文件加密)
- ✅ **gzip压缩** (节省存储空间)
- ✅ **远程存储** (S3/Azure/GCS支持)
- ✅ **完整性验证** (SHA256校验和)

#### 备份调度

```bash
# 通过cron配置自动备份
# /etc/cron.d/hashinsight-backup

# 每天凌晨2点执行完整备份
0 2 * * * /usr/bin/python3 /app/backup/backup_manager.py --type full

# 每4小时执行增量备份
0 */4 * * * /usr/bin/python3 /app/backup/backup_manager.py --type incremental

# 每周日凌晨3点上传到远程存储
0 3 * * 0 /usr/bin/python3 /app/backup/backup_manager.py --upload
```

### 5.2 手动备份

```bash
# 执行完整备份
python backup/backup_manager.py

# 备份输出示例
✅ 备份创建成功: hashinsight_backup_20251003_140000.sql.gz.enc
📦 大小: 245.3 MB
🔐 已加密: AES-256
✅ 校验和: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
⏱️  耗时: 45.2s
```

### 5.3 备份保留策略

| 备份类型 | 保留时间 | 频率 |
|----------|----------|------|
| 完整备份 | 30天 | 每日 |
| 增量备份 | 7天 | 每4小时 |
| 周备份 | 12周 | 每周日 |
| 月备份 | 12个月 | 每月1日 |

#### 自动清理旧备份

```bash
# 清理30天前的备份
python backup/backup_manager.py --cleanup --days 30

# 输出
🗑️  删除旧备份: hashinsight_backup_20250903_*.sql.gz.enc
✅ 清理完成: 释放 2.1 GB
```

### 5.4 RTO/RPO 目标

| 指标 | 目标 | 实际 |
|------|------|------|
| **RTO** (恢复时间目标) | ≤4小时 | ~2小时 |
| **RPO** (恢复点目标) | ≤15分钟 | ~4小时 |

### 5.5 备份恢复流程

#### Step 1: 列出可用备份

```bash
# 列出本地备份
ls -lh /tmp/backups/

# 列出远程备份 (S3)
aws s3 ls s3://hashinsight-backups/
```

#### Step 2: 下载备份 (如果在远程)

```bash
# 从S3下载
aws s3 cp s3://hashinsight-backups/hashinsight_backup_20251003_020000.sql.gz.enc /tmp/restore/

# 从Azure下载
az storage blob download \
  --account-name hashinsight \
  --container-name backups \
  --name hashinsight_backup_20251003_020000.sql.gz.enc \
  --file /tmp/restore/backup.sql.gz.enc
```

#### Step 3: 解密备份

```bash
# 使用backup_manager解密
python backup/backup_manager.py \
  --decrypt /tmp/restore/hashinsight_backup_20251003_020000.sql.gz.enc \
  --output /tmp/restore/backup.sql.gz

# 手动解密 (如果需要)
openssl enc -d -aes-256-cbc \
  -in hashinsight_backup_20251003_020000.sql.gz.enc \
  -out backup.sql.gz \
  -pass env:BACKUP_ENCRYPTION_KEY
```

#### Step 4: 解压备份

```bash
gunzip /tmp/restore/backup.sql.gz
# 输出: backup.sql
```

#### Step 5: 恢复数据库

```bash
# ⚠️ 警告: 这将覆盖现有数据库!
# 建议先备份当前数据库

# 恢复到PostgreSQL
psql $DATABASE_URL < /tmp/restore/backup.sql

# 验证恢复
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM miners;"
```

#### Step 6: 验证应用

```bash
# 重启应用
systemctl restart hashinsight

# 检查健康状态
curl http://localhost:5000/health

# 验证关键功能
curl http://localhost:5000/api/miners | jq '.count'
```

### 5.6 灾难恢复演练

**建议频率**: 每季度一次

#### 演练步骤

1. **准备演练环境**
```bash
# 创建独立的演练数据库
createdb hashinsight_dr_test
export DATABASE_URL=postgresql://localhost/hashinsight_dr_test
```

2. **模拟数据丢失**
```bash
# 删除演练数据库内容
psql $DATABASE_URL -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```

3. **执行恢复** (按5.5流程)

4. **验证恢复完整性**
```bash
# 运行数据完整性检查
python -c "
from app import app, db
from models import User, Miner
with app.app_context():
    assert db.session.query(User).count() > 0
    assert db.session.query(Miner).count() > 0
    print('✅ 恢复验证通过')
"
```

5. **记录演练结果**
   - 恢复耗时
   - 数据完整性
   - 发现的问题
   - 改进建议

### 5.7 备份监控

```bash
# 检查最近备份时间
stat -c '%y' /tmp/backups/hashinsight_backup_*.sql.gz.enc | tail -1

# 备份文件大小趋势
du -h /tmp/backups/hashinsight_backup_*.sql.gz.enc

# 备份完整性验证
python backup/backup_manager.py --verify /tmp/backups/hashinsight_backup_20251003_020000.sql.gz.enc
```

---

## 第6章：安全运维规范

### 6.1 KMS密钥管理

HashInsight 支持企业级KMS集成 (`common/crypto/envelope.py`)：

#### 信封加密原理

```
┌─────────────────────────────────────────────────┐
│  1. 应用请求加密数据                              │
│  2. KMS生成数据加密密钥(DEK)                      │
│  3. 使用DEK加密数据                               │
│  4. 使用KMS主密钥(CMK)加密DEK                     │
│  5. 存储: 加密数据 + 加密的DEK                    │
└─────────────────────────────────────────────────┘
    ▲
    │ 密钥永不离开KMS
    ▼
┌─────────────────────────────────────────────────┐
│  解密流程:                                        │
│  1. 从存储获取加密数据 + 加密DEK                  │
│  2. 调用KMS解密DEK                                │
│  3. 使用解密后的DEK解密数据                       │
└─────────────────────────────────────────────────┘
```

#### 支持的KMS提供商

##### AWS KMS

```python
# 配置AWS KMS
from common.crypto.envelope import KMSClient, KMSProvider, EncryptionContext

kms_config = {
    'key_id': 'arn:aws:kms:us-east-1:123456789:key/xxxxx',
    'region': 'us-east-1'
}

client = KMSClient(KMSProvider.AWS_KMS, kms_config)

# 加密敏感数据
context = EncryptionContext(
    purpose="user_data_encryption",
    tenant_id="tenant_123"
)

ciphertext = client.encrypt_secret(
    plaintext="sensitive data",
    key_id=kms_config['key_id'],
    context=context
)
```

##### GCP KMS

```python
# 配置GCP KMS
kms_config = {
    'project_id': 'hashinsight-prod',
    'location': 'us-east1',
    'keyring': 'hashinsight-keyring',
    'key_id': 'encryption-key'
}

client = KMSClient(KMSProvider.GCP_KMS, kms_config)
```

##### Azure Key Vault

```python
# 配置Azure Key Vault
kms_config = {
    'vault_url': 'https://hashinsight-vault.vault.azure.net/',
    'key_name': 'encryption-key'
}

client = KMSClient(KMSProvider.AZURE_KEY_VAULT, kms_config)
```

#### 密钥轮换流程

```bash
# 1. 在KMS中创建新密钥版本
aws kms create-key --description "HashInsight Master Key v2"

# 2. 更新应用配置
export AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789:key/new-key-id

# 3. 重新加密现有数据 (后台任务)
python scripts/rotate_encryption_keys.py --old-key OLD_KEY_ID --new-key NEW_KEY_ID

# 4. 验证新密钥
python scripts/verify_encryption.py --key-id NEW_KEY_ID

# 5. 停用旧密钥 (保留90天)
aws kms disable-key --key-id OLD_KEY_ID
```

### 6.2 mTLS双向认证

#### 证书生成

```bash
# 1. 生成CA证书
openssl genrsa -out ca.key 4096
openssl req -new -x509 -days 3650 -key ca.key -out ca.crt \
  -subj "/C=US/O=HashInsight/CN=HashInsight Root CA"

# 2. 生成服务器证书
openssl genrsa -out server.key 4096
openssl req -new -key server.key -out server.csr \
  -subj "/C=US/O=HashInsight/CN=*.hashinsight.net"
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt

# 3. 生成客户端证书
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr \
  -subj "/C=US/O=HashInsight/CN=client.hashinsight.net"
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out client.crt
```

#### mTLS配置

```bash
# 环境变量配置
export MTLS_ENABLED=true
export MTLS_CA_CERT_PATH=/app/certs/ca.crt
export MTLS_SERVER_CERT_PATH=/app/certs/server.crt
export MTLS_SERVER_KEY_PATH=/app/certs/server.key
export MTLS_VERIFY_CLIENT=true
export MTLS_ALLOWED_DN_PATTERNS="CN=*.hashinsight.net,O=HashInsight,C=US"
```

#### 使用mTLS认证

```python
from common.mtls_auth import require_mtls

@app.route('/api/admin/sensitive')
@require_mtls()
def sensitive_endpoint():
    # 仅允许持有有效客户端证书的请求
    client_dn = g.client_cert_subject
    return jsonify({"message": f"Authenticated as {client_dn}"})
```

### 6.3 API密钥管理

#### 密钥格式

HashInsight API密钥格式: `hsi_{env}_key_{random}`

示例:
- 生产: `hsi_prod_key_a1b2c3d4e5f6g7h8`
- 开发: `hsi_dev_key_x9y8z7w6v5u4t3s2`

#### 创建API密钥

```bash
# 使用管理工具创建
python scripts/create_api_key.py \
  --user-id 123 \
  --permissions "miners:read,miners:write" \
  --expires-in 90

# 输出
✅ API密钥已创建
密钥: hsi_prod_key_a1b2c3d4e5f6g7h8
用户ID: 123
权限: miners:read,miners:write
过期时间: 2025-12-31T23:59:59Z
⚠️  请妥善保管此密钥，它不会再次显示
```

#### API密钥轮换

```bash
# 1. 创建新密钥
new_key=$(python scripts/create_api_key.py --user-id 123 --copy-from old_key_id)

# 2. 更新客户端配置 (双密钥并存期7天)
# 新旧密钥同时有效

# 3. 验证新密钥
curl -H "Authorization: Bearer $new_key" http://localhost:5000/api/miners

# 4. 吊销旧密钥
python scripts/revoke_api_key.py --key-id old_key_id
```

### 6.4 WireGuard企业专网

#### Hub服务器部署

```bash
# 1. 运行Hub安装脚本
sudo bash wireguard/hub_setup.sh

# 2. 配置防火墙
sudo ufw allow 51820/udp
sudo ufw enable

# 3. 启动WireGuard
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0

# 4. 查看状态
sudo wg show
```

#### 站点网关配置

```bash
# 1. 生成站点密钥
cd wireguard/site-gateway
python key_manager.py --generate-keys --site beijing-dc1

# 2. 添加到Hub配置
sudo nano /etc/wireguard/wg0.conf

# 添加Peer配置
[Peer]
PublicKey = site_public_key
AllowedIPs = 10.8.1.0/24
Endpoint = beijing-gateway.hashinsight.net:51820

# 3. 重载配置
sudo wg-quick down wg0
sudo wg-quick up wg0
```

### 6.5 审计日志

HashInsight 记录所有关键操作到审计日志 (`audit/audit_logger.py`)：

#### 审计事件类型

- ✅ 认证 (登录/登出/失败)
- ✅ 数据访问 (CRUD操作)
- ✅ 配置变更
- ✅ 权限变更
- ✅ 加密操作
- ✅ API密钥管理
- ✅ 可疑活动

#### 审计日志格式

```json
{
  "timestamp": "2025-10-03T12:00:00.000Z",
  "event_id": "a1b2c3d4e5f6g7h8",
  "level": "INFO",
  "category": "authentication",
  "action": "login",
  "user_id": "123",
  "user_email": "user@example.com",
  "user_role": "admin",
  "ip_address": "192.168.1.100",
  "status": "success",
  "details": {
    "login_method": "password",
    "two_factor": true
  }
}
```

#### 查询审计日志

```bash
# 查看最近100条审计日志
tail -100 logs/audit.jsonl

# 查询特定用户的操作
jq 'select(.user_email == "admin@hashinsight.net")' logs/audit.jsonl

# 查询失败的登录尝试
jq 'select(.action == "login_failed")' logs/audit.jsonl

# 查询过去24小时的安全事件
jq --arg date "$(date -d '24 hours ago' -Iseconds)" \
  'select(.timestamp > $date and .level == "SECURITY")' \
  logs/audit.jsonl
```

### 6.6 合规要求

HashInsight 遵循以下合规标准：

#### SOC 2 Type II

- ✅ 访问控制
- ✅ 加密传输 (TLS 1.3)
- ✅ 加密存储 (AES-256)
- ✅ 审计日志 (不可篡改)
- ✅ 变更管理
- ✅ 灾难恢复

#### PCI DSS (如处理支付)

- ✅ 敏感数据脱敏
- ✅ 密钥管理 (KMS)
- ✅ 网络隔离 (WireGuard)
- ✅ 定期渗透测试

#### GDPR

- ✅ 数据最小化
- ✅ 用户数据导出
- ✅ 数据删除 (被遗忘权)
- ✅ 数据处理记录

### 6.7 安全检查清单

- [ ] 所有密钥存储在KMS中 (不在代码/配置文件)
- [ ] 启用mTLS (生产环境)
- [ ] API密钥定期轮换 (90天)
- [ ] SSL/TLS证书有效且未过期
- [ ] 审计日志正常写入
- [ ] 无敏感信息泄露到日志
- [ ] 数据库连接加密 (SSL)
- [ ] 会话密钥强度 ≥256位
- [ ] 定期安全扫描 (每季度)
- [ ] 渗透测试报告 (每年)

---

## 第7章：故障排查手册

### 7.1 应用无法启动

#### 症状
```
$ gunicorn main:app
[ERROR] Application failed to start
```

#### 诊断步骤

**1. 检查端口占用**
```bash
# 查看端口5000占用情况
lsof -i :5000

# 如果被占用，杀死进程
kill -9 $(lsof -t -i:5000)
```

**2. 检查环境变量**
```bash
# 验证必需变量
python3 << 'EOF'
import os
required = ['DATABASE_URL', 'SESSION_SECRET', 'ENCRYPTION_PASSWORD']
for var in required:
    value = os.getenv(var)
    if not value:
        print(f"❌ Missing: {var}")
    else:
        print(f"✅ {var}: {'*' * 8} (set)")
EOF
```

**3. 检查数据库连接**
```bash
# 测试PostgreSQL连接
psql $DATABASE_URL -c "SELECT version();"

# 如果失败，检查Neon端点状态
# 访问 https://console.neon.tech
```

**4. 检查Python依赖**
```bash
# 验证关键库
python3 -c "
import flask
import gunicorn
import psycopg2
import sqlalchemy
print('✅ All dependencies OK')
"
```

**5. 查看详细错误**
```bash
# 启用调试模式
export FLASK_DEBUG=1
python3 main.py

# 查看完整堆栈跟踪
```

#### 常见错误及解决方案

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| `ModuleNotFoundError: No module named 'flask'` | 依赖未安装 | `pip install -r requirements.txt` |
| `OperationalError: could not connect to server` | 数据库连接失败 | 检查 DATABASE_URL，验证Neon端点 |
| `ValueError: SECRET_KEY must be set` | SESSION_SECRET未设置 | `export SESSION_SECRET=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')` |
| `Address already in use` | 端口被占用 | `kill -9 $(lsof -t -i:5000)` |

### 7.2 数据库连接失败

#### 症状
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
could not connect to server: Connection timed out
```

#### 诊断步骤

**1. 验证连接字符串**
```bash
# 解析DATABASE_URL
python3 << 'EOF'
import os
from urllib.parse import urlparse
url = os.getenv('DATABASE_URL')
parsed = urlparse(url)
print(f"Host: {parsed.hostname}")
print(f"Port: {parsed.port}")
print(f"Database: {parsed.path[1:]}")
print(f"User: {parsed.username}")
EOF
```

**2. 测试网络连通性**
```bash
# 提取host和port
export DB_HOST=$(python3 -c "from urllib.parse import urlparse; import os; print(urlparse(os.getenv('DATABASE_URL')).hostname)")
export DB_PORT=$(python3 -c "from urllib.parse import urlparse; import os; print(urlparse(os.getenv('DATABASE_URL')).port or 5432)")

# 测试TCP连接
nc -zv $DB_HOST $DB_PORT
```

**3. 检查连接池**
```python
# 连接池配置 (config.py)
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,           # 默认10个连接
    'pool_recycle': 300,       # 5分钟回收
    'pool_pre_ping': True,     # 使用前测试连接
    'pool_timeout': 30,        # 30秒超时
    'max_overflow': 20,        # 最多溢出20个
    'connect_args': {
        'connect_timeout': 15  # 15秒连接超时
    }
}
```

**4. 检查Neon端点状态**
```bash
# 访问Neon控制台
# https://console.neon.tech/app/projects

# 检查端点状态:
# - Active (绿色) - 正常
# - Idle (黄色) - 需要唤醒
# - Suspended (灰色) - 已暂停
```

**5. 启用连接重试**
```python
# 在app.py中添加重试逻辑
from sqlalchemy import event, exc
from sqlalchemy.pool import Pool

@event.listens_for(Pool, "connect")
def receive_connect(dbapi_conn, connection_record):
    connection_record.info['pid'] = os.getpid()

@event.listens_for(Pool, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    pid = os.getpid()
    if connection_record.info['pid'] != pid:
        connection_record.connection = connection_proxy.connection = None
        raise exc.DisconnectionError(
            "Connection record belongs to pid %s, "
            "attempting to check out in pid %s" %
            (connection_record.info['pid'], pid)
        )
```

### 7.3 缓存问题

#### 症状
- 响应时间显著增加
- 缓存命中率低于50%
- Redis连接错误

#### 诊断步骤

**1. 检查Redis连接**
```bash
# 测试Redis
redis-cli ping
# 预期: PONG

# 检查Redis内存
redis-cli info memory

# 检查键数量
redis-cli dbsize
```

**2. 查看缓存命中率**
```python
# 通过API查询
curl http://localhost:5000/api/cache/stats

# 预期响应
{
  "cache_type": "redis",
  "hit_rate": 75.5,
  "total_requests": 10000,
  "hits": 7550,
  "misses": 2450
}
```

**3. 缓存回退机制**
```python
# cache_manager.py 自动回退
if redis_available:
    cache_backend = RedisCache()
else:
    logger.warning("Redis unavailable, falling back to memory cache")
    cache_backend = MemoryCache()
```

**4. 清理缓存**
```bash
# 清理所有缓存
redis-cli FLUSHDB

# 清理特定前缀
redis-cli --scan --pattern 'hashinsight:*' | xargs redis-cli DEL
```

### 7.4 性能下降

#### 症状
- API响应时间 p95 > 250ms
- 数据库查询缓慢
- CPU/内存使用率高

#### 诊断步骤

**1. 检查Request Coalescing状态**
```bash
# 查看请求合并统计
curl http://localhost:5000/api/performance/coalescing-stats

# 预期响应
{
  "enabled": true,
  "performance_improvement": "9.8x",
  "deduplicated_requests": 5432,
  "total_requests": 53210
}
```

**2. 分析慢查询**
```sql
-- 启用慢查询日志 (PostgreSQL)
ALTER DATABASE hashinsight_db SET log_min_duration_statement = 1000;

-- 查询慢查询
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
WHERE mean_time > 1000
ORDER BY mean_time DESC
LIMIT 10;
```

**3. 检查数据库索引**
```bash
# 运行索引优化
python database/optimize_indexes.py --analyze

# 查看缺失索引
python database/optimize_indexes.py --suggest
```

**4. 监控系统资源**
```bash
# CPU使用率
top -b -n 1 | grep gunicorn

# 内存使用
ps aux | grep gunicorn | awk '{sum+=$6} END {print sum/1024 " MB"}'

# 数据库连接数
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity WHERE datname = 'hashinsight_db';"
```

**5. 启用性能分析**
```python
# 添加到需要分析的路由
from werkzeug.middleware.profiler import ProfilerMiddleware

app.wsgi_app = ProfilerMiddleware(
    app.wsgi_app,
    restrictions=[10],
    profile_dir='./profiles'
)
```

### 7.5 区块链集成错误

#### 症状
```
ERROR:blockchain_integration: 加密配置错误: ENCRYPTION_PASSWORD环境变量必须设置
ERROR:sla_nft_routes: 获取SLA状态失败
```

#### 诊断步骤

**1. 检查ENCRYPTION_PASSWORD**
```bash
# 验证环境变量
echo $ENCRYPTION_PASSWORD

# 如果未设置
export ENCRYPTION_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
```

**2. 检查区块链配置**
```bash
# 验证区块链环境变量
python3 << 'EOF'
import os
config = {
    'BLOCKCHAIN_ENABLED': os.getenv('BLOCKCHAIN_ENABLED'),
    'BLOCKCHAIN_PRIVATE_KEY': '***' if os.getenv('BLOCKCHAIN_PRIVATE_KEY') else None,
    'BLOCKCHAIN_NETWORK': os.getenv('BLOCKCHAIN_NETWORK', 'base-sepolia'),
    'BASE_RPC_URL': os.getenv('BASE_RPC_URL', 'https://sepolia.base.org')
}
for k, v in config.items():
    status = '✅' if v else '❌'
    print(f"{status} {k}: {v}")
EOF
```

**3. 测试Web3连接**
```python
python3 << 'EOF'
from web3 import Web3
import os

rpc_url = os.getenv('BASE_RPC_URL', 'https://sepolia.base.org')
w3 = Web3(Web3.HTTPProvider(rpc_url))

if w3.is_connected():
    print(f"✅ Web3 connected to {rpc_url}")
    print(f"Block number: {w3.eth.block_number}")
else:
    print(f"❌ Web3 connection failed")
EOF
```

**4. 验证私钥格式**
```bash
# 私钥应以0x开头，64个十六进制字符
python3 << 'EOF'
import os
import re

private_key = os.getenv('BLOCKCHAIN_PRIVATE_KEY', '')
if re.match(r'^0x[0-9a-fA-F]{64}$', private_key):
    print("✅ Private key format valid")
else:
    print("❌ Invalid private key format")
    print("Expected: 0x + 64 hex characters")
EOF
```

### 7.6 日志位置

| 日志类型 | 路径 | 格式 |
|----------|------|------|
| 应用日志 | 标准输出 (stdout) | 文本 |
| 审计日志 | `logs/audit.jsonl` | JSON Lines |
| 错误日志 | 标准错误 (stderr) | 文本 |
| Gunicorn日志 | `/var/log/gunicorn/` | 文本 |
| PostgreSQL日志 | Neon Console | 文本 |
| Workflow日志 | `/tmp/logs/` | 文本 |

#### 查看日志

```bash
# 实时查看应用日志
tail -f /var/log/hashinsight/app.log

# 查看错误日志
grep ERROR /var/log/hashinsight/app.log | tail -50

# 查看审计日志
tail -f logs/audit.jsonl | jq '.'

# 查看Gunicorn访问日志
tail -f /var/log/gunicorn/access.log
```

---

## 第8章：日常运维操作

### 8.1 数据库维护

#### 8.1.1 索引优化

```bash
# 自动优化索引
python database/optimize_indexes.py --auto

# 分析并建议索引
python database/optimize_indexes.py --analyze --suggest

# 输出示例:
# ✅ 现有索引: 45个
# 🔍 扫描慢查询...
# 💡 建议创建索引:
#   - CREATE INDEX idx_miners_user_id ON miners(user_id)
#   - CREATE INDEX idx_market_data_timestamp ON market_analytics(created_at DESC)
```

#### 8.1.2 连接池监控

```sql
-- 查看当前连接
SELECT 
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start
FROM pg_stat_activity
WHERE datname = 'hashinsight_db'
ORDER BY query_start;

-- 杀死空闲连接
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'hashinsight_db'
  AND state = 'idle'
  AND state_change < NOW() - INTERVAL '30 minutes';
```

#### 8.1.3 慢查询分析

```sql
-- 启用pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 查看Top 10慢查询
SELECT 
    substring(query, 1, 100) AS short_query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
ORDER BY mean_time DESC
LIMIT 10;

-- 重置统计
SELECT pg_stat_statements_reset();
```

#### 8.1.4 数据库清理

```bash
# 清理旧数据 (保留90天)
python scripts/cleanup_old_data.py --days 90

# 清理示例:
# ✅ 删除90天前的market_analytics: 12,543条
# ✅ 删除90天前的audit日志: 45,123条
# ✅ 清理完成，释放空间: 2.3 GB
```

### 8.2 缓存管理

#### 8.2.1 Redis缓存清理

```bash
# 清理所有HashInsight缓存
redis-cli --scan --pattern 'hashinsight:*' | xargs redis-cli DEL

# 清理特定模块缓存
redis-cli --scan --pattern 'hashinsight:miners:*' | xargs redis-cli DEL

# 清理过期键 (Redis自动，手动触发)
redis-cli --scan --pattern 'hashinsight:*' | while read key; do
    redis-cli TTL "$key"
done
```

#### 8.2.2 内存缓存监控

```python
# 通过API查询内存缓存状态
curl http://localhost:5000/api/cache/memory-stats

# 响应
{
  "cache_type": "memory",
  "size_mb": 124.5,
  "entries": 5432,
  "hit_rate": 82.3,
  "evictions": 234
}
```

#### 8.2.3 Request Coalescer状态

```bash
# 查看请求合并统计
curl http://localhost:5000/api/performance/coalescing-stats | jq

# 手动清理合并缓存
curl -X POST http://localhost:5000/api/performance/clear-coalescing-cache
```

### 8.3 批量任务

#### 8.3.1 批量导入矿机

```bash
# 准备CSV文件 (最多5000台)
# 格式: name,model,hashrate_th,power_w,efficiency

# 执行批量导入
python batch/batch_import_manager.py \
  --file miners_upload_5000.csv \
  --user-id 123 \
  --validate

# 输出:
# ✅ 文件验证通过
# 📊 记录数: 5000
# ⚙️  处理中...
# [████████████████████████████████] 100%
# ✅ 导入完成: 5000台矿机 (耗时: 45.2s)
```

#### 8.3.2 数据收集任务

HashInsight 每15分钟自动收集市场数据：

```bash
# 手动触发数据收集
python modules/analytics/engines/analytics_engine.py --collect-now

# 查看收集状态
curl http://localhost:5000/api/analytics/collection-status

# 响应
{
  "last_collection": "2025-10-03T12:15:00Z",
  "next_collection": "2025-10-03T12:30:00Z",
  "status": "healthy",
  "data_points_today": 8
}
```

#### 8.3.3 数据收集调度

```python
# 配置数据收集频率 (config.py)
ANALYTICS_COLLECTION_INTERVAL = 15  # 分钟
ANALYTICS_MAX_DATA_POINTS_PER_DAY = 10  # 每日限制

# 启用/禁用后台服务（默认：禁用，即 0）
export ENABLE_BACKGROUND_SERVICES=1  # 启用后台数据采集
export ENABLE_BACKGROUND_SERVICES=0  # 禁用后台数据采集（默认行为）
```

### 8.4 用户管理

#### 8.4.1 创建用户

```bash
# 通过管理界面创建
# 访问: http://localhost:5000/admin/users/create

# 通过命令行创建
python scripts/create_user.py \
  --email admin@hashinsight.net \
  --username admin \
  --role owner \
  --password-prompt

# 输出:
# 请输入密码: ********
# ✅ 用户已创建
# ID: 123
# Email: admin@hashinsight.net
# Role: owner
```

#### 8.4.2 角色分配

| 角色 | 权限 | 说明 |
|------|------|------|
| `owner` | 全部权限 | 系统所有者 |
| `admin` | 管理权限 | 系统管理员 |
| `broker` | 经纪人权限 | 客户管理、订单 |
| `client` | 客户权限 | 查看自己的数据 |

```bash
# 修改用户角色
python scripts/change_user_role.py \
  --user-id 123 \
  --new-role admin

# 批量导入用户
python scripts/bulk_import_users.py --file users.csv
```

#### 8.4.3 权限管理

```python
# 检查用户权限
from decorators import has_permission

@app.route('/api/miners/delete/<int:miner_id>', methods=['DELETE'])
@login_required
@requires_permission('miners:delete')
def delete_miner(miner_id):
    # 仅允许有miners:delete权限的用户
    pass
```

### 8.5 数据清理

#### 8.5.1 每日数据点限制

为控制存储成本，HashInsight限制每日数据点数量：

```python
# config.py
ANALYTICS_MAX_DATA_POINTS_PER_DAY = 10  # 每日最多10个数据点
```

#### 8.5.2 历史数据归档

```bash
# 归档90天前的数据到冷存储
python scripts/archive_historical_data.py --days 90 --storage s3

# 输出:
# 📦 扫描需归档数据...
# 📊 market_analytics: 123,456条
# 📊 calculation_history: 45,678条
# ⬆️  上传到 s3://hashinsight-archive/...
# 🗑️  从主数据库删除
# ✅ 归档完成: 释放 5.2 GB
```

#### 8.5.3 审计日志归档

```bash
# 归档6个月前的审计日志
python scripts/archive_audit_logs.py --months 6

# 日志轮转 (自动)
# audit/audit_logger.py 自动轮转100MB日志文件
```

---

## 第9章：性能优化指南

### 9.1 Request Coalescing

HashInsight 使用 Request Coalescing 实现**9.8倍性能提升**：

#### 原理

```
传统模式:
Request 1 → API Call → Response 1
Request 2 → API Call → Response 2
Request 3 → API Call → Response 3
(3个API调用)

Request Coalescing:
Request 1 ┐
Request 2 ├→ Single API Call → Response → Shared Result
Request 3 ┘
(1个API调用，节省67%请求)
```

#### 配置

```python
# cache_manager.py
REQUEST_COALESCING_ENABLED = True
COALESCING_TIMEOUT = 100  # 100ms内的重复请求合并
COALESCING_MAX_WAIT = 500  # 最多等待500ms
```

#### 监控

```bash
# 查看Request Coalescing统计
curl http://localhost:5000/api/performance/coalescing-stats | jq

# 响应
{
  "enabled": true,
  "total_requests": 98234,
  "deduplicated_requests": 85432,
  "api_calls_saved": 85432,
  "performance_improvement": "9.8x",
  "average_wait_time_ms": 45
}
```

### 9.2 数据库优化

#### 9.2.1 索引策略

```sql
-- 高频查询字段索引
CREATE INDEX idx_miners_user_id ON miners(user_id);
CREATE INDEX idx_market_data_timestamp ON market_analytics(created_at DESC);
CREATE INDEX idx_calculations_user_created ON calculations(user_id, created_at);

-- 复合索引 (常同时查询的字段)
CREATE INDEX idx_miners_user_model ON miners(user_id, model);

-- 部分索引 (仅索引活跃数据)
CREATE INDEX idx_active_miners ON miners(user_id) WHERE status = 'active';
```

#### 9.2.2 查询优化

**使用EXPLAIN分析查询**
```sql
EXPLAIN ANALYZE
SELECT m.*, u.username
FROM miners m
JOIN users u ON m.user_id = u.id
WHERE m.status = 'active'
ORDER BY m.created_at DESC
LIMIT 100;

-- 查看执行计划，优化慢查询
```

**避免N+1查询**
```python
# ❌ 不好 - N+1查询
miners = Miner.query.filter_by(user_id=user_id).all()
for miner in miners:
    print(miner.user.username)  # 每次循环一次查询

# ✅ 好 - 使用JOIN
miners = Miner.query.join(User).filter(Miner.user_id == user_id).all()
for miner in miners:
    print(miner.user.username)  # 一次查询
```

#### 9.2.3 连接池调优

```python
# config.py
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,           # 根据并发量调整 (worker数 × 2)
    'pool_recycle': 300,       # 5分钟回收连接
    'pool_pre_ping': True,     # 使用前测试连接 (Neon必需)
    'pool_timeout': 30,        # 30秒超时
    'max_overflow': 20,        # 最多溢出20个
    'connect_args': {
        'connect_timeout': 15,         # 连接超时
        'application_name': 'hashinsight',  # 便于监控
        'options': '-c statement_timeout=30000'  # 查询超时30秒
    }
}
```

### 9.3 缓存策略

#### 9.3.1 多级缓存

```python
# 三级缓存架构
L1: 内存缓存 (最快，容量小)
    ↓ miss
L2: Redis缓存 (快，容量中)
    ↓ miss
L3: 数据库 (慢，容量大)

# 实现
@cache_manager.cached(ttl=300, level='L1')  # 5分钟
def get_user_profile(user_id):
    return db.session.query(User).get(user_id)

@cache_manager.cached(ttl=3600, level='L2')  # 1小时
def get_market_data():
    return fetch_from_api()
```

#### 9.3.2 TTL配置

| 数据类型 | TTL | 理由 |
|----------|-----|------|
| 用户信息 | 5分钟 | 可能变更 |
| 市场数据 | 5分钟 | 实时性要求 |
| 矿机列表 | 1小时 | 变更频率低 |
| 统计数据 | 10分钟 | 计算密集 |
| 静态内容 | 24小时 | 几乎不变 |

#### 9.3.3 缓存预热

```bash
# 启动时预热关键缓存
python scripts/warmup_cache.py

# 脚本内容
# 1. 加载热门用户数据
# 2. 加载当前市场数据
# 3. 预计算统计数据
# 4. 加载配置数据

# 输出:
# ✅ 预热用户缓存: 1,234个
# ✅ 预热市场数据: 当前价格+算力
# ✅ 预热统计数据: 10个仪表板
# ⏱️  耗时: 12.3s
```

### 9.4 批量处理优化

#### 9.4.1 向量化计算

```python
# ❌ 不好 - 逐条计算
for miner in miners:
    daily_revenue = calculate_revenue(
        miner.hashrate, 
        btc_price, 
        network_difficulty
    )
# 耗时: 5000台 × 10ms = 50秒

# ✅ 好 - 向量化计算
import numpy as np

hashrates = np.array([m.hashrate for m in miners])
revenues = calculate_revenue_vectorized(
    hashrates, 
    btc_price, 
    network_difficulty
)
# 耗时: ~500ms (100倍提升)
```

#### 9.4.2 并发处理

```python
from concurrent.futures import ThreadPoolExecutor

# 并发处理批量任务
def process_miner_batch(miners, batch_size=100):
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for i in range(0, len(miners), batch_size):
            batch = miners[i:i+batch_size]
            future = executor.submit(process_batch, batch)
            futures.append(future)
        
        results = [f.result() for f in futures]
    return results
```

#### 9.4.3 内存优化

```python
# 批量插入 (避免ORM开销)
from sqlalchemy import insert

# ❌ 不好 - 逐条插入
for data in large_dataset:
    db.session.add(Model(**data))
    db.session.commit()  # 每次提交

# ✅ 好 - 批量插入
db.session.bulk_insert_mappings(Model, large_dataset)
db.session.commit()  # 一次提交

# ✅ 更好 - 使用bulk insert
stmt = insert(Model).values(large_dataset)
db.session.execute(stmt)
db.session.commit()
```

### 9.5 性能监控

```bash
# 定期运行性能基准测试
python scripts/performance_benchmark.py

# 输出:
# 📊 API响应时间:
#   - /api/miners: p50=45ms, p95=120ms, p99=250ms ✅
#   - /api/dashboard: p50=80ms, p95=200ms, p99=400ms ✅
# 📊 数据库查询:
#   - 平均查询时间: 15ms ✅
#   - 慢查询 (>1s): 0个 ✅
# 📊 缓存性能:
#   - 命中率: 78.5% ✅
#   - Request Coalescing: 9.8x提升 ✅
```

---

## 第10章：应急响应手册

### 10.1 On-Call值班制度

#### 值班排班

| 时段 | 主值班 | 备份值班 | 升级联系人 |
|------|--------|----------|------------|
| 工作日 09:00-18:00 | DevOps工程师 | 后端工程师 | 技术总监 |
| 工作日 18:00-09:00 | 轮值工程师 | 备份工程师 | On-Call Manager |
| 周末/节假日 | 轮值工程师 | 备份工程师 | On-Call Manager |

#### 值班工具

- 📱 **PagerDuty**: 告警通知
- 💬 **Slack**: #incident-response频道
- 📊 **Grafana**: 实时监控
- 📝 **Incident.io**: 事故管理

### 10.2 事故分级

| 级别 | 影响 | 响应时间 | 升级时间 | 示例 |
|------|------|----------|----------|------|
| **P0** | 完全服务中断 | 15分钟 | 30分钟 | 数据库宕机、应用无法访问 |
| **P1** | 核心功能降级 | 30分钟 | 1小时 | API延迟>5s、错误率>5% |
| **P2** | 部分功能故障 | 2小时 | 4小时 | 单个功能无法使用 |
| **P3** | 性能下降 | 4小时 | 8小时 | 响应变慢但可用 |
| **P4** | 非紧急问题 | 1工作日 | 2工作日 | UI显示问题、小bug |

### 10.3 响应流程

#### P0/P1 紧急事故流程

```
1. [0-5分钟] 告警触发
   ├→ PagerDuty通知主值班
   ├→ 自动创建Slack事故频道
   └→ 自动通知备份值班

2. [5-15分钟] 初步响应
   ├→ 确认事故 (ACK告警)
   ├→ 发布初步通告
   ├→ 开始故障排查
   └→ 记录时间线

3. [15-30分钟] 应急处置
   ├→ 实施临时缓解措施
   ├→ 评估影响范围
   ├→ 决定是否升级
   └→ 更新事故状态

4. [30分钟+] 完全解决
   ├→ 实施永久修复
   ├→ 验证服务恢复
   ├→ 发布恢复通告
   └→ 开始事后分析
```

### 10.4 常见紧急场景

#### 场景1: 数据库连接池耗尽

**症状**
```
sqlalchemy.exc.TimeoutError: QueuePool limit of size 10 overflow 20 reached
```

**应急响应**
```bash
# 1. 立即杀死长时间空闲连接
psql $DATABASE_URL -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle' 
  AND state_change < NOW() - INTERVAL '10 minutes';
"

# 2. 增加连接池限制 (临时)
export SQLALCHEMY_POOL_SIZE=20
export SQLALCHEMY_MAX_OVERFLOW=40

# 3. 重启应用
systemctl restart hashinsight

# 4. 监控连接数
watch -n 5 "psql $DATABASE_URL -c 'SELECT count(*) FROM pg_stat_activity;'"
```

#### 场景2: 内存泄漏导致OOM

**症状**
```
MemoryError: Unable to allocate array
Killed (OOM)
```

**应急响应**
```bash
# 1. 立即重启受影响的worker
kill -HUP $(cat /var/run/gunicorn.pid)

# 2. 清理缓存释放内存
redis-cli FLUSHDB

# 3. 限制worker数量 (临时)
gunicorn --workers 2 --max-requests 500 main:app

# 4. 监控内存使用
watch -n 5 'free -h'
```

#### 场景3: 恶意流量攻击

**症状**
- 异常高的请求量
- 大量401/403错误
- 特定IP段的可疑请求

**应急响应**
```bash
# 1. 启用速率限制
export RATE_LIMIT_ENABLED=true
export RATE_LIMIT_REQUESTS_PER_MINUTE=10

# 2. 封禁恶意IP (通过防火墙)
ufw deny from 192.168.1.0/24

# 3. 启用Cloudflare防护 (如使用)
# 访问Cloudflare Dashboard -> Security -> DDoS

# 4. 分析攻击模式
tail -1000 /var/log/gunicorn/access.log | \
  awk '{print $1}' | sort | uniq -c | sort -rn | head -20
```

### 10.5 回滚流程

#### 代码回滚

```bash
# 1. 确定回滚版本
git log --oneline -10

# 2. 回滚到上一个稳定版本
git revert HEAD --no-edit
# 或
git checkout v1.9.5

# 3. 重新部署
git push origin main

# 4. 验证回滚成功
curl http://localhost:5000/health | jq '.version'

# 5. 通知团队
# Slack: "已回滚到v1.9.5，服务恢复正常"
```

#### 数据库回滚

```bash
# ⚠️ 警告: 数据库回滚风险高，必须先备份!

# 1. 创建当前状态备份
python backup/backup_manager.py --type emergency

# 2. 恢复到回滚点
psql $DATABASE_URL < /tmp/backups/hashinsight_backup_20251003_020000.sql

# 3. 验证数据完整性
python scripts/verify_database_integrity.py

# 4. 重启应用
systemctl restart hashinsight
```

### 10.6 沟通模板

#### 初始事故通告

```
📢 [P0 事故] HashInsight 服务中断

时间: 2025-10-03 14:23 UTC
影响: 所有用户无法访问主应用
状态: 正在调查

我们已确认服务中断问题，团队正在紧急排查。
预计在30分钟内提供更新。

事故频道: #incident-2025-10-03-db-outage
值班工程师: @john.doe
```

#### 进度更新

```
🔄 [更新] HashInsight 事故进展

时间: 2025-10-03 14:45 UTC
根本原因: 数据库连接池耗尽
缓解措施: 已重启数据库连接池
当前状态: 服务部分恢复，监控中

下次更新: 15:00 UTC 或有重大进展时
```

#### 恢复通告

```
✅ [已解决] HashInsight 服务已恢复

时间: 2025-10-03 15:12 UTC
持续时间: 49分钟
根本原因: PostgreSQL连接池配置不当
解决方案: 已增加连接池限制并优化慢查询

所有服务现已完全恢复正常。
事后分析报告将在24小时内发布。

感谢您的耐心等待。
```

### 10.7 事后分析 (Postmortem)

#### 模板

```markdown
# HashInsight 事故报告 - 2025-10-03 数据库中断

## 概要
- **事故编号**: INC-2025-1003-001
- **严重程度**: P0
- **发生时间**: 2025-10-03 14:23 UTC
- **恢复时间**: 2025-10-03 15:12 UTC
- **持续时间**: 49分钟
- **影响用户**: 100% (所有用户)

## 时间线
- 14:23 - Prometheus告警: 数据库连接失败
- 14:25 - 值班工程师确认事故
- 14:30 - 发现连接池耗尽
- 14:35 - 实施临时缓解 (杀死空闲连接)
- 14:45 - 服务部分恢复
- 15:00 - 实施永久修复 (增加连接池)
- 15:12 - 服务完全恢复

## 根本原因
PostgreSQL连接池大小配置为10，但实际并发需求达到30+，
导致连接等待超时。

## 解决方案
1. 临时: 杀死空闲连接，释放连接池
2. 永久: 增加连接池大小至20，溢出至40
3. 优化: 识别并优化3个慢查询

## 预防措施
- [ ] 设置连接池告警 (使用率>80%)
- [ ] 定期审查慢查询
- [ ] 增加容量规划流程
- [ ] 添加连接池监控仪表板

## 经验教训
✅ 快速响应和沟通良好
❌ 缺少连接池监控
❌ 容量规划不足
```

---

## 附录

### 附录A: 常用命令速查表

#### 应用管理

```bash
# 启动应用
gunicorn --bind 0.0.0.0:5000 --workers 4 main:app

# 优雅重启
kill -HUP $(cat /var/run/gunicorn.pid)

# 停止应用
kill -TERM $(cat /var/run/gunicorn.pid)

# 查看进程
ps aux | grep gunicorn

# 查看日志
tail -f /var/log/hashinsight/app.log
```

#### 数据库

```bash
# 连接数据库
psql $DATABASE_URL

# 查看表
\dt

# 查看连接数
SELECT count(*) FROM pg_stat_activity;

# 备份数据库
pg_dump $DATABASE_URL > backup.sql

# 恢复数据库
psql $DATABASE_URL < backup.sql
```

#### 缓存

```bash
# Redis连接
redis-cli

# 查看所有键
redis-cli KEYS 'hashinsight:*'

# 清空缓存
redis-cli FLUSHDB

# 查看内存使用
redis-cli INFO memory
```

#### 监控

```bash
# 查看健康状态
curl http://localhost:5000/health | jq

# 查看Prometheus指标
curl http://localhost:9090/metrics

# 查看SLO状态
curl http://localhost:5000/api/slo/status | jq
```

### 附录B: 配置文件示例

#### .env 示例

```bash
# 必需配置
DATABASE_URL=postgresql://user:pass@host:5432/hashinsight_db
SESSION_SECRET=your-secret-key-min-32-chars
ENCRYPTION_PASSWORD=encryption-key-min-32-chars

# 区块链配置
BLOCKCHAIN_ENABLED=true
BLOCKCHAIN_PRIVATE_KEY=0x1234567890abcdef...
BLOCKCHAIN_NETWORK=base-sepolia
BASE_RPC_URL=https://sepolia.base.org

# 备份配置
BACKUP_DIR=/var/backups/hashinsight
BACKUP_ENCRYPTION_KEY=backup-encryption-key
BACKUP_RETENTION_DAYS=30
BACKUP_STORAGE_TYPE=s3
BACKUP_STORAGE_BUCKET=hashinsight-backups

# KMS配置 (AWS)
AWS_KMS_KEY_ID=arn:aws:kms:us-east-1:123456789:key/xxxxx
AWS_KMS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxx

# 监控配置
ENABLE_BACKGROUND_SERVICES=0  # 默认禁用；设为 1 启用后台数据采集
PROMETHEUS_PORT=9090
SLO_MEASUREMENT_WINDOW=30

# API配置
COINWARZ_API_KEY=your-coinwarz-api-key
COINGECKO_API_KEY=your-coingecko-api-key
```

#### systemd服务文件示例

```ini
# /etc/systemd/system/hashinsight.service

[Unit]
Description=HashInsight Platform
After=network.target postgresql.service

[Service]
Type=notify
User=hashinsight
Group=hashinsight
WorkingDirectory=/opt/hashinsight
EnvironmentFile=/opt/hashinsight/.env

ExecStart=/opt/hashinsight/venv/bin/gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --threads 2 \
  --worker-class gthread \
  --timeout 120 \
  --max-requests 1000 \
  --access-logfile /var/log/hashinsight/access.log \
  --error-logfile /var/log/hashinsight/error.log \
  --pid /var/run/gunicorn.pid \
  main:app

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30

Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 附录C: 监控指标参考

#### Prometheus指标列表

| 指标名称 | 类型 | 说明 |
|----------|------|------|
| `hashinsight_requests_total` | Counter | 总请求数 |
| `hashinsight_request_latency_seconds` | Histogram | 请求延迟 |
| `hashinsight_error_rate` | Gauge | 错误率 |
| `hashinsight_cache_hit_rate` | Gauge | 缓存命中率 |
| `hashinsight_db_query_duration_seconds` | Histogram | 数据库查询时间 |
| `hashinsight_db_connection_pool_size` | Gauge | 数据库连接池大小 |
| `hashinsight_db_connection_pool_active` | Gauge | 活跃连接数 |
| `hashinsight_slo_compliance` | Gauge | SLO合规性 |
| `hashinsight_slo_error_budget_remaining` | Gauge | 错误预算剩余 |
| `hashinsight_circuit_breaker_state` | Gauge | 熔断器状态 |

#### SLO阈值

| SLO类型 | 目标 | 警告阈值 | 严重阈值 |
|---------|------|----------|----------|
| 可用性 | 99.95% | <99.9% | <99.5% |
| P95延迟 | ≤250ms | >200ms | >300ms |
| 错误率 | ≤0.1% | >0.5% | >1% |
| 错误预算 | 21.6min/月 | <20% | <10% |

### 附录D: 错误代码对照表

| 错误代码 | HTTP状态 | 说明 | 解决方案 |
|----------|----------|------|----------|
| `AUTH_001` | 401 | 未登录 | 重新登录 |
| `AUTH_002` | 403 | 权限不足 | 联系管理员 |
| `AUTH_003` | 401 | Session过期 | 重新登录 |
| `DB_001` | 500 | 数据库连接失败 | 检查DATABASE_URL |
| `DB_002` | 500 | 查询超时 | 优化查询或增加超时 |
| `CACHE_001` | 503 | Redis不可用 | 检查Redis服务 |
| `API_001` | 429 | 请求过于频繁 | 降低请求频率 |
| `API_002` | 500 | 外部API失败 | 稍后重试 |
| `BLOCKCHAIN_001` | 500 | 私钥未配置 | 设置BLOCKCHAIN_PRIVATE_KEY |
| `ENCRYPTION_001` | 500 | 加密密钥未配置 | 设置ENCRYPTION_PASSWORD |

### 附录E: 更新历史

| 版本 | 日期 | 作者 | 变更内容 |
|------|------|------|----------|
| v2.0 | 2025-10-03 | HashInsight Ops Team | 完整运维手册首次发布 |
| v1.9 | 2025-09-15 | DevOps Team | 添加Request Coalescing优化 |
| v1.8 | 2025-08-20 | Security Team | 增强KMS和mTLS文档 |
| v1.7 | 2025-07-10 | Platform Team | 添加SLO监控章节 |

---

## 文档维护

**维护责任**: HashInsight Platform Operations Team  
**审核周期**: 每季度  
**反馈渠道**: ops@hashinsight.net  
**文档仓库**: https://github.com/hashinsight/operations-manual

**最后更新**: 2025-10-03  
**下次审核**: 2026-01-03

---

**© 2025 HashInsight Platform. All Rights Reserved.**  
**Confidential - Internal Use Only**
