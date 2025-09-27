# HashInsight Module Communication Framework

## 概述

HashInsight 模块通信框架为三个独立模块提供统一的API通信接口，支持独立运行和组合部署。

## 架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Mining Core    │    │ Web3 Integration│    │ User Management │
│   Module        │    │    Module       │    │     Module      │
│   Port 5001     │    │   Port 5002     │    │   Port 5003     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │ Service Registry│
                    │   Port 5005     │
                    └─────────────────┘
                                 │
                    ┌─────────────────┐
                    │   API Gateway   │
                    │   Port 5000     │
                    │ (可选)          │
                    └─────────────────┘
```

## 核心组件

### 1. 认证服务 (auth_token_service.py)
- JWT令牌管理
- API密钥管理
- 令牌验证和刷新
- 权限验证

### 2. 服务注册中心 (service_registry.py)
- 服务发现
- 健康检查
- 负载均衡
- 服务实例管理

### 3. API网关 (api_gateway.py)
- 请求路由
- 统一入口
- 速率限制
- 认证代理

### 4. 模块客户端 (clients/)
- mining_client.py - 挖矿计算客户端
- web3_client.py - Web3集成客户端
- user_client.py - 用户管理客户端

### 5. 优雅降级 (graceful_degradation.py)
- 熔断器模式
- 缓存机制
- 回退策略
- 健康监控

## 部署模式

### 1. 独立模式 (Standalone)
每个模块独立运行，直接进行模块间通信。

```bash
# 启动独立模式
python module_communication/startup_scripts/start_standalone.py start all
```

### 2. 组合模式 (Combined)
所有模块 + API网关 + 服务注册中心一起运行。

```bash
# 启动组合模式
python module_communication/startup_scripts/start_combined.py start
```

### 3. 网关模式 (Gateway)
仅API网关，模块在其他位置运行。

```bash
# 启动API网关
python -m module_communication.api_gateway
```

## 快速开始

### 1. 安装依赖
```bash
pip install flask requests pyjwt cryptography
```

### 2. 设置环境变量
```bash
export DATABASE_URL="postgresql://localhost:5432/hashinsight"
export JWT_SECRET_KEY="your_secret_key"
export SESSION_SECRET="your_session_secret"
export DEPLOYMENT_MODE="standalone"  # 或 "combined", "gateway"
```

### 3. 启动服务

#### 独立启动单个模块
```bash
# 用户管理模块
python module_communication/startup_scripts/start_standalone.py start user_management

# 挖矿核心模块
python module_communication/startup_scripts/start_standalone.py start mining_core

# Web3集成模块
python module_communication/startup_scripts/start_standalone.py start web3_integration
```

#### 启动所有模块
```bash
# 独立模式启动所有模块
python module_communication/startup_scripts/start_standalone.py start all

# 组合模式启动
python module_communication/startup_scripts/start_combined.py start
```

### 4. 验证部署
```bash
# 检查服务状态
python module_communication/startup_scripts/start_standalone.py status

