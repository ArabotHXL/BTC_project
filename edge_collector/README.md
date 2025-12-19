# HashInsight Edge Collector - 矿场边缘数据采集器

## 概述

Edge Collector 是一个部署在矿场本地的数据采集程序，通过 CGMiner API (端口4028) 实时采集矿机运行数据，并上传到 HashInsight 云端平台。

## 系统架构

```
矿场内网                              云端 (HashInsight)
┌─────────────────────┐              ┌─────────────────────┐
│  矿机 x 6000+       │              │  /api/collector/    │
│  (S19/S21/M30等)    │              │  upload             │
│        │            │              │        │            │
│        ▼            │   HTTPS      │        ▼            │
│  ┌─────────────┐    │  ────────>   │  ┌─────────────┐    │
│  │Edge Collector│   │              │  │ PostgreSQL  │    │
│  │ (本程序)     │   │              │  │ + Redis     │    │
│  └─────────────┘    │              │  └─────────────┘    │
└─────────────────────┘              └─────────────────────┘
```

## 功能特性

- ✅ 支持 Antminer S19/S21/T19 系列
- ✅ 支持 Whatsminer M30/M50 系列  
- ✅ 支持 Avalon 系列
- ✅ 批量采集 6000+ 矿机 (50并发)
- ✅ 数据 gzip 压缩传输
- ✅ 断网自动缓存，恢复后重传
- ✅ 采集间隔可配置 (默认30秒)

## 采集数据

| 数据项 | 说明 |
|--------|------|
| hashrate_ghs | 平均算力 (GH/s) |
| hashrate_5s_ghs | 5秒实时算力 |
| temperature_avg | 平均温度 |
| temperature_max | 最高温度 |
| temperature_chips | 各芯片温度 |
| fan_speeds | 风扇转速 |
| frequency_avg | 平均频率 |
| accepted_shares | 接受份额 |
| rejected_shares | 拒绝份额 |
| hardware_errors | 硬件错误 |
| uptime_seconds | 运行时间 |
| pool_url | 矿池地址 |
| worker_name | 矿工名称 |

## 部署指南

### 1. 系统要求

- Python 3.8+
- 网络可访问矿机 (端口 4028)
- 可访问互联网 (HTTPS)

### 2. 安装

```bash
# 克隆或下载 edge_collector 目录
cd edge_collector

# 安装依赖 (仅需 requests)
pip install requests

# 创建配置文件
python cgminer_collector.py --init
```

### 3. 配置

编辑 `collector_config.json`:

```json
{
    "api_url": "https://your-app.replit.app",
    "api_key": "hsc_xxxxx",
    "site_id": "site_001",
    "collection_interval": 30,
    "max_workers": 50,
    "miners": [
        {"id": "S19_0001", "ip": "192.168.1.100", "type": "antminer"},
        {"id": "S19_0002", "ip": "192.168.1.101", "type": "antminer"}
    ],
    "ip_ranges": [
        {"range": "192.168.1.100-192.168.1.199", "prefix": "S19_", "type": "antminer"},
        {"range": "192.168.2.100-192.168.2.199", "prefix": "M30_", "type": "whatsminer"}
    ]
}
```

#### 配置说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| api_url | HashInsight 云端地址 | 必填 |
| api_key | 采集器API密钥 (从平台获取) | 必填 |
| site_id | 矿场站点ID | 必填 |
| collection_interval | 采集间隔 (秒) | 30 |
| max_workers | 并发采集数 | 50 |
| miners | 矿机列表 | [] |
| ip_ranges | IP范围批量生成 | [] |

### 4. 获取API密钥

1. 登录 HashInsight 平台
2. 进入 托管管理 → 站点管理
3. 选择站点 → 采集器设置
4. 点击 "生成新密钥"
5. 复制密钥到配置文件

### 5. 测试连接

```bash
# 测试单个矿机连接
python cgminer_collector.py --test 192.168.1.100

# 单次采集测试
python cgminer_collector.py --once
```

### 6. 运行

```bash
# 前台运行
python cgminer_collector.py

# 后台运行 (Linux)
nohup python cgminer_collector.py > collector.log 2>&1 &

# 使用 systemd (推荐)
sudo cp hashinsight-collector.service /etc/systemd/system/
sudo systemctl enable hashinsight-collector
sudo systemctl start hashinsight-collector
```

## Systemd 服务配置

创建 `/etc/systemd/system/hashinsight-collector.service`:

```ini
[Unit]
Description=HashInsight Edge Collector
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hashinsight-collector
ExecStart=/usr/bin/python3 cgminer_collector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY cgminer_collector.py .
COPY collector_config.json .

RUN pip install requests

CMD ["python", "cgminer_collector.py"]
```

```bash
docker build -t hashinsight-collector .
docker run -d --name collector \
  -v $(pwd)/collector_config.json:/app/collector_config.json \
  -v $(pwd)/cache:/app/cache \
  hashinsight-collector
```

## 故障排查

### 矿机连接失败

