# 📦 Miner Agent 部署运维指南

## 📋 文档信息

- **版本**: 1.0.0
- **日期**: 2025-10-13
- **适用环境**: Linux (Ubuntu 20.04+), CentOS 7+, Debian 10+

---

## 🎯 部署目标

部署 Miner Agent 到矿场本地网络，实现:
- ✅ 自动采集矿机遥测数据
- ✅ 实时上报到云端平台
- ✅ 接收和执行远程控制指令
- ✅ 断线重连和数据缓冲

---

## 📋 环境要求

### 硬件要求

| 部署方式 | 最低配置 | 推荐配置 |
|---------|---------|---------|
| **服务器/工控机** | 1核 CPU, 1GB RAM, 10GB 存储 | 2核 CPU, 2GB RAM, 20GB 存储 |
| **树莓派** | Raspberry Pi 3B+ | Raspberry Pi 4B (2GB+) |
| **路由器** | OpenWRT 支持 Python 3.8+ | 不推荐（资源受限） |

### 软件要求

| 软件 | 版本 | 说明 |
|------|------|------|
| **操作系统** | Ubuntu 20.04+ / CentOS 7+ | 64位 Linux |
| **Python** | 3.8+ | 必须 |
| **systemd** | - | 用于进程管理 |
| **网络** | - | 可访问公网 (HTTPS 出站) |

### 网络要求

#### 出站连接
```
HTTPS (443) → hashinsight.replit.app
带宽: 最低 1 Mbps (推荐 10 Mbps)
```

#### 内网访问
```
TCP 4028 → 所有矿机 (CGMiner API)
无需公网 IP
无需端口映射
```

---

## 🚀 快速部署

### 方法 1: 官方安装包 (推荐)

```bash
# 1. 下载官方发布包（带GPG签名和SHA256校验和）
wget https://hashinsight.replit.app/releases/v1.0.0/miner-agent-v1.0.0.tar.gz
wget https://hashinsight.replit.app/releases/v1.0.0/miner-agent-v1.0.0.tar.gz.asc
wget https://hashinsight.replit.app/releases/v1.0.0/miner-agent-v1.0.0.tar.gz.sha256

# 2. 下载并导入GPG公钥
wget https://hashinsight.replit.app/keys/release-signing-key.asc
gpg --import release-signing-key.asc

# 3. 验证GPG签名
gpg --verify miner-agent-v1.0.0.tar.gz.asc miner-agent-v1.0.0.tar.gz
# 预期输出: "Good signature from 'HashInsight Release Signing Key'"

# 4. 验证SHA256校验和
sha256sum -c miner-agent-v1.0.0.tar.gz.sha256
# 预期输出: "miner-agent-v1.0.0.tar.gz: OK"

# 5. 解压（仅在验证通过后）
sudo tar -xzf miner-agent-v1.0.0.tar.gz -C /opt/
cd /opt/miner-agent

# 6. 运行安装脚本
sudo ./install.sh
```

**安全验证说明：**
- GPG签名验证确保包来自官方，未被篡改
- SHA256校验和验证确保下载过程中没有损坏
- 只有验证通过后才能安装

### 方法 2: 手动安装

#### 步骤 1: 安装 Python 3.8+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
python3 --version  # 确认版本 >= 3.8
```

**CentOS/RHEL:**
```bash
sudo yum install -y python3 python3-pip
python3 --version
```

#### 步骤 2: 创建工作目录

```bash
sudo mkdir -p /opt/miner-agent
cd /opt/miner-agent
```

#### 步骤 3: 下载 Agent 程序

```bash
# 方式 A: 从云端下载
curl -sSL https://hashinsight.replit.app/agent/download -o miner_agent.py

# 方式 B: 从 GitHub 下载
git clone https://github.com/hashinsight/miner-agent.git
cd miner-agent
```

#### 步骤 4: 安装 Python 依赖

```bash
# 安装依赖
pip3 install requests configparser

# 或使用 requirements.txt
pip3 install -r requirements.txt
```

#### 步骤 5: 配置 Agent

```bash
# 复制配置文件模板
cp agent_config.ini.example agent_config.ini

# 编辑配置文件
nano agent_config.ini
```

**必填配置项：**
```ini
[agent]
agent_id = <从管理员获取>
access_token = <从管理员获取>

[cloud]
api_base_url = https://hashinsight.replit.app/agent/api

[miners]
ip_list = 192.168.1.100,192.168.1.101,192.168.1.102
```

#### 步骤 6: 测试运行

```bash
# 前台运行测试
python3 miner_agent.py --config agent_config.ini

