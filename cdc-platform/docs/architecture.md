# HashInsight CDC Platform - 架构文档

## 1. 系统拓扑图

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[Web Browser]
        API_CLIENT[API Clients]
    end
    
    subgraph "API Gateway"
        FLASK[Flask App<br/>Gunicorn Workers]
        AUTH[JWT Auth<br/>Scope Validation]
        RATE[Rate Limiter<br/>Redis]
    end
    
    subgraph "Domain Services"
        MINERS[Miners API<br/>POST/PATCH]
        INTEL[Intelligence API<br/>GET Forecast]
        TREASURY[Treasury API<br/>POST Trade]
        HEALTH[Health API<br/>GET Metrics]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL 15<br/>+ TimescaleDB)]
        REDIS[(Redis<br/>Cache + Lock)]
        OUTBOX[event_outbox<br/>Transactional]
        INBOX[consumer_inbox<br/>Idempotency]
    end
    
    subgraph "CDC Pipeline"
        DEBEZIUM[Debezium<br/>PostgreSQL Connector]
        CONNECT[Kafka Connect]
    end
    
    subgraph "Message Bus"
        KAFKA[Apache Kafka]
        TOPIC_MINER[events.miner]
        TOPIC_TREASURY[events.treasury]
        TOPIC_OPS[events.ops]
        TOPIC_DLQ[events.dlq]
    end
    
    subgraph "Event Consumers"
        PORTFOLIO[Portfolio Consumer<br/>Recalculate + Cache Invalidation]
        INTELLIGENCE[Intelligence Consumer<br/>Forecast Refresh]
        LOCKS[Distributed Locks<br/>Redis]
    end
    
    subgraph "Storage"
        FORECAST[forecast_daily<br/>Hypertable]
        TELEMETRY[miner_telemetry<br/>Hypertable]
        PORTFOLIO_TBL[user_portfolios]
    end
    
    WEB --> FLASK
    API_CLIENT --> FLASK
    FLASK --> AUTH
    AUTH --> RATE
    RATE --> MINERS
    RATE --> INTEL
    RATE --> TREASURY
    RATE --> HEALTH
    
    MINERS -.写入事务.-> PG
    MINERS -.同事务.-> OUTBOX
    INTEL --> REDIS
    INTEL --> FORECAST
    
    OUTBOX --> DEBEZIUM
    DEBEZIUM --> CONNECT
    CONNECT --> KAFKA
    
    KAFKA --> TOPIC_MINER
    KAFKA --> TOPIC_TREASURY
    KAFKA --> TOPIC_OPS
    KAFKA --> TOPIC_DLQ
    
    TOPIC_MINER --> PORTFOLIO
    TOPIC_MINER --> INTELLIGENCE
    
    PORTFOLIO --> LOCKS
    PORTFOLIO --> INBOX
    PORTFOLIO --> PORTFOLIO_TBL
    PORTFOLIO -.失效.-> REDIS
    
    INTELLIGENCE --> FORECAST
    INTELLIGENCE --> INBOX
    
    style OUTBOX fill:#f9f,stroke:#333
    style DEBEZIUM fill:#9f9,stroke:#333
    style KAFKA fill:#99f,stroke:#333
    style REDIS fill:#f99,stroke:#333
