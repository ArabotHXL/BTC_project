# Telemetry 数据契约 (Data Contract)

## 版本: 1.0
## 日期: 2026-01-26

## 四层遥测存储架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      数据流向 (Data Flow)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Edge Collector → raw_24h → Aggregator Job → live + history   │
│                                                                 │
│   采集器写入        原始层      后台聚合任务     快照层 + 趋势层    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 1. telemetry_raw_24h (原始层)

### 定位
- **含义**: 原始、最全、量最大的数据
- **用途**: 故障取证、模型训练、采集异常核对
- **特点**: 写多读少，保留 24 小时

### 字段定义
| 字段 | 类型 | 必填 | 说明 | 单位 |
|------|------|------|------|------|
| `id` | BIGINT | Y | 主键 | - |
| `ts` | TIMESTAMP | Y | 采集时间戳 | UTC |
| `site_id` | INTEGER | Y | 站点 ID | - |
| `miner_id` | VARCHAR | Y | 矿机 ID | - |
| `status` | VARCHAR | N | 状态 (online/offline/error) | - |
| `hashrate_ths` | DOUBLE | N | **即时算力** | TH/s |
| `temperature_c` | DOUBLE | N | 温度 | °C |
| `power_w` | DOUBLE | N | 功耗 | W |
| `fan_rpm` | INTEGER | N | 风扇转速 | RPM |
| `reject_rate` | DOUBLE | N | 拒绝率 (0-1) | ratio |
| `pool_url` | VARCHAR | N | 矿池地址 | - |

### 数据口径
- `hashrate_ths`: **瞬时值** (采集时刻的即时算力)
- `reject_rate`: **区间累计** (自上次采集以来的拒绝率)
- 采集频率: 每 60 秒

---

## 2. miner_telemetry_live (快照层)

### 定位
- **含义**: 每台矿机的"当前最新状态"，只保留最新一条
- **用途**: 列表显示、总览页、地图、站点健康、实时告警判断
- **特点**: 读多写多，每台矿机只有一条记录

### 字段定义
| 字段 | 类型 | 必填 | 说明 | 单位 |
|------|------|------|------|------|
| `id` | INTEGER | Y | 主键 | - |
| `miner_id` | VARCHAR | Y | 矿机 ID (唯一) | - |
| `site_id` | INTEGER | Y | 站点 ID | - |
| `online` | BOOLEAN | N | 是否在线 | - |
| `last_seen` | TIMESTAMP | N | 最后上报时间 | UTC |
| `hashrate_ghs` | DOUBLE | N | **5分钟平均算力** | GH/s |
| `hashrate_5s_ghs` | DOUBLE | N | 5秒滑动平均算力 | GH/s |
| `hashrate_expected_ghs` | DOUBLE | N | 期望算力 | GH/s |
| `temperature_avg` | DOUBLE | N | 平均温度 | °C |
| `temperature_max` | DOUBLE | N | 最高温度 | °C |
| `temperature_min` | DOUBLE | N | 最低温度 | °C |
| `temperature_chips` | JSON | N | 各芯片温度 | °C |
| `fan_speeds` | JSON | N | 各风扇转速 | RPM |
| `frequency_avg` | DOUBLE | N | 平均频率 | MHz |
| `accepted_shares` | INTEGER | N | 累计接受份额 | - |
| `rejected_shares` | INTEGER | N | 累计拒绝份额 | - |
| `hardware_errors` | INTEGER | N | 硬件错误数 | - |
| `uptime_seconds` | INTEGER | N | 运行时间 | seconds |
| `power_consumption` | DOUBLE | N | 功耗 | W |
| `efficiency` | DOUBLE | N | 能效比 | J/TH |
| `pool_url` | VARCHAR | N | 矿池地址 | - |
| `worker_name` | VARCHAR | N | 工人名称 | - |
| `model` | VARCHAR | N | 矿机型号 | - |
| `firmware_version` | VARCHAR | N | 固件版本 | - |
| `error_message` | TEXT | N | 错误信息 | - |
| `boards_data` | JSONB | N | 板级数据 | - |
| `boards_healthy` | INTEGER | N | 健康板数 | - |
| `boards_total` | INTEGER | N | 总板数 | - |
| `pool_latency_ms` | DOUBLE | N | 矿池延迟 | ms |
| `overall_health` | VARCHAR | N | 整体健康状态 | - |
| `updated_at` | TIMESTAMP | N | 更新时间 | UTC |

