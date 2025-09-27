# Mining Core Module 挖矿核心模块

## 概述 Overview

Mining Core Module是一个专业的比特币挖矿收益计算和分析平台，提供实时挖矿数据分析、收益预测、批量计算等核心功能。该模块专注于挖矿算力分析，不包含用户管理功能，可以独立部署使用。

The Mining Core Module is a professional Bitcoin mining profitability calculation and analysis platform that provides real-time mining data analysis, profit forecasting, batch calculation and other core functions. This module focuses on mining hashrate analysis without user management features and can be deployed independently.

## 主要功能 Key Features

- ⚡ **实时挖矿计算器** - 基于最新网络难度和比特币价格计算挖矿收益
- 📊 **高级分析引擎** - 多种算法分析挖矿数据和市场趋势
- 📈 **批量计算处理** - 支持大规模矿机数据批量分析
- 🔄 **实时数据同步** - 自动获取最新的网络难度、价格等数据
- 📋 **专业报告生成** - 生成详细的挖矿分析报告
- 🌐 **RESTful API** - 完整的API接口支持第三方集成
- 📱 **响应式界面** - 现代化的Web界面，支持移动设备

## 系统要求 System Requirements

### 最低要求 Minimum Requirements
- **操作系统**: Linux (Ubuntu 20.04+), macOS 10.15+, Windows 10+
- **Python**: 3.8 或更高版本
- **内存**: 2GB RAM
- **存储**: 5GB 可用空间
- **网络**: 稳定的互联网连接

### 推荐配置 Recommended Configuration
- **操作系统**: Linux (Ubuntu 22.04 LTS)
- **Python**: 3.11+
- **内存**: 4GB+ RAM
- **存储**: 20GB+ SSD
- **CPU**: 2+ 核心
- **数据库**: PostgreSQL 15+

## 快速开始 Quick Start

### 1. 下载和解压
```bash
# 下载部署包
# Download deployment package
wget https://your-domain.com/mining_core_package.zip

# 解压
# Extract
unzip mining_core_package.zip
cd mining_core_package
```

### 2. 配置环境
```bash
# 复制配置模板
# Copy configuration template
cp config.env.template .env

# 编辑配置文件
# Edit configuration file
nano .env
```

### 3. 启动应用

#### Linux/macOS
```bash
# 给启动脚本执行权限
chmod +x start_mining_core.sh

# 启动应用
./start_mining_core.sh
```

#### Windows
```cmd
# 运行启动脚本
start_mining_core.bat
```

### 4. 验证安装
访问 http://localhost:5001 查看应用是否正常运行。

## 详细安装指南 Detailed Installation Guide

### 方法一：使用启动脚本 (推荐)

启动脚本会自动处理以下步骤：
1. 检查Python版本
2. 创建虚拟环境
3. 安装依赖包
4. 初始化数据库
5. 启动应用

```bash
# Linux/macOS
./start_mining_core.sh

# Windows
start_mining_core.bat

# 开发模式
./start_mining_core.sh --dev

# 显示帮助
./start_mining_core.sh --help
```

### 方法二：手动安装

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 2. 升级pip
pip install --upgrade pip

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp config.env.template .env
# 编辑 .env 文件

# 5. 初始化数据库
cd mining_core_module
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 6. 启动应用
# 开发模式
python main.py

# 生产模式
gunicorn --bind 0.0.0.0:5001 main:app
```

### 方法三：Docker部署

```bash
# 1. 构建镜像
docker build -t mining-core .

# 2. 运行容器
docker run -d -p 5001:5001 --name mining-core-app mining-core

# 或使用Docker Compose
docker-compose up -d

# 查看日志
docker-compose logs -f mining-core
```

## 配置说明 Configuration

### 主要配置项

| 配置项 | 说明 | 默认值 | 必需 |
|--------|------|--------|------|
| `DATABASE_URL` | 数据库连接字符串 | sqlite:///mining_core.db | 是 |
| `SESSION_SECRET` | 应用密钥 | - | 是 |
| `COINWARZ_API_KEY` | CoinWarz API密钥 | - | 否 |
| `BITCOIN_RPC_URL` | Bitcoin RPC URL | - | 否 |
| `PORT` | 服务端口 | 5001 | 否 |
| `DEBUG` | 调试模式 | false | 否 |

### 数据库配置

#### PostgreSQL (推荐)
```env
DATABASE_URL=postgresql://username:password@localhost:5432/mining_core_db
```

#### SQLite (开发环境)
```env
DATABASE_URL=sqlite:///mining_core.db
```

### API配置

```env
# CoinWarz API (获取挖矿难度数据)
COINWARZ_API_KEY=your-api-key

