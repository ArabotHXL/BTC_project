# 🗄️ Miner Agent 数据库设计

## 📋 文档信息

- **版本**: 1.0.0
- **日期**: 2025-10-13
- **状态**: 设计阶段
- **数据库**: PostgreSQL 13+

---

## 📊 数据库概览

### 表结构总览

| 表名 | 用途 | 预估数据量 |
|------|------|-----------|
| `miner_agents` | Agent 基本信息和配置 | 100-1000 条 |
| `agent_heartbeats` | Agent 心跳记录 | 高频写入，定期清理 |
| `miner_telemetry_realtime` | 实时遥测数据 | 高频写入，1小时保留 |
| `miner_telemetry_history` | 历史遥测数据 | 中频写入，90天保留 |
| `agent_commands` | 控制指令队列 | 低频写入 |
| `agent_command_logs` | 指令执行日志 | 中频写入，永久保留 |
| `agent_events` | Agent 事件和告警 | 中频写入 |
| `agent_configs` | Agent 配置版本管理 | 低频写入 |

### 数据保留策略

```python
实时数据 (Redis):
  - 最新遥测数据: 1 小时
  - Agent 在线状态: 实时
  - 待执行指令: 实时

历史数据 (PostgreSQL):
  - 心跳记录: 7 天
  - 遥测原始数据: 90 天
  - 聚合数据 (小时/天): 永久
  - 控制日志: 永久
  - 事件告警: 永久
```

---

## 📋 表结构详细设计

### 1. miner_agents (Agent 管理表)

**用途**: 存储 Agent 基本信息、认证凭证、配置

```sql
CREATE TABLE miner_agents (
    -- 主键和标识
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(36) UNIQUE NOT NULL,  -- UUID
    agent_name VARCHAR(100) NOT NULL,      -- Agent 名称
    
    -- 关联信息
    site_id INTEGER REFERENCES hosting_sites(id),  -- 所属矿场
    created_by INTEGER REFERENCES user_access(id), -- 创建者
    
    -- 认证信息
    access_token_hash VARCHAR(256),        -- Token 哈希 (不存明文)
    token_issued_at TIMESTAMP,             -- Token 签发时间
    token_expires_at TIMESTAMP,            -- Token 过期时间
    
    -- Agent 状态
    status VARCHAR(20) DEFAULT 'pending',  -- pending/active/offline/disabled
    version VARCHAR(20),                   -- Agent 版本号
    
    -- 配置
    config_version VARCHAR(20) DEFAULT 'v1.0.0',  -- 配置版本
    collection_interval INTEGER DEFAULT 60,        -- 采集间隔(秒)
    heartbeat_interval INTEGER DEFAULT 30,         -- 心跳间隔(秒)
    permissions JSONB,                             -- 权限列表
    settings JSONB,                                -- 其他配置
    
    -- 连接信息
    last_seen_at TIMESTAMP,               -- 最后心跳时间
    last_ip VARCHAR(45),                  -- 最后连接IP
    connection_count INTEGER DEFAULT 0,  -- 连接次数
    
    -- 统计信息
    total_miners INTEGER DEFAULT 0,       -- 管理的矿机数量
    active_miners INTEGER DEFAULT 0,      -- 在线矿机数量
    total_uptime BIGINT DEFAULT 0,        -- 累计运行时间(秒)
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,                           -- 备注
    
    -- 索引
    CONSTRAINT unique_agent_id UNIQUE (agent_id)
);

-- 索引
CREATE INDEX idx_agents_status ON miner_agents(status);
CREATE INDEX idx_agents_site_id ON miner_agents(site_id);
CREATE INDEX idx_agents_last_seen ON miner_agents(last_seen_at);
```

**字段说明**:

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `agent_id` | UUID | 全局唯一标识 | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `status` | ENUM | `pending`, `active`, `offline`, `disabled` | `active` |
| `permissions` | JSONB | `["read", "control", "config"]` | - |
| `settings` | JSONB | Agent 特定配置 | `{"enable_auto_reboot": true}` |

---