```bash
# 检查矿机API是否开启
telnet 192.168.1.100 4028

# 检查防火墙
iptables -L -n | grep 4028
```

### 上传失败

检查:
1. API密钥是否正确
2. 网络是否可访问云端
3. 查看缓存目录 `./cache/` 是否有待上传数据

### 日志位置

- 控制台输出: 实时日志
- 离线缓存: `./cache/offline_cache.db`

## 性能优化

| 矿机数量 | 推荐 max_workers | 采集周期 |
|---------|-----------------|---------|
| < 100 | 20 | 30s |
| 100-500 | 30 | 30s |
| 500-2000 | 50 | 30s |
| 2000-6000 | 100 | 60s |
| > 6000 | 150 | 60s |

## API 参考

### CGMiner API 命令

| 命令 | 说明 |
|------|------|
| summary | 算力、份额统计 |
| stats | 温度、频率详情 |
| pools | 矿池连接状态 |
| devs | 设备列表 |
| version | 固件版本 |

### 云端 API

| 端点 | 方法 | 说明 |
|------|------|------|
| /api/collector/upload | POST | 上传遥测数据 |
| /api/collector/status | GET | 采集器状态 |
| /api/collector/summary/{site_id} | GET | 站点汇总统计 |
| /api/collector/monitor/sites/{site_id}/miners/latest | GET | 最新矿机列表 (分页) |
| /api/collector/monitor/sites/{site_id}/miners/{miner_id}/history | GET | 矿机历史数据 |

### Upload Response Format

```json
{
  "success": true,
  "inserted": 5,
  "updated": 95,
  "data": {
    "processed": 100,
    "inserted": 5,
    "updated": 95,
    "online": 98,
    "offline": 2,
    "processing_time_ms": 125
  }
}
```

## curl 测试示例

### JSON 上传 (明文)

```bash
curl -X POST "https://calc.hashinsight.net/api/collector/upload" \
  -H "X-Collector-Key: hsc_your-api-key" \
  -H "X-Site-ID: 1" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "miner_id": "miner-001",
      "ip_address": "192.168.1.101",
      "online": true,
      "hashrate_ghs": 140000,
      "temperature_avg": 65,
      "temperature_max": 72,
      "fan_speeds": [4500, 4600],
      "power_consumption": 3250,
      "accepted_shares": 12500,
      "rejected_shares": 15,
      "uptime_seconds": 86400
    }
  ]'
```

### Gzip 压缩上传

```bash
# 创建测试数据
echo '[{"miner_id":"miner-001","ip_address":"192.168.1.101","online":true,"hashrate_ghs":140000,"temperature_avg":65}]' > /tmp/telemetry.json

# 压缩并上传
gzip -c /tmp/telemetry.json | curl -X POST "https://calc.hashinsight.net/api/collector/upload" \
  -H "X-Collector-Key: hsc_your-api-key" \
  -H "X-Site-ID: 1" \
  -H "Content-Type: application/gzip" \
  -H "Content-Encoding: gzip" \
  --data-binary @-
```

### 批量上传多台矿机

```bash
curl -X POST "https://calc.hashinsight.net/api/collector/upload" \
  -H "X-Collector-Key: hsc_your-api-key" \
  -H "X-Site-ID: 1" \
  -H "Content-Type: application/json" \
  -d '[
    {"miner_id":"rack1-001","ip_address":"10.0.1.1","online":true,"hashrate_ghs":140000,"temperature_max":68},
    {"miner_id":"rack1-002","ip_address":"10.0.1.2","online":true,"hashrate_ghs":138500,"temperature_max":71},
    {"miner_id":"rack1-003","ip_address":"10.0.1.3","online":false,"hashrate_ghs":0}
  ]'
```

### 查询站点汇总

```bash
curl "https://calc.hashinsight.net/api/collector/summary/1" \
  -H "X-Collector-Key: hsc_your-api-key"
```

### 查询矿机列表

```bash
curl "https://calc.hashinsight.net/api/collector/monitor/sites/1/miners/latest?page=1&per_page=50&online_only=true"
```

### 查询矿机历史数据

```bash
# 查询算力历史 (最近24小时)
curl "https://calc.hashinsight.net/api/collector/monitor/sites/1/miners/miner-001/history?metric=hashrate_ghs&hours=24"

# 查询温度历史
curl "https://calc.hashinsight.net/api/collector/monitor/sites/1/miners/miner-001/history?metric=temperature_max&hours=12"
```

## 监控页面

访问实时监控仪表板：
```
https://calc.hashinsight.net/monitor/<site_id>
```

功能：
- 矿机实时状态表格 (支持在线/离线筛选)
- 点击矿机查看历史图表
- 多指标支持: 算力、温度、风扇转速、功耗
- 时间范围: 6小时、12小时、24小时、48小时、7天
- 自动刷新 (30秒)

## 支持

如有问题，请联系技术支持或提交 Issue。

---

版本: 1.0.0  
更新: 2024-11
