# 📋 HashInsight CDC Platform - 假设与默认配置清单

## 1. 默认端口配置

| 服务 | 端口 | 说明 |
|------|------|------|
| PostgreSQL | 5432 | 数据库主端口 |
| Redis | 6379 | 缓存和分布式锁 |
| Zookeeper | 2181 | Kafka协调服务 |
| Kafka (Internal) | 9092 | 内部通信 |
| Kafka (External) | 9093 | 外部访问 |
| Kafka Connect | 8083 | Debezium REST API |
| Kafka UI | 8080 | Web界面 |
| Flask Web API | 5000 | 应用主端口 |

## 2. Docker镜像版本

| 组件 | 镜像 | 版本 |
|------|------|------|
| PostgreSQL + TimescaleDB | timescale/timescaledb | 2.13.0-pg15 |
| Redis | redis | 7-alpine |
| Zookeeper | confluentinc/cp-zookeeper | 7.5.0 |
| Kafka | confluentinc/cp-kafka | 7.5.0 |
| Kafka Connect | debezium/connect | 2.4 |
| Kafka UI | provectuslabs/kafka-ui | latest |
| Python | python | 3.11-slim |

## 3. 默认账号密码

### PostgreSQL
- **用户名**: `hashinsight`
- **密码**: `hashinsight_secret_2024`
- **数据库**: `hashinsight`

### JWT
- **Secret**: `dev-secret`（开发环境，生产环境必须修改）
- **算法**: HS256
- **过期时间**: 24小时（未实现，需根据需求配置）

## 4. Kafka配置假设

### 主题配置
| 主题名称 | 分区数 | 副本数 | 保留时间 |
|---------|--------|--------|---------|
| events.miner | 3 | 1 | 7天 (604800000ms) |
| events.treasury | 3 | 1 | 7天 |
| events.ops | 3 | 1 | 7天 |
| events.crm | 3 | 1 | 7天 |
| events.dlq | 3 | 1 | 30天 (2592000000ms) |

### 消费者组
- `portfolio-consumer-group`: Portfolio重算消费者
- `intel-consumer-group`: Intelligence预测消费者

## 5. 缓存TTL假设

| 缓存类型 | TTL | 说明 |
|---------|-----|------|
| user_portfolio:{uid} | 600秒 (10分钟) | 用户投资组合 |
| user_analytics:{uid} | 300秒 (5分钟) | 用户分析数据 |
| forecast:{uid} | 1800秒 (30分钟) | 预测数据 |
| ops_schedule:{uid}:{date} | 3600秒 (1小时) | 运营排班 |

## 6. 性能假设与目标

### 数据规模
- **用户数**: 1,000 - 10,000
- **矿机数**: 10,000 - 100,000
- **日事件量**: 100,000 - 1,000,000
- **Outbox积压**: < 100条
- **DLQ失败率**: < 0.1%

### 延迟目标
- **P95 写库→可见**: ≤ 3秒
- **P99 写库→可见**: ≤ 5秒
- **消费者处理**: < 2秒/事件
- **缓存命中率**: > 80%

### 吞吐量
- **API QPS**: 1,000 req/s
- **Kafka吞吐**: 10,000 msg/s
- **Outbox捕获**: 2,000 events/s

## 7. 数据库配置假设

### PostgreSQL
- **WAL Level**: `logical` (CDC必需)
- **Max Replication Slots**: 4
- **Max WAL Senders**: 4
- **连接池大小**: 20
- **连接超时**: 30秒
- **Pool Recycle**: 3600秒

### TimescaleDB分区
- **Chunk Interval**: 1天
- **自动分区**: 启用
- **压缩策略**: 7天后压缩（未实现）

## 8. 安全假设

### 认证与授权
- **认证方式**: JWT Bearer Token
- **Scopes**: `miners:read`, `miners:write`, `intel:read`, `treasury:trade`
- **密码哈希**: bcrypt (成本因子: 12)
- **Session过期**: 24小时

### 加密
- **传输加密**: TLS 1.3（生产环境）
- **存储加密**: 无（假设PostgreSQL层处理）
- **敏感字段**: KMS加密（占位实现）

### 合规
- **审计日志保留**: 90天
- **GDPR合规**: 支持数据删除（未实现）
- **SOC2**: 支持审计追踪