### 2. agent_heartbeats (心跳记录表)

**用途**: 记录 Agent 心跳，用于监控在线状态

```sql
CREATE TABLE agent_heartbeats (
    -- 主键
    id BIGSERIAL,
    
    -- 关联
    agent_id VARCHAR(36) NOT NULL,
    
    -- 心跳信息
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'online',  -- online/degraded/error
    
    -- 系统状态
    cpu_usage NUMERIC(5,2),               -- CPU 使用率 (%)
    memory_usage NUMERIC(5,2),            -- 内存使用率 (%)
    disk_usage NUMERIC(5,2),              -- 磁盘使用率 (%)
    uptime BIGINT,                        -- Agent 运行时间 (秒)
    
    -- 网络信息
    ip_address VARCHAR(45),               -- IP 地址
    version VARCHAR(20),                  -- Agent 版本
    
    -- 统计
    miners_online INTEGER DEFAULT 0,      -- 在线矿机数
    miners_total INTEGER DEFAULT 0,       -- 总矿机数
    errors_count INTEGER DEFAULT 0,       -- 错误计数
    
    -- 其他
    extra_data JSONB,                     -- 扩展数据
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 创建分区 (按月分区，提升查询性能)
CREATE TABLE agent_heartbeats_y2025m10 PARTITION OF agent_heartbeats
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE agent_heartbeats_y2025m11 PARTITION OF agent_heartbeats
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

-- 索引
CREATE INDEX idx_heartbeats_agent_time ON agent_heartbeats(agent_id, timestamp DESC);
CREATE INDEX idx_heartbeats_timestamp ON agent_heartbeats(timestamp DESC);

-- 外键约束 (分区表后添加)
ALTER TABLE agent_heartbeats ADD CONSTRAINT fk_heartbeats_agent
    FOREIGN KEY (agent_id) REFERENCES miner_agents(agent_id) ON DELETE CASCADE;

-- 自动清理规则 (保留7天)
CREATE OR REPLACE FUNCTION cleanup_old_heartbeats()
RETURNS void AS $$
BEGIN
    DELETE FROM agent_heartbeats 
    WHERE timestamp < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;
```

**数据保留**: 7天  
**写入频率**: 每30秒/Agent  
**预估数据量**: 约 2,880 条/Agent/天

---

### 3. miner_telemetry_realtime (实时遥测数据表 - Redis)

**用途**: 存储最新的矿机遥测数据，用于实时监控

**存储引擎**: Redis Hash

```python
# Redis Key 设计
key_pattern = "telemetry:realtime:{agent_id}:{miner_ip}"

# 数据结构
{
    "ip_address": "192.168.1.100",
    "mac_address": "00:1A:2B:3C:4D:5E",
    "serial_number": "S19-12345",
    "miner_type": "Antminer S19 Pro",
    "status": "running",
    "hashrate_th": "110.5",
    "temperature_avg": "68.3",
    "temperature_max": "72.1",
    "fan_speed_avg": "4500",
    "power_consumption_w": "3250",
    "pool_url": "stratum+tcp://pool.example.com:3333",
    "pool_worker": "worker001",
    "accepted_shares": "12543",
    "rejected_shares": "23",
    "hardware_errors": "0",
    "uptime_seconds": "86400",
    "last_updated": "1729872000",  # Unix timestamp
}

# TTL: 1 小时
# 索引: Redis Secondary Index (RediSearch 模块)
```

---

### 4. miner_telemetry_history (历史遥测数据表)

**用途**: 存储历史遥测数据，用于趋势分析和报表

