# Device Envelope Encryption Architecture (设备信封加密)

## Overview

Device Envelope Encryption provides end-to-end encryption (E2EE) for miner credentials between the web browser and Edge Collector devices. The server never sees plaintext credentials - it only stores encrypted ciphertext packages that can only be decrypted by authorized Edge Collector devices.

## Complete Architecture Diagram

```
浏览器 (矿场主)                                            服务器 (HashInsight)                                            边缘采集器 (Edge Collector)
┌───────────────────────────────────────────────┐         ┌───────────────────────────────────────────────┐              ┌───────────────────────────────────────────────┐
│ 0) 选择场地 Site / 绑定 Edge Device            │         │ 多租户控制面                                   │              │ Init) 首次启动生成设备密钥对 (X25519)          │
│    - site_id / device_id                       │  HTTPS  │ - devices(pubkey/status/key_version/token)     │   HTTPS       │  - privkey 本地安全保存(加密落盘/TPM/Keychain) │
│                                                ├────────►│ - miners(asset metadata + fingerprint)         ├─────────────►│  - pubkey 注册 /devices/register               │
│ 1) 输入 IP 范围/网段                            │         │ - secrets(仅密文包)                            │              │  - 获取 device_id + device_token               │
│    192.168.1.100-200 / 10.10.0.0/24            │         └───────────────────────────────────────────────┘              └───────────────────────────────────────────────┘
│                                                │
│ 2) 点击 "IP 扫描/发现"                          │
│    (不需要先录入密码)                           │
│                                                │                                                        2) 扫描流程 (Discovery)
│ 3) 选择 "隐藏 IP 地址信息"策略 (可选)            │                                                        ┌───────────────────────────────────────────────┐
│    ├─ 方案1: UI脱敏 + RBAC + 审计 (默认)         │                                                        │ - 预探测：ping/TCP 探测                         │
│    ├─ 方案2: 服务器加密IP (KMS/Envelope)         │                                                        │ - 端口探测：4028/80/443(可配)                   │
│    └─ 方案3: E2EE加密IP (Server永不见明文)       │                                                        │ - 协议识别：CGMiner/Web 指纹                     │
│                                                │                                                        │ - 生成 fingerprint：MAC/序列号(优先) / hash(次优)│
│ 4) 选择能力等级                                 │                                                        │ - 上报资产清单：miner_id,fingerprint,model,fw    │
│    ├─ Level 1: 仅发现(资产盘点)                  │                                                        └───────────────────────────────────────────────┘
│    ├─ Level 2: 只读遥测(优先不输密码)            │
│    └─ Level 3: 管理控制(需要凭证+E2EE)           │
│                                                │
│ ---------------- Level 1：仅发现 ----------------│         服务器：保存资产概览（默认不展示完整IP）            Edge：持续更新在线状态/型号/固件
│ UI 展示：别名/型号/在线状态/指纹                 │         + RBAC：特权用户才可 Reveal IP(方案1)              + 上报 last_seen/health
│                                                │
│ ----------- Level 2：只读遥测(推荐) ------------ │         服务器：仅接收遥测与告警                           Edge：网络隔离后只读采集
│ (可选) 配置网络隔离建议：                         │         + 审计：采集/失败/异常                             ┌───────────────────────────────────────────────┐
│  - ACL/VLAN：仅 Edge 可访问矿机端口              │                                                        │ ACL/VLAN 建议：                                  │
│  - Office/Guest 禁止访问 Miner VLAN              │                                                        │ - Allow: Edge_VLAN -> Miner_VLAN : TCP 4028/80/443 │
│                                                │                                                        │ - Deny : Office/Guest -> Miner_VLAN : ANY         │
│                                                │                                                        └───────────────────────────────────────────────┘
│                                                │
│ -------- Level 3：管理/控制（凭证 + E2EE） ------│         服务器：只存密文包（No-decrypt）                   Edge：解封/解密后连接矿机执行
│ 5) 浏览器录入矿机凭证(用户名/密码/Token)         │  HTTPS  ┌───────────────────────────────────────────────┐   HTTPS       ┌───────────────────────────────────────────────┐
│    (IP/Port 可选择同包加密 = 方案3)              ├────────►│ miner_secrets:                                 ├─────────────►│ - 检查 device ACTIVE + counter 防回滚           │
│ 6) 生成随机 DEK (每台矿机/每条记录)              │         │ - encrypted_payload (AES-256-GCM)               │              │ - 用 device_privkey unwrap DEK                  │
│ 7) AES-256-GCM 加密凭证 JSON + AAD 绑定          │         │ - wrapped_DEK (sealed box / X25519)             │              │ - 用 DEK 解密凭证(仅内存短驻留)                 │
│    AAD: tenant/site/device/miner/counter/version │         │ - nonce/tag + aad + counter + schema_version    │              │ - 连接矿机(LAN)执行控制/采集                     │
│ 8) 用 device 公钥 wrap DEK                        │         │ 服务器无法解密（无私钥/无KEK）                   │              │ - 上报遥测+操作审计事件(JSONL)                   │
│ 9) 上传密文包(Server 永不见明文)                 │         └───────────────────────────────────────────────┘              └───────────────────────────────────────────────┘
└───────────────────────────────────────────────┘
```