### 数据口径
- `hashrate_ghs`: **5分钟滑动平均** (用于稳定显示)
- `hashrate_5s_ghs`: **5秒滑动平均** (用于实时监控)
- `temperature_avg`: 所有芯片的平均温度
- `online`: 最近 5 分钟内有上报数据

### 计算公式
```python
reject_rate = rejected_shares / (accepted_shares + rejected_shares) if total > 0 else 0
efficiency = power_consumption / (hashrate_ghs / 1000) if hashrate_ghs > 0 else 0  # J/TH
online = (now - last_seen) < 300  # 5 minutes
```

---

## 3. telemetry_history_5min (趋势层)

### 定位
- **含义**: 按 5 分钟聚合的时间序列
- **用途**: 折线图、异常检测、基线计算、可用率统计
- **特点**: 读多，存储经济，保留 30-90 天

### 字段定义
| 字段 | 类型 | 必填 | 说明 | 单位 |
|------|------|------|------|------|
| `id` | BIGINT | Y | 主键 | - |
| `bucket_ts` | TIMESTAMP | Y | 5分钟时间桶起始时间 | UTC |
| `site_id` | INTEGER | Y | 站点 ID | - |
| `miner_id` | VARCHAR | Y | 矿机 ID | - |
| `avg_hashrate_ths` | DOUBLE | N | **平均算力** | TH/s |
| `max_hashrate_ths` | DOUBLE | N | 最大算力 | TH/s |
| `min_hashrate_ths` | DOUBLE | N | 最小算力 | TH/s |
| `avg_temp_c` | DOUBLE | N | 平均温度 | °C |
| `max_temp_c` | DOUBLE | N | 最高温度 | °C |
| `avg_power_w` | DOUBLE | N | 平均功耗 | W |
| `avg_fan_rpm` | DOUBLE | N | 平均风扇转速 | RPM |
| `online_ratio` | DOUBLE | N | 在线率 (0-1) | ratio |
| `samples` | INTEGER | N | 样本数 | - |
| `created_at` | TIMESTAMP | N | 记录创建时间 | UTC |

### 数据口径
- `bucket_ts`: 向下取整到 5 分钟边界 (e.g., 10:05:00, 10:10:00)
- `avg_hashrate_ths`: 5 分钟内所有样本的算术平均
- `online_ratio`: 5 分钟内在线样本数 / 总样本数
- `samples`: 该时间桶内的原始数据点数

### 聚合规则
```sql
INSERT INTO telemetry_history_5min
SELECT 
    date_trunc('minute', ts) - (EXTRACT(MINUTE FROM ts)::INT % 5) * INTERVAL '1 minute' AS bucket_ts,
    site_id, miner_id,
    AVG(hashrate_ths) AS avg_hashrate_ths,
    MAX(hashrate_ths) AS max_hashrate_ths,
    MIN(hashrate_ths) AS min_hashrate_ths,
    AVG(temperature_c) AS avg_temp_c,
    MAX(temperature_c) AS max_temp_c,
    AVG(power_w) AS avg_power_w,
    AVG(fan_rpm) AS avg_fan_rpm,
    COUNT(CASE WHEN status = 'online' THEN 1 END)::FLOAT / COUNT(*) AS online_ratio,
    COUNT(*) AS samples
FROM telemetry_raw_24h
WHERE ts >= NOW() - INTERVAL '5 minutes'
GROUP BY bucket_ts, site_id, miner_id;
```

---

## 4. telemetry_daily (日聚合层)

### 定位
- **含义**: 按天聚合的统计数据
- **用途**: 报表、账单、长期趋势、MTTR/可用率统计
- **特点**: 保留 365 天以上