# 观察输出，确认：
# - Agent 成功连接到云端
# - 能够采集矿机数据
# - 心跳正常发送
```

**预期输出：**
```
2025-10-13 10:00:00 - MinerAgent - INFO - Starting Miner Agent v1.0.0
2025-10-13 10:00:00 - MinerAgent - INFO - Agent ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
2025-10-13 10:00:00 - MinerAgent - INFO - Monitoring 3 miners
2025-10-13 10:00:01 - MinerAgent - DEBUG - Heartbeat sent successfully
2025-10-13 10:00:05 - MinerAgent - INFO - Collected data from 3/3 miners
2025-10-13 10:00:06 - MinerAgent - INFO - Telemetry data sent successfully
```

#### 步骤 7: 配置 systemd 服务

创建服务文件：
```bash
sudo nano /etc/systemd/system/miner-agent.service
```

内容：
```ini
[Unit]
Description=HashInsight Miner Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/miner-agent
ExecStart=/usr/bin/python3 /opt/miner-agent/miner_agent.py --config /opt/miner-agent/agent_config.ini
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable miner-agent

# 启动服务
sudo systemctl start miner-agent

# 检查状态
sudo systemctl status miner-agent
```

---

## 🔧 配置详解

### 完整配置文件示例

```ini
[agent]
# Agent 唯一标识（必填）
agent_id = a1b2c3d4-e5f6-7890-abcd-ef1234567890

# 访问令牌（必填，仅在创建时显示一次）
access_token = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

[cloud]
# 云端 API 地址（必填）
api_base_url = https://hashinsight.replit.app/agent/api

# API 请求超时（可选，默认30秒）
api_timeout = 30

[miners]
# 矿机 IP 地址列表（必填，逗号分隔）
ip_list = 192.168.1.100,192.168.1.101,192.168.1.102

# 也可以使用 IP 段自动扫描（高级功能，暂未实现）
# ip_range = 192.168.1.100-192.168.1.200

[settings]
# 数据采集间隔（秒，默认60）
collection_interval = 60

# 心跳间隔（秒，默认30）
heartbeat_interval = 30

# CGMiner API 超时（秒，默认5）
cgminer_timeout = 5

# 最大数据缓冲数量（默认10000）
max_buffer_size = 10000

# 最大数据缓冲时长（小时，默认24）
max_buffer_hours = 24

[logging]
# 日志级别（DEBUG/INFO/WARNING/ERROR，默认INFO）
log_level = INFO

# 日志文件路径（默认 miner_agent.log）
log_file = /var/log/miner-agent/agent.log

# 日志文件最大大小（MB，默认10）
log_max_size = 10

# 日志文件保留数量（默认5）
log_backup_count = 5
```

---

## 📊 运维管理

### 服务管理

```bash
# 启动服务
sudo systemctl start miner-agent

# 停止服务
sudo systemctl stop miner-agent

# 重启服务
sudo systemctl restart miner-agent

# 查看状态
sudo systemctl status miner-agent

# 查看实时日志
sudo journalctl -u miner-agent -f

# 查看最近100行日志
sudo journalctl -u miner-agent -n 100

# 查看今天的日志
sudo journalctl -u miner-agent --since today
```

### 日志管理

**日志位置：**
```
systemd 日志: /var/log/syslog 或 journalctl
应用日志: /opt/miner-agent/miner_agent.log
```

**查看日志：**
```bash
# 查看应用日志
tail -f /opt/miner-agent/miner_agent.log

# 过滤错误日志
grep ERROR /opt/miner-agent/miner_agent.log

# 过滤心跳日志
grep Heartbeat /opt/miner-agent/miner_agent.log
```

**日志轮转：**
```bash
# 配置 logrotate
sudo nano /etc/logrotate.d/miner-agent
```

内容：
```
/opt/miner-agent/miner_agent.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    postrotate
        systemctl reload miner-agent > /dev/null 2>&1 || true
    endscript
}
```

### 配置更新

```bash
# 1. 编辑配置文件
sudo nano /opt/miner-agent/agent_config.ini

# 2. 重启服务使配置生效
sudo systemctl restart miner-agent

# 3. 检查状态
sudo systemctl status miner-agent
```

### 版本升级

```bash
# 1. 停止服务
sudo systemctl stop miner-agent

# 2. 备份当前版本
sudo cp /opt/miner-agent/miner_agent.py /opt/miner-agent/miner_agent.py.backup