## Cryptographic Algorithms

| Algorithm | Purpose | Details |
|-----------|---------|---------|
| **X25519 Sealed Box** | Wrap DEK for specific device | libsodium `crypto_box_seal` |
| **AES-256-GCM** | Encrypt miner credentials | 256-bit key, authenticated encryption |
| **12-byte Nonce** | Per-encryption randomness | Unique per encryption operation |
| **Counter** | Anti-rollback protection | Strictly increasing monotonic value |
| **AAD** | Additional Authenticated Data | Binds ciphertext to context |

### AAD Binding Format

AAD (Additional Authenticated Data) ensures the encrypted payload is bound to its intended context:

```json
{
  "tenant_id": 123,
  "site_id": 2,
  "device_id": 456,
  "miner_id": 789,
  "counter": 1,
  "schema_version": 1
}
```

This prevents:
- Cross-tenant attacks (using ciphertext from another tenant)
- Cross-device attacks (replaying to wrong device)
- Rollback attacks (counter must be strictly increasing)

## IP Hiding Strategies (IP 隐藏策略)

### Strategy 1: UI Masking + RBAC + Audit (Default)

```
┌─────────────────────────────────────────────────────────────┐
│ 特点：                                                       │
│ - IP 明文存储在服务器                                         │
│ - UI 默认显示脱敏格式: 192.168.1.xxx                          │
│ - RBAC 控制谁可以 "Reveal IP"                                 │
│ - 所有 Reveal 操作记录审计日志                                 │
│                                                              │
│ 优点：实现简单，支持服务器端搜索/过滤                          │
│ 缺点：服务器管理员理论上可以看到 IP                            │
└─────────────────────────────────────────────────────────────┘
```

### Strategy 2: Server-Side Encryption (KMS/Envelope)

```
┌─────────────────────────────────────────────────────────────┐
│ 特点：                                                       │
│ - IP 使用服务器端 KMS 密钥加密存储                            │
│ - 服务器可以按需解密（需要 KMS 权限）                          │
│ - 支持密钥轮换                                               │
│                                                              │
│ 优点：比明文更安全，支持合规审计                               │
│ 缺点：服务器仍然可以解密                                      │
└─────────────────────────────────────────────────────────────┘
```

### Strategy 3: E2EE Encryption (Zero-Knowledge)

```
┌─────────────────────────────────────────────────────────────┐
│ 特点：                                                       │
│ - IP 与凭证一起在浏览器端加密                                 │
│ - 密文包发送到服务器，服务器无法解密                           │
│ - 只有绑定的 Edge Collector 可以解密                          │
│                                                              │
│ 优点：真正的零知识，服务器永不见明文 IP                        │
│ 缺点：服务器无法基于 IP 进行搜索/分析                          │
└─────────────────────────────────────────────────────────────┘
```

## Capability Levels (能力等级)

| Level | Name | Permissions | Requires Credentials |
|-------|------|-------------|---------------------|
| 1 | DISCOVERY | Discover miners on network, asset inventory | No |
| 2 | TELEMETRY | Read-only telemetry (hashrate, temp, status) | Recommended: No |
| 3 | CONTROL | Full management control (restart, config) | Yes (E2EE) |

### Level 1: Discovery Only
- Edge Collector scans network for miners
- Reports: model, firmware, online status, fingerprint
- No credentials needed
- UI shows masked IP by default

### Level 2: Read-Only Telemetry (Recommended)
- Edge Collector pulls telemetry via CGMiner API (port 4028)
- Reports: hashrate, temperature, fan speed, pool info
- Network isolation recommended (see below)
- Credentials optional but not recommended

### Level 3: Management Control
- Full control: restart, change pool, update firmware
- **Requires encrypted credentials (E2EE)**
- Counter-based anti-rollback protection
- Full audit logging

