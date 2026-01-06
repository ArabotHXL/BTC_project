# HashInsight Secure Miner Onboarding - 使用文档
# HashInsight Secure Miner Onboarding - Documentation

## 目录 / Table of Contents

1. [概述 / Overview](#概述--overview)
2. [快速开始 / Quick Start](#快速开始--quick-start)
3. [ABAC 权限控制 / ABAC Access Control](#abac-权限控制--abac-access-control)
4. [凭证保护模式 / Credential Protection Modes](#凭证保护模式--credential-protection-modes)
5. [审批工作流 / Approval Workflow](#审批工作流--approval-workflow)
6. [审计链 / Audit Chain](#审计链--audit-chain)
7. [API 参考 / API Reference](#api-参考--api-reference)
8. [安全注意事项 / Security Notes](#安全注意事项--security-notes)

---

## 概述 / Overview

HashInsight Secure Miner Onboarding Demo 是一个企业级安全系统演示，展示了以下核心功能：

- **ABAC (基于属性的访问控制)**: 5 条隔离规则保护多租户数据
- **三层凭证保护**: UI Masking → Server Envelope → Device E2EE
- **四眼原则审批**: 敏感操作需要双人审批
- **不可变审计链**: SHA-256 哈希链保证日志完整性
- **Anti-rollback 保护**: 防止凭证重放攻击

---

## 快速开始 / Quick Start

### 启动服务 / Start Server

```bash
cd demo_secure_onboarding
uvicorn main:app --host 0.0.0.0 --port 3000
```

### 运行测试 / Run Tests

```bash
cd demo_secure_onboarding
python test_demo.py
```

### 访问 UI / Access UI

打开浏览器访问: `http://localhost:3000`

---

## ABAC 权限控制 / ABAC Access Control

### 5 条核心隔离规则 / 5 Core Isolation Rules

| 规则 / Rule | 说明 / Description |
|------------|---------------------|
| RULE-1 | **租户隔离 / Tenant Isolation**: 用户只能访问自己租户的资源 |
| RULE-2 | **站点隔离 / Site Isolation**: 用户只能访问被授权的站点 |
| RULE-3 | **敏感操作 / Sensitive Actions**: REVEAL_CREDENTIAL, CHANGE_MODE 等需要 owner/admin 角色 |
| RULE-4 | **操作权限 / Operator Actions**: CREATE_MINER, DISCOVERY_SCAN 需要至少 operator 角色 |
| RULE-5 | **设备访问 / Device Access**: Edge 设备需要有效 token 和 ACTIVE 状态 |

### 角色层级 / Role Hierarchy

```
owner (4) > admin (3) > operator (2) > viewer (1)
```

### 使用示例 / Usage Example

```python
from services.policy_service import evaluate

# 检查用户是否可以创建矿机
allowed, reason = evaluate(db, "CREATE_MINER", actor, resource=site)
if not allowed:
    print(f"拒绝访问: {reason}")
```

### API 示例 / API Example

```bash
# 以 operator 身份列出站点 (需要 Bearer token)
curl -H "Authorization: Bearer {token}" \
     http://localhost:3000/api/sites?tenant_id=1

# 如果 actor 没有站点访问权限，返回空列表
```

---

## 凭证保护模式 / Credential Protection Modes

### Mode 1: UI Masking (UI 掩码)

**特点 / Features:**
- 凭证以明文存储在数据库
- 通过 RBAC 控制显示：非管理员看到掩码版本 (192.168.xxx.xxx)
- 适合低安全要求场景

**存储格式 / Storage Format:**
```json
{"ip": "192.168.1.100", "port": 4028, "password": "secret123"}
```

**显示效果 / Display:**
```json
// 管理员 reveal 后
{"ip": "192.168.1.100", "port": 4028, "password": "secret123"}

// 普通显示
{"ip": "192.168.xxx.xxx", "port": "***", "password": "***"}
```

### Mode 2: Server Envelope Encryption (服务端信封加密)

**特点 / Features:**
- 使用站点 DEK (Data Encryption Key) 加密凭证
- MASTER_KEY → 包装 → Site DEK → 加密 → 凭证
- 服务器可以解密，适合需要服务端处理的场景

**存储格式 / Storage Format:**
```
ENC:gAAAAABh...（Fernet 加密的 base64）
```

**API 示例 / API Example:**
```python
from services.credential_service import store_credential_mode2, reveal_credential_mode2
from services.envelope_kms_service import generate_site_dek, wrap_dek

# 创建站点 DEK
dek = generate_site_dek()
wrapped_dek = wrap_dek(dek)

# 存储加密凭证
cred_json = '{"ip": "10.0.0.50", "port": 4028}'
stored, mode, fingerprint = store_credential_mode2(cred_json, wrapped_dek)

# 解密凭证 (需要审批)
revealed = reveal_credential_mode2(stored, wrapped_dek)
```

### Mode 3: Device E2EE (设备端到端加密)

**特点 / Features:**
- 服务器只存储密文，无法解密
- Edge 设备本地解密（需要 libsodium）
- 最高安全级别，适合敏感矿场

**存储格式 / Storage Format:**
```
E2EE:eyJjcmVkZW50aWFsIjogey4uLn0sICJjb3VudGVyIjogMTAwfQ==
```

**Anti-rollback 验证 / Anti-rollback Validation:**
```python
from services.credential_service import validate_anti_rollback

# 新 counter 必须大于上次接受的 counter
valid, msg = validate_anti_rollback(last_accepted_counter=50, new_counter=100)
# valid=True, msg="OK"

valid, msg = validate_anti_rollback(last_accepted_counter=100, new_counter=50)
# valid=False, msg="Anti-rollback reject: counter 50 <= last_accepted 100"
```

**前端 E2EE 加密示例 (JavaScript):**
```javascript
// 使用 libsodium-wrappers
const sodium = await import('libsodium-wrappers');
await sodium.ready;

// 生成密钥对
const keypair = sodium.crypto_box_keypair();

// 加密凭证
const credential = {ip: "192.168.1.1", port: 4028};
const payload = JSON.stringify({credential, counter: 1});
const encrypted = sodium.to_base64(sodium.crypto_secretbox_easy(
    sodium.from_string(payload),
    nonce,
    keypair.privateKey
));
```

---

## 审批工作流 / Approval Workflow

### 四眼原则 / Four-Eyes Principle

敏感操作需要双人审批：**请求者 ≠ 审批者**

### 变更请求类型 / Change Request Types

| 类型 / Type | 说明 / Description | 风险级别 / Risk |
|------------|---------------------|-----------------|
| REVEAL_CREDENTIAL | 查看明文凭证 | 高 |
| CHANGE_SITE_MODE | 更改站点安全模式 | 高 |
| BATCH_MIGRATE | 批量迁移凭证模式 | 高 |
| DEVICE_REVOKE | 撤销设备访问 | 中 |

### 工作流状态 / Workflow States

```
PENDING → APPROVED → EXECUTED
    ↓         ↓
REJECTED   EXPIRED
```

### API 示例 / API Example

```bash
# 1. 创建变更请求 (Operator)
curl -X POST http://localhost:3000/api/changes \
  -H "Authorization: Bearer {operator_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": 1,
    "site_id": 1,
    "request_type": "REVEAL_CREDENTIAL",
    "target_type": "miner",
    "target_id": 1,
    "requested_action": {"action": "reveal"},
    "reason": "需要检查矿机配置"
  }'

# 响应: {"id": 1, "status": "PENDING", "expires_at": "..."}

# 2. 审批变更请求 (Owner/Admin, 不同于请求者)
curl -X POST http://localhost:3000/api/changes/1/approve \
  -H "Authorization: Bearer {owner_token}"

# 响应: {"id": 1, "status": "APPROVED"}

# 3. 执行变更请求
curl -X POST http://localhost:3000/api/changes/1/execute \
  -H "Authorization: Bearer {owner_token}"

# 响应: {"id": 1, "status": "EXECUTED", "result": {"ip": "...", "port": ...}}
```

### Python 示例 / Python Example

```python
from services.approval_service import (
    create_change_request, 
    approve_change_request
)

# 创建变更请求
cr, msg = create_change_request(
    db,
    tenant_id=1,
    requester=operator,
    request_type="REVEAL_CREDENTIAL",
    target_type="miner",
    target_id=1,
    requested_action={"action": "reveal"},
    reason="配置检查",
    site_id=1
)

# 四眼审批 (owner != operator)
success, msg = approve_change_request(db, cr, owner)
```

---

## 审计链 / Audit Chain

### 不可变日志 / Immutable Logging

每个审计事件包含前一个事件的哈希，形成区块链式的不可变日志链。

### 日志结构 / Log Structure

```python
AuditEvent(
    tenant_id=1,
    event_type="REVEAL_CREDENTIAL_EXECUTE",
    actor_id=1,
    actor_name="owner_alice",
    role="owner",
    site_id=1,
    target_type="miner",
    target_id=1,
    detail={"cr_id": 1, "result": {...}},
    prev_hash="abc123...",
    event_hash="def456..."  # SHA-256(prev_hash + event_data)
)
```

### 验证审计链 / Verify Audit Chain

```python
from services.audit_service import verify_audit_chain

# 验证整个租户的审计链完整性
is_valid, broken_at = verify_audit_chain(db, tenant_id=1)
if not is_valid:
    print(f"审计链在事件 {broken_at} 处被篡改!")
```

### API 示例 / API Example

```bash
# 获取最近的审计日志
curl http://localhost:3000/api/audit?tenant_id=1&limit=10

# 响应
[
  {
    "id": 5,
    "event_type": "REVEAL_CREDENTIAL_EXECUTE",
    "actor_name": "owner_alice",
    "role": "owner",
    "created_at": "2024-01-06T12:00:00",
    "event_hash": "abc123..."
  },
  ...
]
```

---

## API 参考 / API Reference

### 认证 / Authentication

所有需要认证的 API 使用 Bearer Token:
```
Authorization: Bearer {api_token}
```

### 端点列表 / Endpoints

| 方法 / Method | 端点 / Endpoint | 说明 / Description |
|--------------|-----------------|---------------------|
| GET | `/api/tenants` | 列出所有租户 |
| GET | `/api/actors?tenant_id=` | 列出租户的用户 |
| GET | `/api/whoami` | 当前用户信息 |
| GET | `/api/sites?tenant_id=` | 列出站点 (ABAC 过滤) |
| GET | `/api/miners?site_id=` | 列出矿机 (ABAC 过滤) |
| POST | `/api/miners` | 创建矿机 |
| POST | `/api/changes` | 创建变更请求 |
| GET | `/api/changes?tenant_id=` | 列出变更请求 |
| POST | `/api/changes/{id}/approve` | 审批变更请求 |
| POST | `/api/changes/{id}/reject` | 拒绝变更请求 |
| POST | `/api/changes/{id}/execute` | 执行变更请求 |
| POST | `/api/discovery/scan` | 网络发现扫描 |
| GET | `/api/audit?tenant_id=` | 审计日志 |
| POST | `/api/edge/decrypt` | Edge 设备解密 (E2EE) |

---

## 安全注意事项 / Security Notes

### 生产环境配置 / Production Configuration

1. **禁用演示模式:**
   ```bash
   # 删除此环境变量 - 设备密钥不应存储在服务器
   unset DEMO_ALLOW_STORE_DEVICE_SECRET
   ```

2. **设置强 MASTER_KEY:**
   ```bash
   export MASTER_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
   ```

3. **启用 HTTPS:**
   所有 API 调用应通过 HTTPS 进行。

### 安全最佳实践 / Security Best Practices

- ✅ 使用 Mode 3 (E2EE) 保护敏感矿场凭证
- ✅ 定期轮换 API tokens
- ✅ 启用审计日志并定期验证链完整性
- ✅ 使用四眼原则审批所有敏感操作
- ✅ 限制 allowed_site_ids 遵循最小权限原则
- ⚠️ 永远不要在日志中记录明文凭证
- ⚠️ Mode 3 设备密钥只能存在于 Edge 设备

### 测试覆盖 / Test Coverage

所有核心安全功能已通过 11 项自动化测试验证：

1. ✅ 租户隔离 (RULE-1)
2. ✅ 站点隔离 (RULE-2)
3. ✅ 角色权限 (RULE-3, RULE-4)
4. ✅ Mode 1 凭证保护
5. ✅ Mode 2 信封加密
6. ✅ Mode 3 E2EE + Anti-rollback
7. ✅ 四眼审批工作流
8. ✅ 审计链完整性
9. ✅ 网络发现
10. ✅ 跨租户隔离
11. ✅ 权限撤销后拒绝

---

## 联系方式 / Contact

如有问题，请联系 HashInsight 技术支持团队。

---

*版本 / Version: 1.0*
*最后更新 / Last Updated: 2024-01-06*
