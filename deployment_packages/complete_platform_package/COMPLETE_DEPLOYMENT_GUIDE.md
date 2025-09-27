# HashInsight Complete Mining Platform Deployment Guide
# HashInsight完整挖矿平台部署指南

## 概述 Overview

HashInsight Complete Mining Platform是一个专业的模块化挖矿管理平台，包含三个核心模块：Mining Core（挖矿核心）、Web3 Integration（区块链集成）和User Management（用户管理）。本指南将帮助您快速部署和配置完整的平台环境。

## 系统架构 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        HashInsight Mining Platform                      │
│                              v2.1.0                                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Portal   │    │  Admin Portal   │    │  API Gateway    │
│   (Frontend)    │    │   (Management)  │    │   (Port 8080)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │                           │                            │
┌───▼───────────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
│ Mining Core   │    │ Web3 Integration  │    │ User Management   │
│   Module      │    │     Module        │    │     Module        │
│ (Port 5001)   │    │   (Port 5002)     │    │   (Port 5003)     │
└───┬───────────┘    └─────────┬─────────┘    └─────────┬─────────┘
    │                          │                        │
    │                          │                        │
┌───▼──────┐    ┌──────────────▼─────────┐    ┌─────────▼─────────┐
│ Mining   │    │    Blockchain RPC      │    │   PostgreSQL     │
│Analytics │    │   (Ethereum/Bitcoin)   │    │   Database       │
│Database  │    │      & IPFS           │    │    & Redis       │
└──────────┘    └────────────────────────┘    └───────────────────┘
```

## 模块功能说明 Module Functions

### 1. Mining Core Module (挖矿核心模块)
- **端口**: 5001
- **功能**: 挖矿数据分析、性能监控、设备管理
- **主要特性**:
  - 实时挖矿数据收集
  - 性能分析和报表
  - 设备状态监控
  - 收益计算和分析

### 2. Web3 Integration Module (区块链集成模块)
- **端口**: 5002
- **功能**: 区块链交互、钱包管理、智能合约、NFT
- **主要特性**:
  - 多链钱包管理
  - 智能合约部署和交互
  - NFT铸造和管理
  - DeFi协议集成

### 3. User Management Module (用户管理模块)
- **端口**: 5003
- **功能**: 用户认证、CRM、订阅计费、权限管理
- **主要特性**:
  - 用户注册和认证
  - 基于角色的权限控制
  - CRM客户关系管理
  - 订阅和计费系统

## 快速部署 Quick Deployment

### 方法一：自动部署脚本

#### Linux/macOS
```bash
# 1. 解压部署包
unzip complete_platform_package.zip
cd complete_platform_package

# 2. 运行自动部署脚本
chmod +x deploy_all.sh
./deploy_all.sh install

# 3. 启动平台
./deploy_all.sh start
```

#### Windows
```cmd
# 1. 解压部署包
unzip complete_platform_package.zip
cd complete_platform_package

# 2. 运行自动部署脚本
deploy_all.bat install

# 3. 启动平台
deploy_all.bat start
```

### 方法二：Docker部署

```bash
# 启动完整平台栈
docker-compose -f docker-compose.full.yml up -d

# 查看服务状态
docker-compose -f docker-compose.full.yml ps

# 查看日志
docker-compose -f docker-compose.full.yml logs -f
```

## 详细部署步骤 Detailed Deployment Steps

### 1. 系统要求检查

#### 硬件要求
- **CPU**: 4核心以上
- **内存**: 8GB RAM (最低4GB)
- **存储**: 50GB可用空间 (SSD推荐)
- **网络**: 稳定的互联网连接

#### 软件要求
- **操作系统**: Linux (Ubuntu 20.04+), macOS 10.15+, Windows 10+
- **Python**: 3.8或更高版本
- **Node.js**: 16.0+ (用于智能合约)
- **数据库**: PostgreSQL 12+ (推荐) 或 SQLite
- **缓存**: Redis 6.0+
- **Web服务器**: Nginx (可选，用于生产环境)

### 2. 环境配置

#### 数据库配置
```bash
# PostgreSQL安装 (Ubuntu)
sudo apt update
sudo apt install postgresql postgresql-contrib

# 创建数据库和用户
sudo -u postgres psql
CREATE DATABASE mining_platform_db;
CREATE USER platform_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mining_platform_db TO platform_user;
\q
```

#### Redis配置
```bash
# Redis安装 (Ubuntu)
sudo apt install redis-server

