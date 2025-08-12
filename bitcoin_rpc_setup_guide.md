# Bitcoin RPC 用户名密码获取指南

## 方法一：自己运行Bitcoin Core节点 (推荐)

### 1. 下载并安装Bitcoin Core
- 官网下载: https://bitcoin.org/en/download
- 选择适合你操作系统的版本

### 2. 配置bitcoin.conf文件
创建配置文件 `bitcoin.conf`:

**Windows路径**: `C:\Users\{用户名}\AppData\Roaming\Bitcoin\bitcoin.conf`
**macOS路径**: `~/Library/Application Support/Bitcoin/bitcoin.conf`  
**Linux路径**: `~/.bitcoin/bitcoin.conf`

```ini
# bitcoin.conf 配置示例
server=1
rpcuser=mining_calculator_user
rpcpassword=your_secure_password_here123
rpcallowip=127.0.0.1
rpcport=8332

# 可选: 减少磁盘使用 (裁剪模式)
prune=50000
```

### 3. 启动Bitcoin Core
```bash
# 命令行启动
bitcoind

# 或者使用GUI版本Bitcoin Core
```

### 4. 等待同步 (重要!)
- 首次同步需要1-7天时间
- 需要约500GB磁盘空间
- 同步完成后才能使用RPC

## 方法二：使用现有的Bitcoin节点服务

### 公共RPC服务 (不推荐生产环境)
有些服务提供公共Bitcoin RPC接口，但通常:
- 有请求限制
- 稳定性不保证
- 可能收费

### 云服务商
- **QuickNode**: 提供Bitcoin RPC API服务
- **GetBlock**: Bitcoin节点即服务
- **Alchemy**: 区块链基础设施服务

## 方法三：本地测试网络 (开发测试)

```bash
# 启动测试网络节点 (更快同步)
bitcoind -testnet -rpcuser=test_user -rpcpassword=test_pass
```

## 成本对比

| 方案 | 成本 | 优缺点 |
|------|------|---------|
| 自建节点 | ~$10-50/月 (服务器+电费) | 完全控制，最准确 |
| 云服务 | ~$20-100/月 | 即用即得，但有依赖 |
| 不使用RPC | $0 | 当前方案，95%准确度 |

## 推荐方案

### 对于生产环境
**自建Bitcoin Core节点** - 虽然初期投资大，但长期最稳定可靠

### 对于测试开发  
**继续使用当前方案** - 第三方API已经足够准确

### 配置环境变量
获得用户名密码后，在Replit中设置:
```bash
BITCOIN_RPC_USER=你的用户名
BITCOIN_RPC_PASSWORD=你的密码
```

## 注意事项
- Bitcoin节点同步需要很长时间
- 需要稳定的网络连接
- 磁盘空间需求大 (500GB+)
- 如果只是测试挖矿计算器，当前API方案已经够用