## IP Scan / Discovery Flow (IP 扫描流程)

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Pre-Detection (预探测)                               │
│ - ICMP ping sweep                                            │
│ - TCP SYN scan on common ports                               │
│                                                              │
│ Step 2: Port Detection (端口探测)                            │
│ - TCP 4028 (CGMiner API)                                     │
│ - TCP 80/443 (Web interface)                                 │
│ - Custom ports (configurable)                                │
│                                                              │
│ Step 3: Protocol Identification (协议识别)                   │
│ - CGMiner API fingerprint                                    │
│ - Web interface fingerprint                                  │
│ - SNMP (optional)                                            │
│                                                              │
│ Step 4: Generate Fingerprint (生成指纹)                      │
│ - Priority 1: MAC address                                    │
│ - Priority 2: Serial number                                  │
│ - Priority 3: Hash of attributes                             │
│                                                              │
│ Step 5: Report Asset List (上报资产清单)                     │
│ - miner_id, fingerprint, model, firmware, last_seen          │
└─────────────────────────────────────────────────────────────┘
```

## Network Isolation Recommendations (网络隔离建议)

For Level 2 (Telemetry) deployments, we recommend network isolation:

### Recommended ACL/VLAN Configuration

```
┌─────────────────────────────────────────────────────────────┐
│ VLAN Configuration:                                          │
│ - VLAN 100: Edge Collector(s)                                │
│ - VLAN 200: Mining Equipment                                 │
│ - VLAN 300: Office/Guest Network                             │
│                                                              │
│ ACL Rules:                                                   │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ALLOW: VLAN 100 -> VLAN 200 : TCP 4028, 80, 443         │ │
│ │ ALLOW: VLAN 100 -> VLAN 200 : ICMP                      │ │
│ │ DENY:  VLAN 300 -> VLAN 200 : ANY                       │ │
│ │ DENY:  ANY      -> VLAN 200 : ANY (default deny)        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Benefits:                                                    │
│ - Edge Collector is only device that can access miners       │
│ - Office/Guest cannot directly access miner management       │
│ - Reduces attack surface                                     │
└─────────────────────────────────────────────────────────────┘
```

## Edge Collector Private Key Security (私钥安全存储)

### Recommended Storage Methods

| Method | Security Level | Platform |
|--------|---------------|----------|
| TPM 2.0 | Highest | Hardware with TPM |
| macOS Keychain | High | macOS |
| Linux Keyring | High | Linux with GNOME/KDE |
| Encrypted File | Medium | Any (with strong passphrase) |

### Implementation Notes

```python
# Example: Secure key storage with encryption
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Derive encryption key from passphrase
def derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))

# Store private key encrypted
def store_private_key(private_key: bytes, passphrase: str, path: str):
    salt = os.urandom(16)
    key = derive_key(passphrase, salt)
    f = Fernet(key)
    encrypted = f.encrypt(private_key)
    with open(path, 'wb') as file:
        file.write(salt + encrypted)
```

## Data Models

### EdgeDevice (edge_devices table)

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| tenant_id | Integer | Owner (FK to user_access) |
| site_id | Integer | Mining site (optional) |
| device_name | String | Human-readable name |
| device_token | String | Bearer token for API auth |
| public_key | String | Base64 X25519 public key |
| key_version | Integer | Incremented on key rotation |
| status | Enum | ACTIVE, REVOKED, PENDING |
| last_seen_at | DateTime | Last heartbeat |
| created_at | DateTime | Registration time |

### MinerSecret (miner_secrets table)

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| tenant_id | Integer | Owner |
| device_id | Integer | Target device (FK) |
| miner_id | Integer | Miner (FK) |
| encrypted_payload | Text | AES-256-GCM ciphertext |
| wrapped_dek | Text | Sealed Box wrapped DEK |
| nonce | String | 12-byte base64 nonce |
| aad | JSON | Additional authenticated data |
| counter | Integer | Anti-rollback counter |
| key_version | Integer | Device key version used |

### DeviceAuditEvent (device_audit_events table)

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| event_type | String | DEVICE_REGISTERED, SECRET_CREATED, etc. |
| tenant_id | Integer | Tenant ID |
| device_id | Integer | Device ID (optional) |
| miner_id | Integer | Miner ID (optional) |
| actor_id | Integer | User who performed action |
| actor_type | String | 'user' or 'device' |
| ip_address | String | Masked IP address |
| event_data | JSON | Event-specific data |
| result | String | 'success' or 'error' |
| created_at | DateTime | Event timestamp |

## API Endpoints

### Device Management (/api/devices)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /register | Register new edge device with public key |
| GET | / | List devices for tenant |
| GET | /:id | Get device details |
| GET | /:id/pubkey | Get device public key for encryption |
| DELETE | /:id | Revoke device |
| POST | /:id/heartbeat | Device heartbeat |
| POST | /:id/rotate-key | Rotate device public key |

### Miner Secrets (/api/miners)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /:id/secrets | Upload encrypted credentials |
| GET | /:id/secrets | Get encrypted secrets |
| DELETE | /:id/secrets/:device_id | Delete secret |

### Capability Management (/api/miners)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /:id/capability | Get miner capability level |
| PUT | /:id/capability | Update capability level |
| PUT | /batch-capability | Batch update |

### Edge Collector (/api/edge)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /secrets | Pull secrets for all bound miners |
| GET | /secrets/:miner_id | Get specific miner secret |
| GET | /status | Get device status |
| POST | /ack | Acknowledge secret decryption |

### Audit (/api/audit)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /events | List audit events with filtering |
| GET | /events/:id | Get event details |
| GET | /stats | Get audit statistics |

## Security Features

1. **Zero-Knowledge Server**: Server never sees plaintext credentials or IP (Strategy 3)
2. **Anti-Rollback**: Monotonic counter prevents replay attacks
3. **Key Rotation**: Devices can rotate keypairs if compromised
4. **Device Binding**: Secrets are bound to specific devices via AAD
5. **Audit Logging**: All operations logged with masked IP, user agent
6. **CSP Protection**: Content Security Policy headers in production
7. **Device Revocation**: REVOKED status immediately stops secret access

## Client-Side Usage (Browser)

```javascript
// Initialize DeviceEnvelope
await DeviceEnvelope.init();