```sql
CREATE TABLE miner_telemetry_history (
    -- 主键
    id BIGSERIAL,
    
    -- 关联
    agent_id VARCHAR(36) NOT NULL,
    miner_id INTEGER,
    
    -- 时间戳
    timestamp TIMESTAMP NOT NULL,
    
    -- 矿机标识
    ip_address VARCHAR(45),
    mac_address VARCHAR(17),
    serial_number VARCHAR(50),
    miner_type VARCHAR(50),
    
    -- 运行状态
    status VARCHAR(20),                   -- running/stopped/error
    
    -- 性能数据
    hashrate_th NUMERIC(10,2),            -- 算力 (TH/s)
    hashrate_5s NUMERIC(10,2),            -- 5秒平均算力
    hashrate_1m NUMERIC(10,2),            -- 1分钟平均算力
    hashrate_5m NUMERIC(10,2),            -- 5分钟平均算力
    hashrate_15m NUMERIC(10,2),           -- 15分钟平均算力
    
    -- 温度数据
    temperature_avg NUMERIC(5,2),         -- 平均温度 (°C)
    temperature_max NUMERIC(5,2),         -- 最高温度
    temperature_min NUMERIC(5,2),         -- 最低温度
    temperature_board1 NUMERIC(5,2),      -- 板1温度
    temperature_board2 NUMERIC(5,2),      -- 板2温度
    temperature_board3 NUMERIC(5,2),      -- 板3温度
    
    -- 风扇数据
    fan_speed_avg INTEGER,                -- 平均风扇转速 (RPM)
    fan_speed_max INTEGER,                -- 最高风扇转速
    fan1_speed INTEGER,                   -- 风扇1转速
    fan2_speed INTEGER,                   -- 风扇2转速
    fan3_speed INTEGER,                   -- 风扇3转速
    fan4_speed INTEGER,                   -- 风扇4转速
    
    -- 功耗数据
    power_consumption_w NUMERIC(8,2),     -- 功耗 (W)
    voltage_v NUMERIC(6,2),               -- 电压 (V)
    current_a NUMERIC(6,2),               -- 电流 (A)
    
    -- 矿池数据
    pool_url VARCHAR(200),                -- 矿池地址
    pool_worker VARCHAR(100),             -- 矿工名
    pool_status VARCHAR(20),              -- 矿池连接状态
    
    -- 份额数据
    accepted_shares BIGINT,               -- 接受份额
    rejected_shares BIGINT,               -- 拒绝份额
    hardware_errors BIGINT,               -- 硬件错误
    reject_rate NUMERIC(5,2),             -- 拒绝率 (%)
    
    -- 其他
    uptime_seconds BIGINT,                -- 运行时间 (秒)
    frequency_mhz INTEGER,                -- 频率 (MHz)
    raw_data JSONB,                       -- 原始数据
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- 创建分区 (按月分区)
CREATE TABLE miner_telemetry_y2025m10 PARTITION OF miner_telemetry_history
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

CREATE TABLE miner_telemetry_y2025m11 PARTITION OF miner_telemetry_history
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');

CREATE TABLE miner_telemetry_y2025m12 PARTITION OF miner_telemetry_history
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- 索引
CREATE INDEX idx_telemetry_agent_time ON miner_telemetry_history(agent_id, timestamp DESC);
CREATE INDEX idx_telemetry_miner_time ON miner_telemetry_history(miner_id, timestamp DESC);
CREATE INDEX idx_telemetry_ip_time ON miner_telemetry_history(ip_address, timestamp DESC);
CREATE INDEX idx_telemetry_timestamp ON miner_telemetry_history(timestamp DESC);

-- 复合索引 (用于聚合查询)
CREATE INDEX idx_telemetry_agg ON miner_telemetry_history(agent_id, date_trunc('hour', timestamp));

-- 外键约束 (分区表后添加)
ALTER TABLE miner_telemetry_history ADD CONSTRAINT fk_telemetry_miner
    FOREIGN KEY (miner_id) REFERENCES hosting_miners(id) ON DELETE SET NULL;
```

**数据保留**: 90天原始数据  
**写入频率**: 每60秒/矿机  
**预估数据量**: 约 1,440 条/矿机/天

---

### 5. agent_commands (控制指令队列表)

**用途**: 存储待执行的控制指令