### 字段定义
| 字段 | 类型 | 必填 | 说明 | 单位 |
|------|------|------|------|------|
| `id` | BIGINT | Y | 主键 | - |
| `day` | DATE | Y | 日期 | - |
| `site_id` | INTEGER | Y | 站点 ID | - |
| `miner_id` | VARCHAR | Y | 矿机 ID | - |
| `avg_hashrate_ths` | DOUBLE | N | 日均算力 | TH/s |
| `max_hashrate_ths` | DOUBLE | N | 日最大算力 | TH/s |
| `min_hashrate_ths` | DOUBLE | N | 日最小算力 | TH/s |
| `avg_temp_c` | DOUBLE | N | 日均温度 | °C |
| `max_temp_c` | DOUBLE | N | 日最高温度 | °C |
| `avg_power_w` | DOUBLE | N | 日均功耗 | W |
| `total_power_kwh` | DOUBLE | N | 日总用电量 | kWh |
| `online_ratio` | DOUBLE | N | 日在线率 (0-1) | ratio |
| `uptime_hours` | DOUBLE | N | 日运行时长 | hours |
| `samples` | INTEGER | N | 日样本数 | - |
| `created_at` | TIMESTAMP | N | 记录创建时间 | UTC |

### 计算公式
```python
total_power_kwh = avg_power_w * 24 / 1000
uptime_hours = online_ratio * 24
```

---

## 统一查询 API 接口规范

### GET /api/v1/telemetry/live
实时矿机状态查询

**参数:**
- `site_id` (int, optional): 站点过滤
- `miner_id` (string, optional): 矿机过滤
- `online` (bool, optional): 在线状态过滤

**响应:**
```json
{
  "miners": [
    {
      "miner_id": "string",
      "hashrate": {"value": 100.5, "unit": "TH/s", "source": "5min_avg"},
      "temperature": {"avg": 65, "max": 72, "unit": "C"},
      "power": {"value": 3250, "unit": "W"},
      "online": true,
      "last_seen": "2026-01-26T12:00:00Z"
    }
  ],
  "_meta": {"source": "miner_telemetry_live", "updated_at": "..."}
}
```

### GET /api/v1/telemetry/history
历史趋势查询

**参数:**
- `site_id` (int, required): 站点 ID
- `miner_id` (string, optional): 矿机过滤
- `start` (datetime, required): 开始时间
- `end` (datetime, required): 结束时间
- `resolution` (string): "5min" | "hourly" | "daily"

**响应:**
```json
{
  "series": [
    {
      "miner_id": "string",
      "data": [
        {"ts": "2026-01-26T10:00:00Z", "hashrate_ths": 100.5, "temp_c": 65}
      ]
    }
  ],
  "_meta": {"source": "telemetry_history_5min", "resolution": "5min"}
}
```

---

## 数据一致性保证

### 写入规则
1. **Collector** 只负责写入 `telemetry_raw_24h`
2. **后台任务** (APScheduler) 负责:
   - 每分钟更新 `miner_telemetry_live`
   - 每 5 分钟聚合到 `telemetry_history_5min`
   - 每天聚合到 `telemetry_daily`
3. **不允许** UI 或其他服务直接写入 live/history 表

### 读取规则
1. **实时显示** 只从 `miner_telemetry_live` 读取
2. **趋势图表** 只从 `telemetry_history_5min` 或 `telemetry_daily` 读取
3. **故障排查** 可从 `telemetry_raw_24h` 读取

### 单位标准化
| 指标 | 存储单位 | 显示单位 | 转换 |
|------|----------|----------|------|
| 算力 | TH/s 或 GH/s | TH/s | 1 TH/s = 1000 GH/s |
| 温度 | °C | °C | - |
| 功耗 | W | W 或 kW | 1 kW = 1000 W |
| 拒绝率 | ratio (0-1) | % | × 100 |
| 在线率 | ratio (0-1) | % | × 100 |

---

## 数据保留策略

| 层级 | 保留时长 | 清理策略 |
|------|----------|----------|
| telemetry_raw_24h | 24 小时 | 每小时删除超过 24h 的数据 |
| miner_telemetry_live | 永久 (每矿机一条) | 自动覆盖更新 |
| telemetry_history_5min | 90 天 | 每天删除超过 90 天的数据 |
| telemetry_daily | 365 天 | 每月删除超过 365 天的数据 |