# 3. 下载新版本
cd /opt/miner-agent
sudo curl -sSL https://hashinsight.replit.app/agent/download -o miner_agent.py

# 4. 启动服务
sudo systemctl start miner-agent

# 5. 检查版本
sudo journalctl -u miner-agent -n 10 | grep "Starting Miner Agent"
```

---

## 🔍 故障排查

### 常见问题

#### 1. Agent 无法启动

**症状：**
```bash
sudo systemctl status miner-agent
# 显示 failed
```

**排查步骤：**
```bash
# 查看详细错误
sudo journalctl -u miner-agent -n 50

# 手动运行查看错误
cd /opt/miner-agent
python3 miner_agent.py --config agent_config.ini
```

**常见原因：**
- 配置文件路径错误
- agent_id 或 access_token 缺失
- Python 版本不兼容
- 缺少依赖库

#### 2. 无法连接到云端

**症状：**
```
Heartbeat failed - entering offline mode
```

**排查步骤：**
```bash
# 测试网络连接
curl -I https://hashinsight.replit.app

# 测试 API 连接
curl -H "Authorization: Bearer <your_token>" \
     https://hashinsight.replit.app/agent/api/auth/verify

# 检查防火墙
sudo iptables -L -n | grep 443
```

**常见原因：**
- 防火墙阻止 HTTPS 出站
- 网络不稳定
- Token 已过期
- API 地址配置错误

#### 3. 无法采集矿机数据

**症状：**
```
Collected data from 0/10 miners
```

**排查步骤：**
```bash
# 测试 CGMiner API 连接
nc -zv 192.168.1.100 4028

# 手动调用 CGMiner API
echo '{"command":"summary"}' | nc 192.168.1.100 4028

# 检查矿机 IP 是否可达
ping -c 3 192.168.1.100
```

**常见原因：**
- 矿机 IP 地址错误
- CGMiner API 未启用
- 网络隔离（Agent 与矿机不在同一网段）
- 矿机端口 4028 被防火墙阻止

#### 4. 数据缓冲区满

**症状：**
```
Buffer size: 10000 (max reached)
```

**解决方案：**
```bash
# 1. 检查云端连接
sudo journalctl -u miner-agent -n 100 | grep "Heartbeat"

# 2. 如果长时间离线，清空缓冲区
sudo systemctl stop miner-agent
sudo rm -f /opt/miner-agent/data_buffer.json  # 如果有缓冲文件
sudo systemctl start miner-agent

# 3. 增大缓冲区大小（修改配置）
# max_buffer_size = 50000
```

---

## 📈 监控和告警

### 1. 健康检查脚本

创建健康检查脚本：
```bash
sudo nano /opt/miner-agent/health_check.sh
```

内容：
```bash
#!/bin/bash

# 检查服务状态
if ! systemctl is-active --quiet miner-agent; then
    echo "CRITICAL: Miner Agent is not running"
    # 发送告警（可集成到监控系统）
    exit 2
fi

# 检查最近心跳时间
last_heartbeat=$(journalctl -u miner-agent --since "2 minutes ago" | grep "Heartbeat sent successfully" | tail -1)
if [ -z "$last_heartbeat" ]; then
    echo "WARNING: No heartbeat in last 2 minutes"
    exit 1
fi

echo "OK: Miner Agent is healthy"
exit 0
```

添加到 cron：
```bash
# 每5分钟检查一次
*/5 * * * * /opt/miner-agent/health_check.sh
```

### 2. Prometheus 监控（可选）

Agent 可以暴露 Prometheus 指标：

```python
# 在 miner_agent.py 中添加
from prometheus_client import start_http_server, Counter, Gauge

# 定义指标
heartbeat_count = Counter('agent_heartbeat_total', 'Total heartbeats sent')
miners_online = Gauge('agent_miners_online', 'Number of online miners')
data_buffer_size = Gauge('agent_buffer_size', 'Data buffer size')

# 启动 Prometheus HTTP 服务器
start_http_server(9090)
```

Prometheus 配置：
```yaml
scrape_configs:
  - job_name: 'miner-agent'
    static_configs:
      - targets: ['<agent-ip>:9090']
```

---

## 🔒 安全最佳实践

### 1. Token 管理

```bash
# Token 应保密，建议使用环境变量
export AGENT_ACCESS_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 配置文件中引用环境变量
access_token = ${AGENT_ACCESS_TOKEN}