```sql
CREATE TABLE agent_commands (
    -- 主键
    id SERIAL PRIMARY KEY,
    command_id VARCHAR(36) UNIQUE NOT NULL,  -- UUID
    
    -- 关联
    agent_id VARCHAR(36) NOT NULL REFERENCES miner_agents(agent_id),
    created_by INTEGER REFERENCES user_access(id),  -- 创建者
    
    -- 指令信息
    command_type VARCHAR(50) NOT NULL,      -- reboot_miner/switch_pool/etc
    target_ip VARCHAR(45),                  -- 目标矿机IP
    target_miner_id INTEGER REFERENCES hosting_miners(id),  -- 目标矿机ID
    
    -- 指令参数
    params JSONB,                           -- 指令参数
    
    -- 状态
    status VARCHAR(20) DEFAULT 'pending',   -- pending/sent/executing/completed/failed/timeout
    priority INTEGER DEFAULT 0,             -- 优先级 (0-9)
    
    -- 执行信息
    sent_at TIMESTAMP,                      -- 下发时间
    executed_at TIMESTAMP,                  -- 执行时间
    completed_at TIMESTAMP,                 -- 完成时间
    timeout_seconds INTEGER DEFAULT 300,    -- 超时时间 (秒)
    
    -- 结果
    result JSONB,                           -- 执行结果
    error_message TEXT,                     -- 错误信息
    
    -- 重试机制
    retry_count INTEGER DEFAULT 0,          -- 重试次数
    max_retries INTEGER DEFAULT 3,          -- 最大重试次数
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- 索引
CREATE INDEX idx_commands_agent_status ON agent_commands(agent_id, status);
CREATE INDEX idx_commands_status ON agent_commands(status) WHERE status IN ('pending', 'sent');
CREATE INDEX idx_commands_created ON agent_commands(created_at DESC);
```

**字段说明**:

| command_type | params | 说明 |
|-------------|--------|------|
| `reboot_miner` | `{"delay_seconds": 30}` | 重启矿机 |
| `switch_pool` | `{"pool_url": "...", "worker": "..."}` | 切换矿池 |
| `adjust_frequency` | `{"frequency_mhz": 550}` | 调整频率 |
| `enable_low_power` | `{}` | 低功耗模式 |
| `update_config` | `{"config": {...}}` | 更新配置 |

---

### 6. agent_command_logs (指令执行日志表)

**用途**: 记录所有指令的完整生命周期，用于审计

```sql
CREATE TABLE agent_command_logs (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    
    -- 关联
    command_id VARCHAR(36) NOT NULL REFERENCES agent_commands(command_id),
    agent_id VARCHAR(36) NOT NULL,
    
    -- 日志信息
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    log_level VARCHAR(10),                 -- INFO/WARNING/ERROR
    event_type VARCHAR(50),                -- created/sent/executed/completed/failed
    
    -- 状态变更
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    
    -- 详情
    message TEXT,                          -- 日志消息
    details JSONB,                         -- 详细信息
    
    -- 执行者
    executed_by VARCHAR(50),               -- user/agent/system
    
    -- 性能
    execution_time_ms INTEGER              -- 执行耗时 (毫秒)
);

-- 索引
CREATE INDEX idx_cmdlogs_command ON agent_command_logs(command_id, timestamp);
CREATE INDEX idx_cmdlogs_agent ON agent_command_logs(agent_id, timestamp DESC);
CREATE INDEX idx_cmdlogs_timestamp ON agent_command_logs(timestamp DESC);
```

---

### 7. agent_events (Agent 事件和告警表)

**用途**: 记录 Agent 重要事件和告警

```sql
CREATE TABLE agent_events (
    -- 主键
    id BIGSERIAL PRIMARY KEY,
    
    -- 关联
    agent_id VARCHAR(36) NOT NULL,
    site_id INTEGER REFERENCES hosting_sites(id),
    
    -- 事件信息
    event_type VARCHAR(50) NOT NULL,       -- agent_registered/agent_offline/miner_error/etc
    severity VARCHAR(20) DEFAULT 'info',   -- info/warning/error/critical
    
    -- 详情
    title VARCHAR(200) NOT NULL,           -- 事件标题
    message TEXT,                          -- 事件描述
    details JSONB,                         -- 详细数据
    
    -- 关联对象
    related_miner_ip VARCHAR(45),          -- 相关矿机
    related_command_id VARCHAR(36),        -- 相关指令
    
    -- 状态
    status VARCHAR(20) DEFAULT 'open',     -- open/acknowledged/resolved
    acknowledged_by INTEGER REFERENCES user_access(id),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_events_agent_time ON agent_events(agent_id, created_at DESC);
CREATE INDEX idx_events_severity ON agent_events(severity) WHERE status = 'open';
CREATE INDEX idx_events_status ON agent_events(status, created_at DESC);
```