```

## 2. 端到端时序图

```mermaid
sequenceDiagram
    participant Client
    participant Flask API
    participant PostgreSQL
    participant Outbox
    participant Debezium
    participant Kafka
    participant Portfolio Worker
    participant Redis Cache
    
    Note over Client,Redis Cache: POST /api/miners - 创建矿机
    
    Client->>Flask API: POST /api/miners<br/>{model, hashrate, power...}
    Flask API->>Flask API: JWT验证 + Scope检查
    
    rect rgb(200, 230, 255)
        Note over Flask API,Outbox: 数据库事务（原子性保证）
        Flask API->>PostgreSQL: INSERT INTO user_miners
        Flask API->>Outbox: INSERT INTO event_outbox<br/>{kind: miner.added, user_id, payload}
        PostgreSQL-->>Flask API: 事务提交成功
    end
    
    Flask API-->>Client: 200 OK {miner_id}
    
    Note over Debezium,Kafka: CDC Pipeline（异步）
    
    Debezium->>Outbox: 监听 WAL (Write-Ahead Log)
    Outbox-->>Debezium: 捕获新记录
    Debezium->>Debezium: 转换为事件<br/>key=user_id
    Debezium->>Kafka: 发布到 events.miner<br/>partition=hash(user_id)
    
    Note over Portfolio Worker,Redis Cache: 消费者处理（幂等+重算）
    
    Kafka-->>Portfolio Worker: 消费消息<br/>{kind, user_id, payload}
    
    Portfolio Worker->>Redis Cache: 获取分布式锁<br/>lock:recalc:{user_id}
    Redis Cache-->>Portfolio Worker: 锁获取成功
    
    Portfolio Worker->>PostgreSQL: 检查 consumer_inbox<br/>(consumer, event_id)
    
    alt 未处理过
        Portfolio Worker->>PostgreSQL: INSERT INTO consumer_inbox
        Portfolio Worker->>Portfolio Worker: recalc_user_portfolio(user_id)
        Portfolio Worker->>PostgreSQL: UPDATE user_portfolios
        Portfolio Worker->>Redis Cache: DEL user_portfolio:{user_id}<br/>缓存失效
        Portfolio Worker->>Redis Cache: 释放锁
        Portfolio Worker->>Kafka: 处理成功
    else 已处理（幂等）
        Portfolio Worker->>Redis Cache: 释放锁
        Portfolio Worker->>Kafka: 跳过（幂等）
    end
    
    Note over Client,Redis Cache: GET /analytics/main - 查询更新
    
    Client->>Flask API: GET /analytics/main
    Flask API->>Redis Cache: GET user_portfolio:{user_id}
    
    alt 缓存失效
        Redis Cache-->>Flask API: cache miss
        Flask API->>PostgreSQL: SELECT FROM user_portfolios
        PostgreSQL-->>Flask API: 最新数据
        Flask API->>Redis Cache: SET user_portfolio:{user_id}<br/>TTL=600s
        Flask API-->>Client: 200 OK {portfolio, cache_hit: false}
    else 缓存命中
        Redis Cache-->>Flask API: 缓存数据
        Flask API-->>Client: 200 OK {portfolio, cache_hit: true}
    end
    
    Note over Client,Redis Cache: P95延迟 ≤ 3s（写库→页面可见）