# 启动Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### 3. 模块配置

每个模块都需要独立配置，编辑对应的`.env`文件：

#### Mining Core Module (.env)
```env
# 基础配置
FLASK_ENV=production
DATABASE_URL=postgresql://platform_user:secure_password@localhost:5432/mining_platform_db
SESSION_SECRET=your-mining-core-secret-key

# 挖矿池配置
MINING_POOL_URL=stratum+tcp://pool.example.com:4444
MINING_POOL_USERNAME=your_pool_username
MINING_POOL_PASSWORD=your_pool_password

# 监控配置
MONITORING_ENABLED=true
MONITORING_INTERVAL=30
ALERT_EMAIL=admin@yourcompany.com
```

#### Web3 Integration Module (.env)
```env
# 基础配置
FLASK_ENV=production
DATABASE_URL=postgresql://platform_user:secure_password@localhost:5432/mining_platform_db
SESSION_SECRET=your-web3-secret-key

# 区块链配置
ETHEREUM_RPC_URL=https://mainnet.infura.io/v3/your-project-id
PRIVATE_KEY=0xYourPrivateKeyHere
CHAIN_ID=1

# IPFS配置
IPFS_PROJECT_ID=your-ipfs-project-id
IPFS_PROJECT_SECRET=your-ipfs-project-secret
```

#### User Management Module (.env)
```env
# 基础配置
FLASK_ENV=production
DATABASE_URL=postgresql://platform_user:secure_password@localhost:5432/mining_platform_db
SESSION_SECRET=your-user-mgmt-secret-key

# 邮件配置
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Redis配置
REDIS_URL=redis://localhost:6379/0

# JWT配置
JWT_SECRET_KEY=your-jwt-secret-key
```

### 4. 启动和验证

#### 启动服务
```bash
# 使用部署脚本启动
./deploy_all.sh start

# 或者手动启动各模块
cd mining_core_module && python main.py &
cd web3_integration_module && python main.py &
cd user_management_module && python main.py &
```

#### 验证服务
```bash
# 检查服务状态
curl http://localhost:5001/health  # Mining Core
curl http://localhost:5002/health  # Web3 Integration  
curl http://localhost:5003/health  # User Management

# 或使用部署脚本检查
./deploy_all.sh health
```

## 生产环境配置 Production Configuration

### 1. Nginx反向代理配置

```nginx
# /etc/nginx/sites-available/hashinsight-platform
server {
    listen 80;
    server_name your-domain.com;
    
    # SSL重定向
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL配置
    ssl_certificate /path/to/your/cert.pem;
    ssl_certificate_key /path/to/your/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
    
    # API路由
    location /api/mining/ {
        proxy_pass http://127.0.0.1:5001/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/web3/ {
        proxy_pass http://127.0.0.1:5002/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/users/ {
        proxy_pass http://127.0.0.1:5003/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # 默认路由到用户管理模块
    location / {
        proxy_pass http://127.0.0.1:5003/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. Systemd服务配置

为每个模块创建systemd服务文件：

```ini
# /etc/systemd/system/hashinsight-mining-core.service
[Unit]
Description=HashInsight Mining Core Module
After=network.target postgresql.service

[Service]
Type=exec
User=hashinsight
Group=hashinsight
WorkingDirectory=/opt/hashinsight/mining_core_module
Environment=PATH=/opt/hashinsight/mining_core_module/venv/bin
ExecStart=/opt/hashinsight/mining_core_module/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 4 main:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

类似地为其他模块创建服务文件。

### 3. 监控和日志

#### Logrotate配置
```bash
# /etc/logrotate.d/hashinsight-platform
/opt/hashinsight/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 hashinsight hashinsight
    postrotate
        systemctl reload hashinsight-*
    endscript
}
```

#### 监控配置
```bash
# 安装监控工具
sudo apt install htop iotop

# 创建监控脚本
cat > /opt/hashinsight/scripts/monitor.sh << 'EOF'
#!/bin/bash
# 平台监控脚本

check_service() {
    if systemctl is-active --quiet $1; then
        echo "$1 is running"
    else
        echo "$1 is not running" >&2
        systemctl restart $1
    fi
}

check_service hashinsight-mining-core
check_service hashinsight-web3-integration
check_service hashinsight-user-management
EOF

# 添加到crontab
echo "*/5 * * * * /opt/hashinsight/scripts/monitor.sh" | crontab -
```

## 安全配置 Security Configuration