**事件类型示例**:

| event_type | severity | 说明 |
|-----------|----------|------|
| `agent_registered` | `info` | Agent 首次注册 |
| `agent_offline` | `warning` | Agent 离线 |
| `agent_reconnected` | `info` | Agent 重新连接 |
| `miner_offline` | `error` | 矿机离线 |
| `high_temperature` | `warning` | 温度过高 |
| `hashrate_drop` | `error` | 算力异常下降 |
| `command_failed` | `error` | 指令执行失败 |

---

### 8. agent_configs (配置版本管理表)

**用途**: 管理 Agent 配置的版本和历史

```sql
CREATE TABLE agent_configs (
    -- 主键
    id SERIAL PRIMARY KEY,
    
    -- 版本信息
    version VARCHAR(20) UNIQUE NOT NULL,   -- 版本号 (如 v1.0.0)
    
    -- 配置内容
    config_data JSONB NOT NULL,            -- 完整配置
    
    -- 适用范围
    applies_to VARCHAR(10) DEFAULT 'all',  -- all/specific
    agent_ids TEXT[],                      -- 适用的 agent_id 列表
    
    -- 状态
    status VARCHAR(20) DEFAULT 'draft',    -- draft/active/deprecated
    is_default BOOLEAN DEFAULT FALSE,      -- 是否为默认配置
    
    -- 变更信息
    change_summary TEXT,                   -- 变更摘要
    created_by INTEGER REFERENCES user_access(id),
    
    -- 元数据
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activated_at TIMESTAMP,
    deprecated_at TIMESTAMP
);

-- 索引
CREATE INDEX idx_configs_version ON agent_configs(version);
CREATE INDEX idx_configs_status ON agent_configs(status);
```

**配置示例**:

```json
{
  "version": "v1.0.0",
  "collection_interval": 60,
  "heartbeat_interval": 30,
  "cgminer_api_timeout": 5,
  "retry_policy": {
    "max_retries": 3,
    "backoff_seconds": [5, 15, 30]
  },
  "buffer_config": {
    "max_buffer_size": 10000,
    "max_buffer_hours": 24
  },
  "features": {
    "enable_auto_discovery": false,
    "enable_remote_control": true,
    "enable_auto_reboot": false
  }
}
```

---

## 🔍 数据查询示例

### 1. 获取 Agent 实时状态

```sql
SELECT 
    a.agent_id,
    a.agent_name,
    a.status,
    a.version,
    a.last_seen_at,
    a.total_miners,
    a.active_miners,
    h.cpu_usage,
    h.memory_usage,
    h.disk_usage
FROM miner_agents a
LEFT JOIN LATERAL (
    SELECT cpu_usage, memory_usage, disk_usage
    FROM agent_heartbeats
    WHERE agent_id = a.agent_id
    ORDER BY timestamp DESC
    LIMIT 1
) h ON true
WHERE a.status = 'active'
ORDER BY a.last_seen_at DESC;
```

### 2. 获取矿机实时数据 (Redis + PostgreSQL)

```python
# Step 1: 从 Redis 获取实时数据
redis_key = f"telemetry:realtime:{agent_id}:*"
realtime_data = redis.hgetall(redis_key)

# Step 2: 如果 Redis 无数据，从 PostgreSQL 获取最新数据
if not realtime_data:
    sql = """
    SELECT * FROM miner_telemetry_history
    WHERE agent_id = %s
      AND timestamp > NOW() - INTERVAL '5 minutes'
    ORDER BY timestamp DESC
    LIMIT 100
    """
```