# 运行集成测试
python -m module_communication.tests.test_integration
```

## API 端点

### Mining Core Module (端口 5001)
- `GET /health` - 健康检查
- `POST /api/calculate/profitability` - 计算挖矿盈利能力
- `GET /api/analytics/market` - 获取市场分析
- `POST /api/reports/generate` - 生成挖矿报告
- `GET /api/miners/models` - 获取矿机型号
- `GET /api/network/metrics` - 获取网络指标

### Web3 Integration Module (端口 5002)
- `GET /health` - 健康检查
- `POST /api/auth/wallet` - 钱包认证
- `POST /api/payments/create` - 创建支付订单
- `GET /api/payments/{id}/status` - 检查支付状态
- `POST /api/nft/sla/mint` - 铸造SLA NFT
- `POST /api/storage/ipfs` - IPFS存储
- `POST /api/compliance/kyc` - KYC检查

### User Management Module (端口 5003)
- `GET /health` - 健康检查
- `POST /api/auth/validate` - 验证用户令牌
- `GET /api/users/{id}/subscription` - 检查用户订阅
- `POST /api/users/{id}/permissions` - 检查用户权限
- `PUT /api/users/{id}/kyc` - 更新KYC状态
- `POST /api/users/{id}/payments/complete` - 处理支付完成

### API Gateway (端口 5000)
- `GET /health` - 网关健康检查
- `GET /gateway/info` - 网关信息
- `/api/mining/*` → 路由到Mining Core
- `/api/web3/*` → 路由到Web3 Integration
- `/api/users/*` → 路由到User Management

### Service Registry (端口 5005)
- `GET /health` - 注册中心健康检查
- `GET /services` - 列出所有服务
- `GET /services/{name}` - 发现特定服务
- `POST /services/register` - 注册服务
- `POST /services/{name}/{id}/heartbeat` - 服务心跳

## 模块间通信示例

### 1. 挖矿计算工作流
```python
# 1. 验证用户认证
auth_result = user_client.validate_user_token(jwt_token)

# 2. 检查订阅权限
subscription = user_client.check_user_subscription(user_id)

# 3. 执行挖矿计算
calculation = mining_client.calculate_mining_profitability(miner_data)

# 4. 存储到IPFS
storage_result = web3_client.store_data_ipfs(calculation)

# 5. 铸造SLA NFT
nft_result = web3_client.mint_sla_nft(sla_data)
```

### 2. 支付处理工作流
```python
# 1. 创建支付订单
payment_order = web3_client.create_payment_order(payment_data)

# 2. 监控支付状态
payment_status = web3_client.check_payment_status(payment_id)

# 3. 处理支付完成
if payment_status['status'] == 'completed':
    completion_result = user_client.process_payment_completion(
        user_id, payment_data
    )
```

## 安全特性

### 1. 认证和授权
- JWT令牌认证
- API密钥验证
- 角色权限控制
- 令牌自动刷新

### 2. 网络安全
- HTTPS加密传输（生产环境）
- 请求签名验证
- API密钥轮换
- 速率限制防护

### 3. 服务安全
- 健康检查验证
- 熔断器保护
- 请求超时控制
- 错误重试机制

## 监控和调试

### 1. 健康检查
```bash
# 检查单个模块
curl http://localhost:5001/health

# 检查所有服务
curl http://localhost:5005/services
```

### 2. 日志配置
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 3. 性能监控
- 请求响应时间
- 服务可用性
- 错误率统计
- 资源使用情况

## 容错和恢复

### 1. 熔断器模式
自动检测故障服务并暂停请求，在服务恢复后自动重连。

### 2. 缓存机制
缓存关键响应数据，在服务不可用时提供基本功能。

### 3. 回退策略
为每个服务调用提供合理的回退行为。

### 4. 健康监控
持续监控服务健康状态，自动处理故障恢复。

## 开发指南

### 1. 添加新的API端点
```python
# 在对应模块的 routes/api_communication.py 中添加
@api_comm_bp.route('/api/new/endpoint', methods=['POST'])
def new_endpoint():
    # 实现逻辑
    return jsonify(format_success_response(data))
```

### 2. 添加新的客户端方法
```python
# 在对应的客户端文件中添加
def new_client_method(self, data):
    return self._make_request('POST', '/api/new/endpoint', json=data)
```

### 3. 添加集成测试
```python
# 在 tests/test_integration.py 中添加
def test_new_integration_flow(self):
    # 测试逻辑
    assert result['success'] == True
```

## Docker 部署

### 1. 生成配置
```bash
python module_communication/deploy_config.py
```

### 2. Docker Compose
```bash
docker-compose -f deployment_configs/docker-compose.yml up
```

### 3. Kubernetes
```bash
kubectl apply -f deployment_configs/kubernetes/
```

## 故障排除

### 1. 服务无法启动
- 检查端口是否被占用
- 验证环境变量配置
- 查看服务日志输出

### 2. 模块间通信失败
- 验证服务发现配置
- 检查网络连接
- 确认认证令牌有效

### 3. 性能问题
- 检查数据库连接
- 验证缓存配置
- 分析请求日志

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 运行测试
5. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。