# Bitcoin RPC (获取区块链数据)
BITCOIN_RPC_URL=https://your-rpc-endpoint
BITCOIN_RPC_USER=your-username
BITCOIN_RPC_PASSWORD=your-password
```

## API使用说明 API Usage

### 基础URL
```
http://localhost:5001/api/v1
```

### 主要端点

#### 1. 挖矿计算器
```http
POST /api/v1/calculate
Content-Type: application/json

{
    "hashrate": 110,
    "power_consumption": 3250,
    "electricity_cost": 0.06,
    "miner_model": "Antminer S19 Pro",
    "miner_count": 10
}
```

#### 2. 批量计算
```http
POST /api/v1/batch/calculate
Content-Type: multipart/form-data

file: miners.csv
```

#### 3. 获取市场数据
```http
GET /api/v1/market/data
```

#### 4. 健康检查
```http
GET /health
```

更多API文档请参考 `mining_api_docs.md`

## 功能模块 Functional Modules

### 1. 挖矿计算器 (Calculator)
- 单机计算模式
- 批量计算模式
- 实时数据更新
- 多种算法支持

### 2. 分析引擎 (Analytics)
- 高级算法引擎
- 历史数据分析
- 趋势预测分析
- 市场数据整合

### 3. 报告生成 (Reports)
- PDF格式报告
- Excel格式导出
- 图表可视化
- 自定义报告模板

### 4. 数据管理 (Data Management)
- 市场数据同步
- 历史数据存储
- 数据备份恢复
- 数据清理优化

## 性能优化 Performance Optimization

### 数据库优化
```python
# 数据库连接池配置
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 5,
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'pool_timeout': 30,
    'max_overflow': 10
}
```

### 缓存配置
```python
# Redis缓存配置
CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://localhost:6379/0'
CACHE_DEFAULT_TIMEOUT = 300
```

### API优化
- 启用请求压缩
- 实现响应缓存
- 优化数据库查询
- 异步任务处理

## 监控和日志 Monitoring & Logging

### 日志配置
```env
LOG_LEVEL=INFO
LOG_FILE=logs/mining_core.log
```

### 健康检查端点
```http
GET /health
GET /metrics
GET /status
```

### 性能监控
- CPU和内存使用率
- 数据库连接状态
- API响应时间
- 错误率统计

## 故障排除 Troubleshooting

### 常见问题

#### 1. 应用启动失败
```bash
# 检查Python版本
python3 --version

# 检查依赖安装
pip list

# 查看错误日志
tail -f logs/mining_core.log
```

#### 2. 数据库连接失败
```bash
# 检查数据库状态
# PostgreSQL
pg_isready -h localhost -p 5432

# 检查连接字符串
echo $DATABASE_URL
```

#### 3. API请求失败
```bash
# 测试健康检查
curl http://localhost:5001/health

# 测试API端点
curl -X POST http://localhost:5001/api/v1/calculate \
  -H "Content-Type: application/json" \
  -d '{"hashrate": 110, "power_consumption": 3250}'
```

### 调试模式

```bash
# 启用调试模式
export DEBUG=true
export LOG_LEVEL=DEBUG

# 重启应用
./start_mining_core.sh --dev
```

## 更新和维护 Updates & Maintenance

### 版本更新
```bash
# 备份数据
pg_dump mining_core_db > backup.sql

# 更新代码
git pull origin main

# 安装新依赖
pip install -r requirements.txt

# 数据库迁移
python -c "from app import app, db; app.app_context().push(); db.create_all()"

# 重启应用
./start_mining_core.sh
```

### 数据备份
```bash
# 自动备份脚本
./scripts/backup_database.sh

# 手动备份
pg_dump mining_core_db > backup_$(date +%Y%m%d_%H%M%S).sql
```

### 定期维护
- 清理过期日志文件
- 优化数据库索引
- 更新API密钥
- 监控系统性能

## 安全配置 Security Configuration

### SSL/TLS配置
```nginx
# Nginx SSL配置示例
server {
    listen 443 ssl;
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### API安全
```env
# API访问密钥
API_ACCESS_KEY=your-secure-api-key

# CORS配置
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

## 支持和贡献 Support & Contributing

### 技术支持
- 📧 Email: support@hashinsight.net
- 📞 电话: +86-xxx-xxxx-xxxx
- 💬 在线客服: https://support.hashinsight.net

### 文档
- 📖 完整文档: https://docs.hashinsight.net
- 🔧 API文档: https://api.hashinsight.net/docs
- 📝 更新日志: https://changelog.hashinsight.net

### 许可证
本项目采用 MIT 许可证。详见 LICENSE 文件。

### 版本信息
- 当前版本: v2.1.0
- 发布日期: 2025-09-27
- 构建号: 20250927-001

---

**HashInsight Mining Intelligence Platform**  
© 2025 HashInsight Technologies. All rights reserved.