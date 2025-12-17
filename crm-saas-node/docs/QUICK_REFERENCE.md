# 快速参考手册

## 常用命令

### 启动/停止

```bash
./scripts/start.sh          # 启动所有服务
./scripts/stop.sh           # 停止所有服务
./scripts/stop.sh --clean   # 停止并清理所有数据
docker-compose restart      # 重启所有服务
docker-compose restart api  # 重启特定服务
```

### 数据库

```bash
./scripts/migrate.sh        # 运行数据库迁移
./scripts/backup.sh         # 备份数据库
./scripts/restore.sh <file> # 恢复数据库
npx prisma studio           # 打开Prisma Studio (数据库GUI)
```

### 日志查看

```bash
docker-compose logs -f              # 查看所有服务日志
docker-compose logs -f api          # 查看后端日志
docker-compose logs -f db           # 查看数据库日志
docker-compose logs -f redis        # 查看Redis日志
docker-compose logs --tail=100 api  # 查看最后100行日志
```

### 开发

```bash
cd backend && npm run dev   # 后端开发模式（热重载）
cd frontend && npm run dev  # 前端开发模式（热重载）
npm run type-check          # TypeScript类型检查
npm run build               # 构建生产版本
```

### Docker操作

```bash
docker-compose ps                    # 查看容器状态
docker-compose exec api sh           # 进入后端容器
docker-compose exec db psql -U crm_user -d crm_db  # 连接数据库
docker stats                         # 查看资源使用
docker-compose down -v               # 停止并删除所有数据
```

## API端点

### 认证 (Authentication)

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/refresh` | 刷新访问令牌 |
| POST | `/api/auth/logout` | 用户登出 |
| POST | `/api/auth/logout-all` | 从所有设备登出 |

### Lead管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/leads` | 获取Lead列表 |
| POST | `/api/leads` | 创建新Lead |
| GET | `/api/leads/:id` | 获取Lead详情 |
| PUT | `/api/leads/:id` | 更新Lead |
| DELETE | `/api/leads/:id` | 删除Lead |
| POST | `/api/leads/:id/convert` | 转换为Deal |

### Deal管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/deals` | 获取Deal列表 |
| POST | `/api/deals` | 创建新Deal |
| GET | `/api/deals/:id` | 获取Deal详情 |
| PUT | `/api/deals/:id` | 更新Deal |
| PUT | `/api/deals/:id/stage` | 更新Deal阶段 |
| POST | `/api/deals/:id/generate-contract` | 生成合同 |

### Invoice管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/invoices` | 获取Invoice列表 |
| POST | `/api/invoices` | 创建新Invoice |
| GET | `/api/invoices/:id` | 获取Invoice详情 |
| PUT | `/api/invoices/:id` | 更新Invoice |
| POST | `/api/invoices/:id/send` | 发送Invoice |
| GET | `/api/invoices/aging-report` | 获取账龄报告 |

### Payment管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/payments` | 获取Payment列表 |
| POST | `/api/payments` | 记录付款 |
| GET | `/api/payments/:id` | 获取Payment详情 |

### 资产管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/assets` | 获取矿机资产列表 |
| POST | `/api/assets` | 创建矿机资产 |
| GET | `/api/assets/:id` | 获取资产详情 |
| PUT | `/api/assets/:id` | 更新资产状态 |

### 批次管理

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/batches` | 获取批次列表 |
| POST | `/api/batches` | 创建批次 |
| GET | `/api/batches/:id` | 获取批次详情 |
| POST | `/api/batches/:id/allocate` | 分配矿机到账户 |

## 默认端口

| 服务 | 端口 | 访问地址 |
|------|------|----------|
| 前端应用 | 5000 | http://localhost:5000 |
| 后端API | 3000 | http://localhost:3000 |
| API文档 | 3000 | http://localhost:3000/api-docs |
| PostgreSQL | 5432 | localhost:5432 |
| Redis | 6379 | localhost:6379 |
| Adminer (数据库管理) | 8080 | http://localhost:8080 |

## 环境变量

### 核心变量

```env
# 数据库
DATABASE_URL=postgresql://crm_user:crm_password@db:5432/crm_db
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=crm_password
POSTGRES_DB=crm_db

# JWT认证
JWT_SECRET=your-super-secret-jwt-key
REFRESH_TOKEN_SECRET=your-refresh-token-secret
JWT_EXPIRES_IN=15m
REFRESH_TOKEN_EXPIRES_IN=30d

# API配置
PORT=3000
NODE_ENV=development

# Redis
REDIS_URL=redis://redis:6379