### 3. 统计 Agent 性能指标

```sql
SELECT 
    agent_id,
    COUNT(*) as total_commands,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - created_at))), 2) as avg_execution_time
FROM agent_commands
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY agent_id;
```

### 4. 告警汇总

```sql
SELECT 
    severity,
    COUNT(*) as event_count,
    COUNT(CASE WHEN status = 'open' THEN 1 END) as open_count
FROM agent_events
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY severity
ORDER BY 
    CASE severity
        WHEN 'critical' THEN 1
        WHEN 'error' THEN 2
        WHEN 'warning' THEN 3
        WHEN 'info' THEN 4
    END;
```

---

## 🚀 性能优化

### 1. 分区策略

```sql
-- 按月分区 (遥测数据)
CREATE TABLE miner_telemetry_y2025m10 PARTITION OF miner_telemetry_history
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');

-- 按周分区 (心跳数据)
CREATE TABLE agent_heartbeats_y2025w41 PARTITION OF agent_heartbeats
    FOR VALUES FROM ('2025-10-07') TO ('2025-10-14');
```

### 2. 批量插入

```python
# 使用 COPY 命令批量插入
from io import StringIO
import psycopg2

def batch_insert_telemetry(data_list):
    buffer = StringIO()
    for row in data_list:
        buffer.write('\t'.join(map(str, row)) + '\n')
    
    buffer.seek(0)
    cursor.copy_from(buffer, 'miner_telemetry_history', columns=[...])
```

### 3. 索引优化

```sql
-- 部分索引 (仅索引活跃数据)
CREATE INDEX idx_active_commands ON agent_commands(agent_id, created_at)
    WHERE status IN ('pending', 'sent', 'executing');

-- 覆盖索引 (包含常用字段)
CREATE INDEX idx_telemetry_cover ON miner_telemetry_history(
    agent_id, timestamp, hashrate_th, temperature_avg, power_consumption_w
);
```

### 4. 自动清理

```sql
-- 定时任务 (使用 pg_cron)
SELECT cron.schedule('cleanup_old_data', '0 2 * * *', $$
    DELETE FROM agent_heartbeats WHERE timestamp < NOW() - INTERVAL '7 days';
    DELETE FROM miner_telemetry_history WHERE timestamp < NOW() - INTERVAL '90 days';
    VACUUM ANALYZE agent_heartbeats, miner_telemetry_history;
$$);
```

---

## 📊 聚合视图

### 1. Agent 监控汇总视图

```sql
CREATE MATERIALIZED VIEW agent_monitoring_summary AS
SELECT 
    a.agent_id,
    a.agent_name,
    a.status,
    a.total_miners,
    a.active_miners,
    a.last_seen_at,
    
    -- 最新心跳
    (SELECT cpu_usage FROM agent_heartbeats WHERE agent_id = a.agent_id ORDER BY timestamp DESC LIMIT 1) as cpu_usage,
    (SELECT memory_usage FROM agent_heartbeats WHERE agent_id = a.agent_id ORDER BY timestamp DESC LIMIT 1) as memory_usage,
    
    -- 告警统计
    (SELECT COUNT(*) FROM agent_events WHERE agent_id = a.agent_id AND status = 'open' AND severity = 'critical') as critical_alerts,
    (SELECT COUNT(*) FROM agent_events WHERE agent_id = a.agent_id AND status = 'open' AND severity = 'error') as error_alerts,
    
    -- 指令统计
    (SELECT COUNT(*) FROM agent_commands WHERE agent_id = a.agent_id AND status = 'pending') as pending_commands
    
FROM miner_agents a
WHERE a.status != 'disabled';

-- 每5分钟刷新一次
CREATE UNIQUE INDEX ON agent_monitoring_summary(agent_id);
REFRESH MATERIALIZED VIEW CONCURRENTLY agent_monitoring_summary;
```

### 2. 矿机性能聚合 (小时级)