// Encrypt credentials for a device
const envelope = await DeviceEnvelope.encrypt({
    username: 'root',
    password: 'miner_password',
    ip: '192.168.1.100',  // Optional: include in E2EE (Strategy 3)
    port: 4028
}, devicePublicKeyBase64, keyVersion);

// Upload to server
await fetch(`/api/miners/${minerId}/secrets`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        device_id: deviceId,
        encrypted_payload: envelope.encrypted_payload,
        wrapped_dek: envelope.wrapped_dek,
        nonce: envelope.nonce,
        aad: envelope.aad,
        counter: nextCounter,
        key_version: keyVersion
    })
});
```

## Edge Collector Usage (Python)

```python
from nacl.public import PrivateKey, SealedBox
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64
import json

# Load private key from secure storage
private_key = PrivateKey(base64.b64decode(private_key_b64))
sealed_box = SealedBox(private_key)

# Pull secrets from cloud
response = requests.get(
    'https://api.example.com/api/edge/secrets',
    headers={'Authorization': f'Bearer {device_token}'}
)
secrets = response.json()['secrets']

for secret in secrets:
    # Verify counter (anti-rollback)
    if secret['counter'] <= last_processed_counter:
        log_security_event('ROLLBACK_ATTEMPT', secret)
        continue
    
    # Unwrap DEK using device private key
    wrapped_dek = base64.b64decode(secret['wrapped_dek'])
    dek = sealed_box.decrypt(wrapped_dek)
    
    # Decrypt credentials using DEK
    nonce = base64.b64decode(secret['nonce'])
    ciphertext = base64.b64decode(secret['encrypted_payload'])
    aesgcm = AESGCM(dek)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    credentials = json.loads(plaintext)
    
    # Use credentials (memory only, short-lived)
    connect_to_miner(credentials['ip'], credentials['port'],
                     credentials['username'], credentials['password'])
    
    # Clear from memory immediately after use
    del credentials
    del plaintext
    
    # Update counter
    last_processed_counter = secret['counter']
    
    # Acknowledge to server
    requests.post(
        f'https://api.example.com/api/edge/ack',
        headers={'Authorization': f'Bearer {device_token}'},
        json={'miner_id': secret['miner_id'], 'counter': secret['counter']}
    )
```

## UI Access

The Device Envelope Encryption UI is accessible at:
- **Site Settings Page**: `/hosting/site/:site_id/settings`
- Sections: Device Management, Capability Configuration, Audit Log

## Files

| File | Description |
|------|-------------|
| `api/device_api.py` | All API blueprints |
| `models_device_encryption.py` | Data models |
| `static/js/crypto_device_envelope.js` | Browser encryption library |
| `templates/hosting/site_settings.html` | Management UI |
| `migrations/012_add_device_envelope_encryption.sql` | Database schema |

## December 2025 Updates

- Implemented complete end-to-end encryption architecture
- Added capability level system (DISCOVERY/TELEMETRY/CONTROL)
- IP hiding strategies documented (3 options)
- Network isolation recommendations added
- AAD binding format specified
- Edge private key security guidelines
- CSP security headers enabled for production
- Audit log viewing API and UI
- Network scan API for miner discovery