# 限制配置文件权限
sudo chmod 600 /opt/miner-agent/agent_config.ini
sudo chown root:root /opt/miner-agent/agent_config.ini
```

### 2. 网络隔离

```bash
# 使用防火墙限制出站连接
sudo ufw allow out 443/tcp to hashinsight.replit.app

# 限制 CGMiner API 访问（仅允许 Agent 访问）
# 在矿机端配置防火墙
iptables -A INPUT -p tcp --dport 4028 -s <agent-ip> -j ACCEPT
iptables -A INPUT -p tcp --dport 4028 -j DROP
```

### 3. 日志脱敏

```python
# 在日志中隐藏敏感信息
def sanitize_log(message):
    # 隐藏 Token
    message = re.sub(r'Bearer [\w\.\-]+', 'Bearer ***', message)
    # 隐藏 IP 后两段
    message = re.sub(r'(\d+\.\d+)\.\d+\.\d+', r'\1.***', message)
    return message
```

---

## 🧪 测试和验证

### 功能测试清单

```bash
# 1. Agent 注册验证
python3 miner_agent.py --config agent_config.ini
# 预期：成功连接到云端，日志显示 "Starting Miner Agent"

# 2. 心跳测试
# 预期：每30秒显示 "Heartbeat sent successfully"

# 3. 数据采集测试
# 预期：每60秒显示 "Collected data from X/Y miners"

# 4. 数据上报测试
# 预期：显示 "Telemetry data sent successfully"

# 5. 离线恢复测试
# 断开网络 → 等待5分钟 → 恢复网络
# 预期：显示 "Flushing X buffered data points"

# 6. 控制指令测试
# 在云端下发重启指令
# 预期：Agent 接收并执行指令，上报执行结果
```

---

## 📦 备份和恢复

### 备份

```bash
# 备份配置文件
sudo cp /opt/miner-agent/agent_config.ini \
       /opt/miner-agent/agent_config.ini.backup.$(date +%Y%m%d)

# 备份日志
sudo tar -czf /opt/miner-agent/logs_backup_$(date +%Y%m%d).tar.gz \
       /opt/miner-agent/*.log
```

### 恢复

```bash
# 恢复配置文件
sudo cp /opt/miner-agent/agent_config.ini.backup.20251013 \
       /opt/miner-agent/agent_config.ini

# 重启服务
sudo systemctl restart miner-agent
```

---

## 🚀 高级部署

### Docker 部署（可选）

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY miner_agent.py .
COPY agent_config.ini .

# 运行
CMD ["python", "miner_agent.py"]
```

**构建和运行:**
```bash
# 构建镜像
docker build -t miner-agent:1.0.0 .

# 运行容器
docker run -d \
  --name miner-agent \
  --restart always \
  --network host \
  -v /opt/miner-agent/agent_config.ini:/app/agent_config.ini:ro \
  miner-agent:1.0.0

# 查看日志
docker logs -f miner-agent
```

### 多矿场部署

```bash
# 矿场 A
/opt/miner-agent-a/
├── miner_agent.py
├── agent_config.ini (agent_id = site-a-agent)
└── systemd service: miner-agent-a.service

# 矿场 B
/opt/miner-agent-b/
├── miner_agent.py
├── agent_config.ini (agent_id = site-b-agent)
└── systemd service: miner-agent-b.service
```

---

## 📚 常用命令速查

```bash
# 服务管理
systemctl start miner-agent      # 启动
systemctl stop miner-agent       # 停止
systemctl restart miner-agent    # 重启
systemctl status miner-agent     # 状态

# 日志查看
journalctl -u miner-agent -f     # 实时日志
journalctl -u miner-agent -n 100 # 最近100行
tail -f miner_agent.log          # 应用日志

# 测试
python3 miner_agent.py           # 前台运行
nc -zv <ip> 4028                 # 测试CGMiner连接
curl -I https://hashinsight.replit.app  # 测试云端连接

# 配置
nano agent_config.ini            # 编辑配置
systemctl daemon-reload          # 重载systemd
```

---

## 📞 支持和联系

**问题反馈：**
- Email: support@hashinsight.com
- 工单系统: https://hashinsight.replit.app/support

**文档更新：**
- 架构设计: [miner_agent_architecture.md](./miner_agent_architecture.md)
- 数据库设计: [miner_agent_database.md](./miner_agent_database.md)
- API 规范: [miner_agent_api.md](./miner_agent_api.md)

---

**文档版本**: v1.0.0  
**最后更新**: 2025-10-13
