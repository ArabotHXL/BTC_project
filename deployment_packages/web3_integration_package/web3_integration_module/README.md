# Web3 Integration Module

完整独立的Web3集成Flask应用，提供区块链、加密货币支付和NFT证书功能。

## 🚀 功能特性

### 核心功能
- **钱包认证**: MetaMask、WalletConnect等钱包连接和签名验证
- **加密货币支付**: 支持BTC、ETH、USDC支付处理和监控
- **NFT证书系统**: 自动铸造月度SLA证明NFT（Soulbound代币）
- **合规检查**: AML/KYC验证和风险评估
- **区块链集成**: Base L2网络集成，IPFS数据存储
- **智能合约**: 完整的合约部署和管理工具

### 技术栈
- **后端**: Flask 2.3.3, SQLAlchemy, Web3.py
- **区块链**: Base L2 (低gas费用), 以太坊兼容
- **存储**: PostgreSQL, IPFS (Pinata)
- **加密**: Fernet对称加密, JWT会话管理
- **监控**: 实时交易监控和确认跟踪

## 📁 项目结构

```
web3_integration_module/
├── app.py                    # 主Flask应用
├── main.py                   # 启动入口
├── config.py                 # 配置管理
├── models.py                 # 数据库模型
├── requirements.txt          # 依赖包
├── routes/                   # API路由
│   ├── auth.py              # 钱包认证
│   ├── payments.py          # 支付处理
│   ├── nft.py               # NFT管理
│   └── compliance.py        # 合规检查
├── services/                # 核心服务
│   ├── blockchain.py        # 区块链集成
│   ├── crypto_payment.py    # 加密支付
│   ├── nft_minting.py       # NFT铸造
│   ├── payment_monitor.py   # 支付监控
│   ├── nft_metadata.py      # NFT元数据生成
│   └── compliance.py        # 合规服务
├── contracts/               # 智能合约
│   ├── SLAProofNFT.sol     # SLA证书NFT合约
│   ├── MiningDataRegistry.sol # 数据注册合约
│   └── deploy.py            # 部署脚本
├── templates/               # HTML模板
├── static/                  # 静态文件
└── utils/                   # 工具函数
```

## 🛠️ 安装和配置

### 1. 环境要求
- Python 3.8+
- PostgreSQL 12+
- Node.js 16+ (用于合约编译)

### 2. 安装依赖
```bash
cd web3_integration_module
pip install -r requirements.txt
```

### 3. 环境变量配置

创建 `.env` 文件并配置以下变量：

#### 基础配置
```bash
FLASK_ENV=development
SESSION_SECRET=your-secret-key-32-chars-minimum
DATABASE_URL=postgresql://user:password@localhost/web3_integration
```

#### 区块链配置
```bash
# 网络配置 (默认使用测试网)
BLOCKCHAIN_ENABLE_MAINNET_WRITES=false
BLOCKCHAIN_PRIVATE_KEY=your-private-key
BASE_MAINNET_RPC=https://mainnet.base.org
BASE_TESTNET_RPC=https://sepolia.base.org

# 合约地址 (部署后更新)
MINING_REGISTRY_CONTRACT_ADDRESS=0x...
SLA_NFT_CONTRACT_ADDRESS=0x...

# 钱包地址
BTC_WALLET_ADDRESS=1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
ETH_WALLET_ADDRESS=0x742d35Cc6634C0532925a3b8D4C3bfcf4F0af2
USDC_WALLET_ADDRESS=0x742d35Cc6634C0532925a3b8D4C3bfcf4F0af2
```

#### 加密和存储
```bash
# 数据加密 (生产环境必需)
ENCRYPTION_PASSWORD=your-strong-encryption-password-32-chars
ENCRYPTION_SALT=your-unique-salt-16-chars

# IPFS存储
PINATA_JWT=your-pinata-jwt-token
```

#### 外部API (可选)
```bash
ETHERSCAN_API_KEY=your-etherscan-api-key
AML_API_KEY=your-aml-api-key
HD_WALLET_MNEMONIC=your-hd-wallet-mnemonic
```

### 4. 数据库初始化
```bash
# 创建数据库表
flask init-db

# 或重置数据库
flask reset-db
```

## 🚀 运行应用

### 开发模式
```bash
python main.py
```
应用将在 http://localhost:5002 启动

### 生产模式
```bash
FLASK_ENV=production gunicorn --bind 0.0.0.0:5002 main:app
```

## 📋 智能合约部署

### 1. 安装Solidity编译器
```bash
npm install -g solc
pip install py-solc-x
```

### 2. 部署合约
```bash
cd contracts
python deploy.py
```

按提示选择要部署的合约：
- MiningDataRegistry: 区块链数据注册合约
- SLAProofNFT: SLA证明NFT合约

部署成功后，将合约地址添加到环境变量中。

## 🔧 API接口

### 认证接口
```
POST /auth/wallet/connect     # 钱包连接
POST /auth/wallet/verify      # 签名验证
POST /auth/wallet/disconnect  # 断开连接
GET  /auth/status            # 认证状态
```

### 支付接口
```
GET  /payments/supported-currencies  # 支持的货币
POST /payments/create               # 创建支付
GET  /payments/status/<payment_id>  # 支付状态
GET  /payments/history             # 支付历史
```