# CORS
CORS_ORIGIN=http://localhost:5000
```

### 可选变量

```env
# 第三方集成
QUICKBOOKS_CLIENT_ID=
DOCUSIGN_INTEGRATION_KEY=
GMAIL_CLIENT_ID=

# 功能开关
ENABLE_API_DOCS=true
ENABLE_SEED_DATA=false

# 日志
LOG_LEVEL=debug
LOG_FORMAT=json
```

## 数据库操作

### Prisma CLI命令

```bash
# 进入后端容器
docker-compose exec api sh

# 生成Prisma Client
npx prisma generate

# 创建新迁移
npx prisma migrate dev --name <migration-name>

# 应用迁移
npx prisma migrate deploy

# 重置数据库
npx prisma migrate reset

# 打开Prisma Studio
npx prisma studio

# 查看迁移状态
npx prisma migrate status

# 执行种子数据
npm run prisma:seed
```

### SQL查询

```bash
# 连接到数据库
docker-compose exec db psql -U crm_user -d crm_db

# 查看所有表
\dt

# 查看表结构
\d <table_name>

# 查询示例
SELECT * FROM "Lead" LIMIT 10;
SELECT COUNT(*) FROM "Deal";
```

## 故障排查

### 常见问题快速修复

```bash
# 问题: 容器无法启动
docker-compose down
docker-compose up -d

# 问题: 端口被占用
lsof -i :3000  # 查看占用端口的进程
kill -9 <PID>  # 终止进程

# 问题: 数据库连接失败
docker-compose restart db
docker-compose logs db

# 问题: npm依赖问题
docker-compose exec api sh -c "rm -rf node_modules package-lock.json && npm install"

# 问题: Prisma Client过期
docker-compose exec api sh -c "npx prisma generate"

# 问题: 前端构建失败
docker-compose exec frontend sh -c "npm run build"
```

### 日志检查

```bash
# 检查错误日志
docker-compose logs api | grep ERROR
docker-compose logs api | grep -i error

# 检查数据库连接
docker-compose logs api | grep -i database

# 检查API请求
docker-compose logs api | grep -i "POST\|GET\|PUT\|DELETE"
```

## 性能优化

### 数据库优化

```sql
-- 查看慢查询
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;

-- 查看表大小
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 分析表
ANALYZE "Lead";
ANALYZE "Deal";
```

### Redis缓存

```bash
# 连接Redis
docker-compose exec redis redis-cli

# 查看所有键
KEYS *

# 查看键数量
DBSIZE

# 清空缓存
FLUSHDB

# 查看内存使用
INFO memory
```

## 备份和恢复

### 备份操作

```bash
# 完整备份
./scripts/backup.sh

# 手动备份
docker-compose exec -T db pg_dump -U crm_user crm_db > backup_$(date +%Y%m%d).sql

# 压缩备份
gzip backup_$(date +%Y%m%d).sql
```

### 恢复操作

```bash
# 从备份恢复
./scripts/restore.sh ./backups/crm_backup_20250107_120000.sql.gz

# 手动恢复
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U crm_user crm_db
```

## 测试

### API测试

```bash
# 使用curl测试
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# 使用健康检查
curl http://localhost:3000/api/health
```

### 端到端测试

```bash
# 运行测试套件（如已配置）
npm run test

# 集成测试
npm run test:integration
```

## 安全最佳实践

### 密钥生成

```bash
# 生成JWT密钥
openssl rand -base64 32

# 生成刷新令牌密钥
openssl rand -base64 48

# 生成会话密钥
openssl rand -hex 32
```

### 定期维护任务

```bash
# 每日任务
- 检查日志: docker-compose logs --since 24h
- 检查磁盘空间: df -h
- 备份数据库: ./scripts/backup.sh

# 每周任务
- 更新依赖: npm audit fix
- 检查安全漏洞: npm audit
- 清理Docker: docker system prune

# 每月任务
- 轮换密钥
- 审查访问日志
- 性能优化评估
```

## 资源链接

- **API文档**: http://localhost:3000/api-docs
- **Prisma Studio**: `npx prisma studio`
- **Adminer**: http://localhost:8080
- **健康检查**: http://localhost:3000/api/health

## 快速故障排查流程

1. **检查服务状态**: `docker-compose ps`
2. **查看日志**: `docker-compose logs -f api`
3. **检查健康**: `./scripts/health-check.sh`
4. **重启服务**: `docker-compose restart api`
5. **完全重启**: `./scripts/stop.sh && ./scripts/start.sh`