```

## 3. 领域模型ER图

```mermaid
erDiagram
    USER ||--o{ USER_MINER : owns
    USER ||--o{ USER_PORTFOLIO : has
    USER ||--o{ EVENT_OUTBOX : generates
    
    MINER_MODEL ||--o{ USER_MINER : references
    
    EVENT_OUTBOX ||--o{ CONSUMER_INBOX : "processed by"
    EVENT_OUTBOX ||--o{ EVENT_DLQ : "failed to"
    
    USER {
        text id PK
        text email UK
        text tenant_id
        text role
    }
    
    USER_MINER {
        int id PK
        int user_id FK
        int miner_model_id FK
        int quantity
        double actual_hashrate
        int actual_power
        double electricity_cost
        timestamp created_at
    }
    
    MINER_MODEL {
        int id PK
        varchar model_name
        varchar manufacturer
        double reference_hashrate
        int reference_power
        date release_date
    }
    
    EVENT_OUTBOX {
        text id PK
        text kind
        text user_id
        text tenant_id
        text entity_id
        jsonb payload
        text idempotency_key UK
        timestamptz created_at
        bool processed
    }
    
    CONSUMER_INBOX {
        text consumer_name PK
        text event_id PK
        text event_kind
        text user_id
        jsonb payload
        timestamptz consumed_at
        int processing_duration_ms
    }
    
    EVENT_DLQ {
        text id PK
        text consumer_name
        text event_id
        text event_kind
        jsonb payload
        text error_message
        int retry_count
        timestamptz first_failed_at
        bool resolved
    }
    
    USER_PORTFOLIO {
        int id PK
        int user_id FK
        numeric btc_inventory
        numeric avg_cost_basis
        numeric monthly_opex
        timestamptz last_updated
    }
    
    FORECAST_DAILY {
        int id PK
        varchar user_id
        date forecast_date
        numeric predicted_btc_price
        numeric predicted_difficulty
        numeric confidence_score
        timestamptz created_at
    }
```

## 4. 核心设计模式

### 4.1 Transactional Outbox模式

**问题**：如何保证数据库写入和事件发布的原子性？

**解决方案**：
1. 业务数据和事件在同一个数据库事务中写入
2. `event_outbox`表作为"发件箱"存储待发布事件
3. Debezium监听PostgreSQL WAL，自动捕获outbox变更
4. 事件通过Kafka发布，无需应用层轮询

**优点**：
- ✅ 原子性保证（事务ACID）
- ✅ 无数据丢失
- ✅ 应用层无需关心消息发送
- ✅ 支持高吞吐（批量捕获）

### 4.2 Inbox幂等模式

**问题**：如何防止消息重复消费？

**解决方案**：
1. `consumer_inbox`表记录已消费事件
2. 复合主键`(consumer_name, event_id)`确保唯一
3. 消费前先检查inbox，已存在则跳过

**优点**：
- ✅ 数据库级别幂等保证
- ✅ 支持多消费者独立去重
- ✅ 可追溯消费历史

### 4.3 分布式锁模式

**问题**：如何防止并发重算冲突？

**解决方案**：
1. Redis `SETNX` 命令实现分布式锁
2. 锁键：`lock:recalc:{user_id}`
3. TTL自动过期防止死锁
4. 获取锁后才执行重算逻辑

### 4.4 SWR缓存模式

**问题**：如何平衡缓存性能和数据新鲜度？

**解决方案**：
1. 先返回缓存数据（Stale）
2. 后台异步刷新（Revalidate）
3. 设置合理TTL（portfolio 600s, forecast 1800s）
4. 事件驱动失效（精准失效）

## 5. 性能指标

| 指标 | 目标 | 监控方式 |
|------|------|---------|
| **写库→可见延迟** | P95 ≤ 3s | `/api/health` 的 `forecast_freshness_sec` |
| **Outbox积压** | < 100 | `/api/health` 的 `outbox_backlog` |
| **消费者延迟** | < 2s | `/api/health` 的 `kafka_consumer_lag` |
| **DLQ失败率** | < 0.1% | `/api/health` 的 `dlq_count` |
| **缓存命中率** | > 80% | `/api/health` 的 `cache_hit_rate` |

## 6. 安全与合规

### 6.1 Row Level Security (RLS)

```sql
-- 多租户隔离
ALTER TABLE user_miners ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_miners_tenant_policy ON user_miners
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id', true));
```

### 6.2 数据加密

- **传输加密**：TLS 1.3
- **存储加密**：PostgreSQL透明数据加密（TDE）
- **敏感字段**：矿机密码、API密钥使用KMS加密

### 6.3 审计日志

所有写操作自动记录到`audit_logs`表：
- 用户ID、租户ID
- 操作类型（CREATE/UPDATE/DELETE）
- 资源类型和ID
- IP地址、User-Agent
- 时间戳

## 7. 故障处理

### 7.1 DLQ（死信队列）

失败重试机制：
1. 首次失败：立即重试
2. 第2次失败：5秒后重试
3. 第3次失败：写入`event_dlq`表

人工干预：
```bash
# 查看DLQ
SELECT * FROM event_dlq WHERE resolved = false;

# 重放失败事件
python scripts/replay_dlq.py --event-id <id>
```

### 7.2 回溯机制

按时间窗口重放事件：
```bash
# 重放最近1小时的事件
python scripts/replay_events.py --start '2024-01-01 10:00' --end '2024-01-01 11:00'
```

## 8. 扩展性

### 8.1 水平扩展

- **API层**：无状态，可横向扩展
- **Worker层**：Kafka分区机制，增加worker自动负载均衡
- **数据库**：TimescaleDB分布式部署

### 8.2 新增事件类型

1. 在`connectors/outbox-connector.json`添加路由规则
2. 创建新Kafka主题：`events.<domain>`
3. 实现新Worker消费者
4. 更新健康检查指标
