# CRM Platform 部署指南

## 快速启动

### 前置要求
- Docker & Docker Compose
- Node.js 18+ (本地开发)
- PostgreSQL 15+ (如果不使用Docker)

### 一键启动
```bash
# 1. 克隆项目
git clone <repository-url>
cd crm-saas-node

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件，设置数据库密码、JWT密钥等

# 3. 启动所有服务
chmod +x scripts/*.sh
./scripts/start.sh
```

系统将在以下端口运行：
- 前端: http://localhost:5000
- 后端API: http://localhost:3000
- API文档: http://localhost:3000/api-docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## 生产环境部署

### 1. 环境变量配置

生产环境必须设置以下变量：
```env
# 数据库（使用强密码）
DATABASE_URL=postgresql://prod_user:strong_password@db.example.com:5432/crm_prod

# JWT密钥（生成强随机密钥）
JWT_SECRET=<使用openssl rand -base64 32生成>
REFRESH_TOKEN_SECRET=<使用openssl rand -base64 32生成>
SESSION_SECRET=<使用openssl rand -base64 32生成>

# 域名
VITE_API_BASE_URL=https://api.example.com
CORS_ORIGIN=https://app.example.com

# Node环境
NODE_ENV=production
```

### 2. SSL/TLS配置

使用Nginx作为反向代理并配置SSL：

```nginx
server {
    listen 443 ssl http2;
    server_name app.example.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 数据库备份策略

```bash
# 手动备份
./scripts/backup.sh

# 定时备份（添加到crontab）
0 2 * * * /path/to/crm-saas-node/scripts/backup.sh
```

### 4. 监控与日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f api
docker-compose logs -f db

# 查看资源使用
docker stats
```

## 故障排查

### 问题1: 前端无法连接后端

**症状**: 前端显示网络错误

**解决方案**:
1. 检查后端是否运行: `docker-compose ps api`
2. 检查CORS配置: `.env`中的`CORS_ORIGIN`
3. 检查网络: `docker-compose logs api | grep CORS`

### 问题2: 数据库连接失败

**症状**: 后端无法启动，显示数据库错误

**解决方案**:
1. 检查PostgreSQL状态: `docker-compose ps db`
2. 验证DATABASE_URL: `echo $DATABASE_URL`
3. 手动测试连接: `docker-compose exec db psql -U crm_user -d crm_db`

### 问题3: JWT Token过期

**症状**: 用户频繁被登出

**解决方案**:
1. 检查JWT_EXPIRES_IN配置（建议15-30分钟）
2. 检查REFRESH_TOKEN_EXPIRES_IN（建议7-30天）
3. 确认token刷新机制正常工作

### 问题4: 迁移失败

**症状**: Prisma迁移报错

**解决方案**:
```bash
# 查看迁移状态
docker-compose exec api sh -c "cd /app && npx prisma migrate status"

# 重置数据库（⚠️危险操作）
docker-compose exec api sh -c "cd /app && npx prisma migrate reset"

# 强制应用迁移
docker-compose exec api sh -c "cd /app && npx prisma migrate deploy --force"
```

## 性能优化

### 1. 数据库索引
确保Prisma schema中定义了必要的索引：
- Lead: email, status, createdAt
- Deal: stage, accountId, createdAt
- Invoice: invoiceNumber, accountId, status

### 2. Redis缓存
启用缓存可以显著提升性能：
- Dashboard指标缓存: 5分钟
- 列表查询缓存: 2分钟

### 3. 前端优化
- 启用Gzip压缩（已在Nginx中配置）
- 使用CDN托管静态资源
- 实施代码分割（已在Vite中配置）

## 扩展部署

### 使用Docker Compose构建生产镜像

```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 启动生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 水平扩展

使用Docker Swarm或Kubernetes进行水平扩展：

```bash
# Docker Swarm 示例
docker stack deploy -c docker-compose.yml crm-stack
docker service scale crm-stack_api=3
```

### 负载均衡

使用Nginx或HAProxy进行负载均衡：

```nginx
upstream backend {
    server backend1:3000;
    server backend2:3000;
    server backend3:3000;
}

server {
    listen 80;
    
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 安全检查清单

- [ ] 所有环境变量使用强密钥
- [ ] 数据库密码足够复杂（至少16字符）
- [ ] HTTPS/SSL已配置
- [ ] CORS仅允许受信域名
- [ ] 定期备份数据库（每日自动备份）
- [ ] 日志监控已设置
- [ ] 敏感数据已加密
- [ ] API速率限制已配置
- [ ] 容器以非root用户运行
- [ ] 定期更新依赖包
- [ ] 启用防火墙规则

## 升级和维护

### 应用升级

```bash
# 1. 备份数据库
./scripts/backup.sh

# 2. 停止服务
./scripts/stop.sh

# 3. 更新代码
git pull origin main

# 4. 重新构建镜像
docker-compose build

# 5. 运行迁移
./scripts/migrate.sh

# 6. 启动服务
./scripts/start.sh
```

### 数据库维护

```bash
# 清理过期数据
docker-compose exec db psql -U crm_user -d crm_db -c "VACUUM ANALYZE;"

# 重建索引
docker-compose exec db psql -U crm_user -d crm_db -c "REINDEX DATABASE crm_db;"

# 检查数据库大小
docker-compose exec db psql -U crm_user -d crm_db -c "SELECT pg_size_pretty(pg_database_size('crm_db'));"
```

## 监控和告警

### 推荐监控工具

1. **应用监控**: Sentry, New Relic
2. **基础设施监控**: Prometheus + Grafana
3. **日志聚合**: ELK Stack (Elasticsearch, Logstash, Kibana)
4. **容器监控**: cAdvisor

### 健康检查

```bash
# 检查所有服务健康状态
./scripts/health-check.sh

# 单独检查API健康
curl http://localhost:3000/api/health

# 检查数据库连接
docker-compose exec db pg_isready -U crm_user
```

## 附录

### 常用Docker命令

```bash
# 查看容器状态
docker-compose ps

# 查看容器日志
docker-compose logs -f [service-name]

# 进入容器shell
docker-compose exec [service-name] sh

# 重启服务
docker-compose restart [service-name]

# 查看资源使用
docker stats

# 清理未使用的镜像和容器
docker system prune -a
```

### 环境变量生成

```bash
# 生成安全的JWT密钥
openssl rand -base64 32

# 生成UUID
uuidgen

# 生成随机密码
openssl rand -base64 24
```