## 9. 运维假设

### 健康检查
- **检查间隔**: 30秒
- **超时时间**: 5秒
- **失败重试**: 3次

### 日志
- **级别**: INFO（开发环境）, WARNING（生产环境）
- **格式**: JSON结构化日志
- **保留期**: 7天（Docker日志）

### 备份
- **数据库备份**: 每日全量（假设外部工具）
- **Kafka备份**: 7天保留期
- **Redis持久化**: AOF模式

## 10. 开发假设

### 开发环境
- **OS**: Linux/macOS
- **Docker**: 20+
- **Docker Compose**: 2.0+
- **Python**: 3.11
- **依赖管理**: pip + requirements.txt

### 测试数据
- **测试用户**: `test-user-001`
- **测试租户**: `default`
- **测试矿机**: Antminer S19 Pro (110 TH/s)

## 11. 未实现功能（占位）

以下功能已预留接口但未完整实现：

1. **KMS加密**
   - 矿机密码加密
   - 交易所API密钥加密
   - Secret轮转策略

2. **Treasury交易执行**
   - `POST /api/treasury/execute` 仅占位
   - 需要对接真实交易所API

3. **DLQ重放工具**
   - `scripts/replay_dlq.py` 未实现
   - 需要手动SQL查询处理

4. **时间窗口重放**
   - `scripts/replay_events.py` 未实现

5. **压力测试**
   - `tests/load_test.py` 未实现
   - 建议使用Locust

6. **监控告警**
   - Prometheus metrics已暴露
   - Alertmanager规则未配置

7. **自动扩缩容**
   - 手动扩展Worker数量
   - 未集成Kubernetes HPA

## 12. 生产环境建议

### 必须修改
- ✅ JWT_SECRET: 使用强随机密钥（32+字符）
- ✅ PostgreSQL密码: 强密码策略
- ✅ Redis密码: 启用requirepass
- ✅ Kafka认证: 启用SASL/SSL

### 建议优化
- ✅ 增加Kafka副本数（3副本）
- ✅ 启用PostgreSQL SSL
- ✅ 配置自动备份
- ✅ 集成监控告警
- ✅ 使用外部密钥管理（AWS KMS/Vault）

### 扩展性
- ✅ 使用Kafka集群（3+ broker）
- ✅ PostgreSQL主从复制
- ✅ Redis Cluster模式
- ✅ 多Worker实例负载均衡

## 13. 限制与约束

### 技术限制
- **单Kafka Broker**: 开发环境限制，生产需集群
- **无副本**: Kafka主题副本数=1，数据可能丢失
- **内存数据库**: Redis无持久化配置（AOF已启用但未测试）

### 业务限制
- **租户隔离**: RLS仅示例实现，需完整测试
- **幂等窗口**: Inbox无自动清理，需定期维护
- **事件顺序**: 同user_id保证顺序，跨用户无序

## 14. 依赖假设

### 外部服务
- **无外部依赖**: 完全自包含Docker环境
- **时区**: 统一UTC
- **字符集**: UTF-8

### 网络
- **内网通信**: 假设所有容器在同一网络
- **出口IP**: 无需固定IP
- **DNS**: Docker内置DNS解析

## 15. 故障模式

### 已处理
- ✅ Kafka broker重启: 自动重连
- ✅ PostgreSQL重启: 连接池重连
- ✅ Redis重启: 自动重连
- ✅ Worker崩溃: Docker自动重启
- ✅ 重复消息: Inbox幂等保证

### 未处理
- ❌ 脑裂问题: 单broker无此问题
- ❌ 数据丢失: 无Kafka副本
- ❌ 雪崩效应: 无熔断器
- ❌ 毒丸消息: DLQ手动处理

## 16. 版本兼容性

### 向后兼容
- **数据库Schema**: 迁移脚本递增式
- **API**: 使用版本号（未实现）
- **事件格式**: JSONB灵活扩展

### 升级路径
1. 停止Worker
2. 升级数据库Schema
3. 部署新版API
4. 启动新版Worker
5. 验证健康检查

---

**注意**: 本文档列出的假设基于开发/测试环境。生产部署需根据实际需求调整。