```sql
CREATE TABLE miner_telemetry_hourly (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(36) NOT NULL,
    miner_id INTEGER,
    hour_bucket TIMESTAMP NOT NULL,
    
    -- 聚合数据
    avg_hashrate NUMERIC(10,2),
    max_hashrate NUMERIC(10,2),
    min_hashrate NUMERIC(10,2),
    
    avg_temperature NUMERIC(5,2),
    max_temperature NUMERIC(5,2),
    
    avg_power NUMERIC(8,2),
    
    total_accepted_shares BIGINT,
    total_rejected_shares BIGINT,
    avg_reject_rate NUMERIC(5,2),
    
    uptime_percentage NUMERIC(5,2),
    sample_count INTEGER,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(agent_id, miner_id, hour_bucket)
);

-- 定时聚合任务
SELECT cron.schedule('aggregate_hourly', '5 * * * *', $$
    INSERT INTO miner_telemetry_hourly (agent_id, miner_id, hour_bucket, ...)
    SELECT 
        agent_id,
        miner_id,
        date_trunc('hour', timestamp) as hour_bucket,
        AVG(hashrate_th),
        MAX(hashrate_th),
        MIN(hashrate_th),
        AVG(temperature_avg),
        MAX(temperature_max),
        AVG(power_consumption_w),
        SUM(accepted_shares),
        SUM(rejected_shares),
        AVG(reject_rate),
        COUNT(*) * 100.0 / 60 as uptime_percentage,
        COUNT(*)
    FROM miner_telemetry_history
    WHERE timestamp >= date_trunc('hour', NOW() - INTERVAL '1 hour')
      AND timestamp < date_trunc('hour', NOW())
    GROUP BY agent_id, miner_id, hour_bucket
    ON CONFLICT (agent_id, miner_id, hour_bucket) DO NOTHING;
$$);
```

---

## 🔒 安全和权限

### 1. 行级安全 (RLS)

```sql
-- 启用 RLS
ALTER TABLE agent_events ENABLE ROW LEVEL SECURITY;

-- 用户只能看到自己矿场的 Agent 事件
CREATE POLICY agent_events_policy ON agent_events
    FOR SELECT
    USING (
        site_id IN (
            SELECT site_id FROM user_site_access 
            WHERE user_id = current_setting('app.current_user_id')::INTEGER
        )
    );
```

### 2. 敏感字段加密

```sql
-- 使用 pgcrypto 加密 Token
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 插入时加密
INSERT INTO miner_agents (agent_id, access_token_hash, ...)
VALUES ('uuid', crypt('raw_token', gen_salt('bf')), ...);

-- 验证 Token
SELECT agent_id FROM miner_agents
WHERE access_token_hash = crypt('input_token', access_token_hash);
```

---

## 📈 扩展性考虑

### 1. 时序数据库方案 (可选)

如果遥测数据量超大，可考虑使用 TimescaleDB:

```sql
-- 安装 TimescaleDB 扩展
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 将表转换为 hypertable
SELECT create_hypertable('miner_telemetry_history', 'timestamp');

-- 自动数据保留策略
SELECT add_retention_policy('miner_telemetry_history', INTERVAL '90 days');

-- 连续聚合
CREATE MATERIALIZED VIEW telemetry_hourly
WITH (timescaledb.continuous) AS
SELECT 
    time_bucket('1 hour', timestamp) AS bucket,
    agent_id,
    AVG(hashrate_th) as avg_hashrate,
    MAX(temperature_max) as max_temperature
FROM miner_telemetry_history
GROUP BY bucket, agent_id;
```

### 2. 读写分离

```python
# 主库 (写)
MASTER_DB = "postgresql://user:pass@master-host/db"

# 从库 (读)
SLAVE_DB = "postgresql://user:pass@slave-host/db"

# 根据操作类型选择连接
def get_db_connection(read_only=True):
    return SLAVE_DB if read_only else MASTER_DB
```

---

## 📋 初始化 SQL 脚本

完整的表创建脚本请参见: [`init_agent_tables.sql`](../sql/init_agent_tables.sql)

---

**文档版本**: v1.0.0  
**最后更新**: 2025-10-13