### 1. 防火墙设置
```bash
# UFW配置
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 2. 数据库安全
```sql
-- PostgreSQL安全配置
ALTER USER platform_user SET default_transaction_isolation TO 'read committed';
ALTER USER platform_user SET timezone TO 'UTC';
ALTER USER platform_user SET client_encoding TO 'utf8';

-- 限制连接
ALTER USER platform_user CONNECTION LIMIT 20;
```

### 3. SSL/TLS配置
```bash
# 使用Let's Encrypt获取SSL证书
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## 备份和恢复 Backup & Recovery

### 1. 数据库备份
```bash
# 创建备份脚本
cat > /opt/hashinsight/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/hashinsight/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# 数据库备份
pg_dump -U platform_user -h localhost mining_platform_db > $BACKUP_DIR/db_backup_$DATE.sql

# 压缩备份
gzip $BACKUP_DIR/db_backup_$DATE.sql

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
EOF

# 添加到crontab (每天凌晨2点)
echo "0 2 * * * /opt/hashinsight/scripts/backup.sh" | crontab -
```

### 2. 配置文件备份
```bash
# 备份配置文件
tar -czf /opt/hashinsight/backups/config_backup_$(date +%Y%m%d).tar.gz \
    mining_core_module/.env \
    web3_integration_module/.env \
    user_management_module/.env \
    nginx/sites-available/hashinsight-platform
```

## 性能优化 Performance Optimization

### 1. 数据库优化
```sql
-- PostgreSQL性能调优
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
SELECT pg_reload_conf();
```

### 2. Redis优化
```bash
# Redis配置优化
echo "maxmemory 512mb" >> /etc/redis/redis.conf
echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
sudo systemctl restart redis-server
```

### 3. 应用优化
```bash
# Gunicorn工作进程优化
workers = (2 * cpu_cores) + 1
worker_class = 'gevent'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
```

## 故障排除 Troubleshooting

### 常见问题

#### 1. 服务启动失败
```bash
# 检查日志
journalctl -u hashinsight-mining-core -f
tail -f /opt/hashinsight/logs/mining_core.log

# 检查端口占用
sudo netstat -tlnp | grep :5001
```

#### 2. 数据库连接失败
```bash
# 测试数据库连接
psql -U platform_user -h localhost -d mining_platform_db

# 检查PostgreSQL状态
sudo systemctl status postgresql
```

#### 3. Web3连接问题
```bash
# 测试RPC连接
curl -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","id":1}' \
  -H "Content-Type: application/json" $ETHEREUM_RPC_URL
```

#### 4. 邮件发送失败
```bash
# 测试SMTP连接
python3 -c "
import smtplib
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('your-email@gmail.com', 'your-app-password')
server.quit()
print('SMTP connection successful')
"
```

## 扩展和升级 Scaling & Upgrading

### 1. 水平扩展
```yaml
# Docker Swarm配置示例
version: '3.8'
services:
  mining-core:
    image: hashinsight/mining-core:latest
    deploy:
      replicas: 3
      placement:
        constraints:
          - node.role == worker
```

### 2. 负载均衡
```nginx
upstream mining_core_backend {
    server 127.0.0.1:5001;
    server 127.0.0.1:5011;
    server 127.0.0.1:5021;
}
```

### 3. 版本升级
```bash
# 升级脚本
#!/bin/bash
# 停止服务
sudo systemctl stop hashinsight-*

# 备份当前版本
tar -czf /opt/hashinsight/backups/platform_backup_$(date +%Y%m%d).tar.gz /opt/hashinsight/

# 部署新版本
tar -xzf hashinsight-platform-v2.2.0.tar.gz -C /opt/hashinsight/

# 数据库迁移
cd /opt/hashinsight && alembic upgrade head

# 启动服务
sudo systemctl start hashinsight-*
```

## 许可证和支持 License & Support

### 许可证
本平台采用MIT许可证，详见各模块的LICENSE文件。

### 技术支持
- 📧 **Email**: support@hashinsight.net
- 💬 **Discord**: https://discord.gg/hashinsight
- 📖 **文档**: https://docs.hashinsight.net
- 🔧 **GitHub**: https://github.com/hashinsight

### 社区
- 📝 **博客**: https://blog.hashinsight.net
- 🎥 **视频教程**: https://youtube.com/hashinsight
- 📰 **新闻**: https://news.hashinsight.net

---

**HashInsight Complete Mining Platform v2.1.0**  
© 2025 HashInsight Technologies. All rights reserved.