### NFT接口
```
GET  /nft/certificates              # 用户证书列表
GET  /nft/certificates/<id>         # 证书详情
POST /nft/certificates/mint         # 铸造证书
GET  /nft/certificates/<id>/metadata # 证书元数据
```

### 合规接口
```
GET  /compliance/kyc/status         # KYC状态
POST /compliance/kyc/verify         # KYC验证
POST /compliance/aml/check          # AML检查
GET  /compliance/risk-assessment    # 风险评估
```

## 🔍 监控和健康检查

### 健康检查
```bash
curl http://localhost:5002/health
```

### 服务状态
```bash
curl http://localhost:5002/api/info
```

## 🔐 安全配置

### 生产环境安全检查清单

1. **环境变量**:
   - ✅ 设置强密码 (`SECRET_KEY`, `ENCRYPTION_PASSWORD`)
   - ✅ 配置真实的API密钥
   - ✅ 启用HTTPS (`SESSION_COOKIE_SECURE=true`)

2. **区块链安全**:
   - ✅ 使用专用部署私钥
   - ✅ 在主网部署前充分测试
   - ✅ 设置合理的Gas限制

3. **合规配置**:
   - ✅ 启用AML/KYC检查
   - ✅ 配置风险阈值
   - ✅ 启用审计日志

## 🧪 测试

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_auth.py
pytest tests/test_payments.py
pytest tests/test_nft.py
```

### 手动测试
```bash
# 测试钱包连接
curl -X POST http://localhost:5002/auth/wallet/connect \\
  -H "Content-Type: application/json" \\
  -d '{"wallet_address":"0x742d35Cc6634C0532925a3b8D4C3bfcf4F0af2","wallet_provider":"metamask"}'

# 测试支付创建
curl -X POST http://localhost:5002/payments/create \\
  -H "Content-Type: application/json" \\
  -d '{"amount_usd":100,"crypto_currency":"BTC"}'
```

## 📊 监控和日志

### 日志文件
- 应用日志: `web3_integration.log`
- 错误日志: 控制台输出

### 监控服务状态
```python
from services.payment_monitor import payment_monitor_service
from services.nft_minting import sla_nft_minting_system

# 检查服务状态
payment_status = payment_monitor_service.get_service_status()
nft_status = sla_nft_minting_system.get_minting_statistics()
```

## 🔄 部署和扩展

### Docker部署
```dockerfile
FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5002
CMD ["gunicorn", "--bind", "0.0.0.0:5002", "main:app"]
```

### 环境分离
- 开发环境: `FLASK_ENV=development`
- 测试环境: `FLASK_ENV=testing`
- 生产环境: `FLASK_ENV=production`

## 🤝 与其他模块集成

### API调用示例 (其他模块调用此模块)
```python
import requests

# 其他模块调用Web3集成模块
web3_base_url = "http://localhost:5002"

# 创建支付
response = requests.post(f"{web3_base_url}/payments/create", json={
    "amount_usd": 100,
    "crypto_currency": "BTC"
})

# 检查支付状态
payment_id = response.json()['payment']['payment_id']
status = requests.get(f"{web3_base_url}/payments/status/{payment_id}")
```

## 📚 技术文档

### 核心概念

1. **Soulbound NFT**: 不可转移的NFT证书，永久绑定到持有者地址
2. **Base L2集成**: 使用Base网络降低交易费用
3. **IPFS存储**: 去中心化存储NFT元数据和证书数据
4. **HD钱包**: 分层确定性钱包，为每个支付生成唯一地址

### 架构设计

1. **模块化设计**: 服务层、路由层、模型层分离
2. **异步监控**: 后台服务监控区块链交易状态
3. **缓存机制**: 合规检查结果缓存，减少重复计算
4. **错误处理**: 完整的异常处理和重试机制

## ⚠️ 注意事项

1. **主网部署**: 默认使用测试网，主网部署需要明确启用
2. **私钥安全**: 生产环境私钥必须安全存储
3. **Gas费用**: 监控并设置合理的Gas费用限制
4. **合规要求**: 根据当地法规配置KYC/AML检查
5. **备份策略**: 定期备份数据库和配置文件

## 🐛 故障排除

### 常见问题

1. **无法连接到区块链网络**:
   - 检查RPC URL配置
   - 验证网络连通性
   - 确认API密钥有效

2. **支付监控不工作**:
   - 检查后台服务状态
   - 验证数据库连接
   - 查看服务日志

3. **NFT铸造失败**:
   - 检查合约地址配置
   - 验证账户余额充足
   - 确认Gas费用设置

### 日志分析
```bash
# 查看最新日志
tail -f web3_integration.log

# 搜索错误
grep "ERROR" web3_integration.log

# 按服务过滤
grep "payment_monitor" web3_integration.log
```

## 📄 许可证

MIT License - 详见 LICENSE 文件

## 🙋‍♂️ 支持

如需技术支持或有问题，请联系开发团队或提交Issue。

---

**Web3 Integration Module v1.0.0**  
*独立的Web3集成服务，为现代DeFi应用提供完整的区块链功能*