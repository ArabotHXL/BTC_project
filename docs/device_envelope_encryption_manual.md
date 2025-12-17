# Device Envelope Encryption User Manual
# 设备信封加密用户手册

---

## Table of Contents / 目录

1. [System Overview / 系统概述](#1-system-overview--系统概述)
2. [IP Hiding Strategies / IP隐藏策略](#2-ip-hiding-strategies--ip隐藏策略)
3. [Device Management / 设备管理](#3-device-management--设备管理)
4. [Capability Levels / 能力等级](#4-capability-levels--能力等级)
5. [Security Audit / 安全审计](#5-security-audit--安全审计)
6. [E2EE Credential Flow / E2EE凭证流程](#6-e2ee-credential-flow--e2ee凭证流程)
7. [API Reference / API参考](#7-api-reference--api参考)
8. [Troubleshooting / 故障排除](#8-troubleshooting--故障排除)

---

## 1. System Overview / 系统概述

### English

The Device Envelope Encryption system provides enterprise-grade security for miner credentials in Bitcoin mining hosting platforms. It implements a zero-knowledge architecture where sensitive data (like miner IP addresses and login credentials) can only be decrypted by authorized Edge Collector devices.

**Key Features:**
- Three IP hiding strategies (UI Masking, Server Encryption, E2EE)
- X25519 Sealed Box for key exchange
- AES-256-GCM for credential encryption
- Anti-rollback protection with monotonic counters
- Complete audit trail for all security events

**Architecture:**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Browser       │────▶│   Cloud Server  │────▶│  Edge Collector │
│   (Encryption)  │     │   (Storage)     │     │  (Decryption)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   X25519+AES-GCM         Encrypted Blob          X25519 Unseal
   Browser-side           Never sees keys         Device-side
```

### 中文

设备信封加密系统为比特币矿机托管平台提供企业级安全保护。它采用零知识架构，敏感数据（如矿机IP地址和登录凭证）只能被授权的边缘采集器设备解密。

**核心特性：**
- 三种IP隐藏策略（UI脱敏、服务器加密、端到端加密）
- X25519密封盒用于密钥交换
- AES-256-GCM用于凭证加密
- 单调计数器防重放保护
- 完整的安全事件审计追踪

**架构图：**

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     浏览器      │────▶│    云端服务器    │────▶│   边缘采集器    │
│   （加密端）    │     │   （存储端）     │     │   （解密端）    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
   X25519+AES-GCM          加密数据块           X25519解封装
   浏览器端加密            无法查看密钥          设备端解密
```

---

## 2. IP Hiding Strategies / IP隐藏策略

### English

The system supports three IP address protection strategies:

#### Strategy 1: UI Masking (Default)
- **How it works:** IP addresses are stored in plaintext but masked in the UI display
- **Display format:** `192.168.xxx.xxx`
- **Security level:** Basic - protects against casual viewing
- **Use case:** Internal networks where IP discovery is not a concern

#### Strategy 2: Server Encryption (Fernet)
- **How it works:** IP addresses are encrypted on the server using Fernet (AES-128-CBC)
- **Key storage:** Server-side encryption key
- **Security level:** Medium - protects data at rest
- **Use case:** Compliance requirements for data encryption

#### Strategy 3: E2EE (End-to-End Encryption)
- **How it works:** IP addresses are encrypted in the browser before upload
- **Key exchange:** X25519 Sealed Box
- **Data encryption:** AES-256-GCM
- **Security level:** Highest - server never sees plaintext
- **Use case:** Maximum security for sensitive mining operations

**How to Change Strategy:**

1. Navigate to **Site Settings** → **IP Hiding Strategy**
2. Select desired strategy from dropdown
3. Click **"Batch Update All Miners"**
4. Confirm the action in the dialog

### 中文

系统支持三种IP地址保护策略：

#### 策略1：UI脱敏（默认）
- **工作原理：** IP地址以明文存储，但在UI显示时进行脱敏
- **显示格式：** `192.168.xxx.xxx`
- **安全等级：** 基础 - 防止随意查看
- **使用场景：** 内部网络，IP发现不是主要顾虑

#### 策略2：服务器加密（Fernet）
- **工作原理：** IP地址在服务器端使用Fernet（AES-128-CBC）加密
- **密钥存储：** 服务器端加密密钥
- **安全等级：** 中等 - 保护静态数据
- **使用场景：** 数据加密合规要求

#### 策略3：E2EE（端到端加密）
- **工作原理：** IP地址在浏览器端加密后再上传
- **密钥交换：** X25519密封盒
- **数据加密：** AES-256-GCM
- **安全等级：** 最高 - 服务器永远看不到明文
- **使用场景：** 敏感矿场操作的最高安全需求

**如何更改策略：**

1. 进入 **站点设置** → **IP隐藏策略**
2. 从下拉菜单选择所需策略
3. 点击 **"批量更新所有矿机"**
4. 在弹窗中确认操作

---

## 3. Device Management / 设备管理

### English

Edge Collector devices must be registered before they can receive encrypted credentials.

#### Registering a New Device

**Method 1: Via Web UI (Recommended)**
1. Navigate to **Site Settings** → **Device Envelope Encryption**
2. Click **"Generate Keypair"** to create X25519 keypair in browser
3. Enter a device name and click **"Register Device"**
4. Save the generated **Device Token** securely - it's shown only once

**Method 2: Via Python Script**
```python
from edge_collector.device_keypair import KeypairManager
import requests

manager = KeypairManager('/path/to/keystore')
keypair = manager.generate_and_save('my-device', passphrase='secure-pass')

# Register with cloud server
response = requests.post('https://your-server/api/devices/register', json={
    'device_name': 'my-device',
    'public_key': keypair.public_key_base64,
    'site_id': 1
}, headers={'Authorization': 'Bearer YOUR_TOKEN'})
device_token = response.json()['device']['device_token']
```

The device appears in **Site Settings** → **Device Management**

#### Device Status

| Status | Description |
|--------|-------------|
| ACTIVE | Device is registered and can receive secrets |
| REVOKED | Device access has been revoked |
| PENDING | Device registration is pending approval |

#### Key Rotation

To rotate a device's keypair (recommended every 90 days):

1. Navigate to **Device Management**
2. Click **"Rotate Key"** for the target device
3. All miners need to re-encrypt credentials for this device

### 中文

边缘采集器设备必须先注册才能接收加密凭证。

#### 注册新设备

**方法1：通过Web界面（推荐）**
1. 进入 **站点设置** → **设备信封加密**
2. 点击 **"生成密钥对"** 在浏览器中创建X25519密钥对
3. 输入设备名称并点击 **"注册设备"**
4. 安全保存生成的 **设备令牌** - 仅显示一次

**方法2：通过Python脚本**
```python
from edge_collector.device_keypair import KeypairManager
import requests

manager = KeypairManager('/path/to/keystore')
keypair = manager.generate_and_save('my-device', passphrase='secure-pass')

# 向云服务器注册
response = requests.post('https://your-server/api/devices/register', json={
    'device_name': 'my-device',
    'public_key': keypair.public_key_base64,
    'site_id': 1
}, headers={'Authorization': 'Bearer YOUR_TOKEN'})
device_token = response.json()['device']['device_token']
```

设备将出现在 **站点设置** → **设备管理**

#### 设备状态

| 状态 | 描述 |
|------|------|
| ACTIVE | 设备已注册，可以接收密钥 |
| REVOKED | 设备访问权限已撤销 |
| PENDING | 设备注册待审批 |

#### 密钥轮换

轮换设备密钥对（建议每90天一次）：

1. 进入 **设备管理**
2. 点击目标设备的 **"轮换密钥"**
3. 所有矿机需要为此设备重新加密凭证

---

## 4. Capability Levels / 能力等级

### English

Capability levels control what operations an Edge Collector can perform on miners.

| Level | Name | Permissions |
|-------|------|-------------|
| 1 | DISCOVERY | Can discover miners on network only |
| 2 | TELEMETRY | Can read miner status and metrics |
| 3 | CONTROL | Full control (requires E2EE credentials) |

**Setting Capability Level:**

1. Navigate to **Site Settings** → **Capability Levels**
2. Select a miner from the list
3. Choose the desired capability level
4. Click **Save**

**Important:** Level 3 (CONTROL) requires encrypted credentials to be uploaded via the E2EE flow. Without credentials, the Edge Collector cannot control the miner.

### 中文

能力等级控制边缘采集器可以对矿机执行的操作。

| 等级 | 名称 | 权限 |
|------|------|------|
| 1 | DISCOVERY | 仅可发现网络上的矿机 |
| 2 | TELEMETRY | 可读取矿机状态和指标 |
| 3 | CONTROL | 完全控制（需要E2EE凭证） |

**设置能力等级：**

1. 进入 **站点设置** → **能力等级**
2. 从列表中选择矿机
3. 选择所需的能力等级
4. 点击 **保存**

**重要提示：** 等级3（CONTROL）需要通过E2EE流程上传加密凭证。没有凭证，边缘采集器无法控制矿机。

---

## 5. Security Audit / 安全审计

### English

All security-related events are logged for compliance and forensics.

#### Audit Event Types

| Event Type | Description |
|------------|-------------|
| DEVICE_REGISTERED | New Edge device registered |
| KEY_ROTATED | Device keypair rotated |
| SECRET_CREATED | New E2EE credential uploaded |
| SECRET_UPDATED | E2EE credential updated |
| IP_MODE_CHANGED | Single miner IP mode changed |
| BATCH_IP_ENCRYPTION_MODE_CHANGED | Batch IP mode update |
| CAPABILITY_CHANGED | Miner capability level changed |

#### Viewing Audit Logs

1. Navigate to **Site Settings** → **Security Audit**
2. Use filters to narrow by event type, device, or date range
3. Click on any event for detailed information

#### Data Retention

Audit logs are retained for 365 days by default.

### 中文

所有安全相关事件都会记录日志，用于合规和取证。

#### 审计事件类型

| 事件类型 | 描述 |
|----------|------|
| DEVICE_REGISTERED | 新边缘设备注册 |
| KEY_ROTATED | 设备密钥对轮换 |
| SECRET_CREATED | 新E2EE凭证上传 |
| SECRET_UPDATED | E2EE凭证更新 |
| IP_MODE_CHANGED | 单台矿机IP模式变更 |
| BATCH_IP_ENCRYPTION_MODE_CHANGED | 批量IP模式更新 |
| CAPABILITY_CHANGED | 矿机能力等级变更 |

#### 查看审计日志

1. 进入 **站点设置** → **安全审计**
2. 使用筛选器按事件类型、设备或日期范围筛选
3. 点击任意事件查看详细信息

#### 数据保留

审计日志默认保留365天。

---

## 6. E2EE Credential Flow / E2EE凭证流程

### English

The E2EE credential flow ensures that miner passwords are encrypted in the browser and can only be decrypted by the target Edge Collector.

#### Encryption Flow (Browser → Cloud)

```
1. Browser generates random DEK (Data Encryption Key)
2. Credentials encrypted with DEK using AES-256-GCM
3. DEK wrapped with Edge device's X25519 public key (Sealed Box)
4. Encrypted package sent to cloud: {wrapped_dek, encrypted_payload, nonce, aad}
5. Cloud stores encrypted blob (cannot decrypt)
```

#### Decryption Flow (Cloud → Edge)

```
1. Edge Collector requests secrets from cloud
2. Cloud returns encrypted package
3. Edge uses X25519 private key to unseal DEK
4. DEK decrypts credentials with AES-256-GCM
5. Edge uses plaintext credentials to control miner
```

#### Anti-Rollback Protection

Each secret has a monotonic counter that must increase with every update. This prevents replay attacks where an attacker tries to restore an old credential.

### 中文

E2EE凭证流程确保矿机密码在浏览器中加密，只能被目标边缘采集器解密。

#### 加密流程（浏览器 → 云端）

```
1. 浏览器生成随机DEK（数据加密密钥）
2. 使用AES-256-GCM用DEK加密凭证
3. 使用边缘设备的X25519公钥包装DEK（密封盒）
4. 加密包发送到云端：{wrapped_dek, encrypted_payload, nonce, aad}
5. 云端存储加密数据块（无法解密）
```

#### 解密流程（云端 → 边缘）

```
1. 边缘采集器从云端请求密钥
2. 云端返回加密包
3. 边缘使用X25519私钥解封DEK
4. DEK使用AES-256-GCM解密凭证
5. 边缘使用明文凭证控制矿机
```

#### 防重放保护

每个密钥都有一个单调计数器，每次更新必须递增。这可以防止攻击者尝试恢复旧凭证的重放攻击。

---

## 7. API Reference / API参考

### Device Management APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/devices/register` | POST | Register new Edge device |
| `/api/devices` | GET | List all devices for tenant |
| `/api/devices/<id>` | GET | Get device details |
| `/api/devices/<id>` | DELETE | Revoke device access |
| `/api/devices/<id>/rotate-key` | POST | Rotate device keypair |
| `/api/devices/<id>/heartbeat` | POST | Device heartbeat |
| `/api/devices/<id>/pubkey` | GET | Get device public key |
| `/api/devices/by-site/<site_id>` | GET | List devices for site |

### Miner Secrets APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/miners/<id>/secrets` | POST | Upload encrypted credentials |
| `/api/miners/<id>/secrets` | GET | Get credential metadata |
| `/api/miners/<id>/secrets/<device_id>` | DELETE | Delete credential for device |
| `/api/miners/<id>/capability` | GET | Get capability level |
| `/api/miners/<id>/capability` | PUT | Set capability level |
| `/api/miners/batch-capability` | PUT | Batch update capability levels |

#### POST `/api/miners/<id>/secrets` Request Schema

```json
{
  "device_id": 1,                           // Required: Target Edge device ID
  "encrypted_payload": "base64-string",     // Required: AES-256-GCM encrypted credentials
  "wrapped_dek": "base64-string",           // Required: X25519 Sealed Box wrapped DEK
  "nonce": "base64-string",                 // Required: AES-GCM nonce (12 bytes)
  "aad": {                                  // Required: Additional Authenticated Data
    "schema_version": 1,
    "key_version": 1,
    "created_at": "2025-01-01T00:00:00Z"
  },
  "key_version": 1                          // Required: Must match device's current key_version
}
```

**Important Notes:**
- Counter is auto-incremented by server (starts at 1, increases on each update)
- Key version must match the device's current key_version (check via GET `/api/devices/<id>/pubkey`)
- If key_version mismatch, re-encrypt with new public key

### Edge Collector APIs

These APIs are called by Edge Collector devices using their device token.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/edge/secrets` | GET | Get all secrets for this device |
| `/api/edge/secrets/<miner_id>` | GET | Get secret for specific miner |
| `/api/edge/status` | GET | Get edge device status |
| `/api/edge/ack` | POST | Acknowledge receipt of secrets |

**Authentication:** Include `X-Device-Token: <device_token>` header

### IP Encryption APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sites/<id>/miners` | PATCH | Batch update IP encryption mode |
| `/api/sites/<id>/ip-stats` | GET | Get IP mode statistics |

### Audit APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/audit/events` | GET | List audit events (with filters) |
| `/api/audit/events/<id>` | GET | Get event details |
| `/api/audit/stats` | GET | Get audit statistics |

#### GET `/api/audit/events` Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `event_type` | string | Filter by event type (e.g., DEVICE_REGISTERED) |
| `device_id` | int | Filter by device ID |
| `miner_id` | int | Filter by miner ID |
| `start_date` | ISO date | Filter events after this date |
| `end_date` | ISO date | Filter events before this date |
| `limit` | int | Max results (default 50, max 100) |
| `offset` | int | Pagination offset |

---

## 8. Troubleshooting / 故障排除

### English

#### "Key version mismatch" Error
**Cause:** Device key has been rotated but credentials were not re-encrypted.
**Solution:** Re-upload credentials for the affected miners.

#### Edge Collector Cannot Decrypt Secrets
**Cause:** Device private key file is missing or corrupted.
**Solution:** 
1. Check if `device_keypair.json` exists
2. If lost, revoke old device and re-register

#### "Counter rollback detected" Error
**Cause:** Anti-rollback protection triggered.
**Solution:** Upload new credentials with higher counter value.

#### Device Shows "REVOKED" Status
**Cause:** Administrator revoked device access.
**Solution:** Contact administrator to re-enable or register new device.

### 中文

#### "密钥版本不匹配"错误
**原因：** 设备密钥已轮换，但凭证未重新加密。
**解决方案：** 为受影响的矿机重新上传凭证。

#### 边缘采集器无法解密密钥
**原因：** 设备私钥文件丢失或损坏。
**解决方案：**
1. 检查 `device_keypair.json` 是否存在
2. 如果丢失，撤销旧设备并重新注册

#### "检测到计数器回滚"错误
**原因：** 触发了防重放保护。
**解决方案：** 使用更高的计数器值上传新凭证。

#### 设备显示"已撤销"状态
**原因：** 管理员撤销了设备访问权限。
**解决方案：** 联系管理员重新启用或注册新设备。

---

## Version History / 版本历史

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12 | Initial release with full E2EE support |

---

*This manual is part of HashInsight Enterprise documentation.*
*本手册是HashInsight Enterprise文档的一部分。*
