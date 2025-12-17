# Device Envelope Encryption User Manual
# 设备信封加密用户手册

---

## Table of Contents / 目录

1. [Introduction / 简介](#1-introduction--简介)
2. [Getting Started / 快速开始](#2-getting-started--快速开始)
3. [Device Management / 设备管理](#3-device-management--设备管理)
4. [Capability Levels / 能力等级](#4-capability-levels--能力等级)
5. [Key Rotation / 密钥轮换](#5-key-rotation--密钥轮换)
6. [Audit Logs / 审计日志](#6-audit-logs--审计日志)
7. [Troubleshooting / 故障排除](#7-troubleshooting--故障排除)
8. [Security Best Practices / 安全最佳实践](#8-security-best-practices--安全最佳实践)

---

## 1. Introduction / 简介

### What is Device Envelope Encryption? / 什么是设备信封加密？

**English:**
Device Envelope Encryption is a security system that protects your miner access credentials (like passwords and API keys) using end-to-end encryption. This means your sensitive data is encrypted in your browser before being sent to the server, and can only be decrypted by authorized Edge Collector devices at your mining site.

**中文:**
设备信封加密是一个安全系统，使用端到端加密保护您的矿机访问凭证（如密码和API密钥）。这意味着您的敏感数据在浏览器中加密后才发送到服务器，只有您矿场授权的Edge Collector设备才能解密。

### Why Do I Need This? / 为什么需要这个功能？

**English:**
- **Zero-Knowledge Security**: Even our servers cannot read your miner passwords
- **Protection Against Breaches**: If our database is compromised, your credentials remain encrypted
- **Device-Level Access Control**: Only your registered Edge Collectors can access miner credentials
- **Audit Trail**: Complete logging of all credential access attempts

**中文:**
- **零知识安全**: 即使我们的服务器也无法读取您的矿机密码
- **防止数据泄露**: 即使数据库被攻破，您的凭证仍然是加密的
- **设备级访问控制**: 只有您注册的Edge Collector才能访问矿机凭证
- **完整审计追踪**: 记录所有凭证访问尝试

### How It Works / 工作原理

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your Browser  │───▶│  Cloud Server   │───▶│ Edge Collector  │
│   您的浏览器     │    │  云服务器        │    │ 边缘采集器       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
   1. Encrypt               2. Store              3. Decrypt
   1. 加密                  2. 存储               3. 解密
   credentials            ciphertext            and use
   凭证                    密文                   并使用
```

---

## 2. Getting Started / 快速开始

### Prerequisites / 前提条件

**English:**
- You must be a site administrator (Admin or Owner role)
- Your Edge Collector must be installed and connected to the internet
- Modern web browser (Chrome, Firefox, Safari, Edge)

**中文:**
- 您必须是站点管理员（Admin或Owner角色）
- 您的Edge Collector必须已安装并连接互联网
- 现代浏览器（Chrome、Firefox、Safari、Edge）

### Step 1: Access Site Settings / 步骤1：访问站点设置

**English:**
1. Log in to the hosting portal
2. Navigate to **Hosting** → **Sites**
3. Click on your site name
4. Go to **Settings** tab
5. Scroll down to **Device Encryption** section

**中文:**
1. 登录托管门户
2. 导航到 **托管** → **站点**
3. 点击您的站点名称
4. 进入 **设置** 标签
5. 向下滚动到 **设备加密** 部分

### Step 2: Register Your First Edge Device / 步骤2：注册您的第一个边缘设备

**English:**
1. Click **Register New Device** button
2. Enter a descriptive name (e.g., "Warehouse-A Edge Collector")
3. The system will generate a unique Device ID and API Token
4. **IMPORTANT**: Copy the API Token immediately - it will only be shown once!
5. Configure your Edge Collector with this token

**中文:**
1. 点击 **注册新设备** 按钮
2. 输入描述性名称（例如："A仓库边缘采集器"）
3. 系统将生成唯一的设备ID和API令牌
4. **重要**：立即复制API令牌 - 它只会显示一次！
5. 使用此令牌配置您的Edge Collector

---

## 3. Device Management / 设备管理

### Viewing Registered Devices / 查看已注册设备

**English:**
The Device Management panel shows all your registered Edge Collectors with:
- **Device Name**: Your chosen identifier
- **Status**: Active, Inactive, or Revoked
- **Last Seen**: When the device last connected
- **Public Key**: The device's encryption key (truncated for display)

**中文:**
设备管理面板显示所有已注册的Edge Collector：
- **设备名称**: 您选择的标识符
- **状态**: 活跃、非活跃或已吊销
- **最后在线**: 设备最后连接时间
- **公钥**: 设备的加密密钥（显示时截断）

### Device Status / 设备状态

| Status / 状态 | Description / 描述 |
|---------------|-------------------|
| **Active / 活跃** | Device is registered and can decrypt secrets / 设备已注册并可解密密钥 |
| **Inactive / 非活跃** | Device registered but not recently connected / 设备已注册但最近未连接 |
| **Revoked / 已吊销** | Device access has been revoked / 设备访问权限已被吊销 |

### Revoking a Device / 吊销设备

**English:**
If a device is compromised or no longer needed:
1. Find the device in the list
2. Click the **Revoke** button (red icon)
3. Confirm the revocation
4. The device will immediately lose access to all encrypted credentials

**IMPORTANT**: After revoking a device, you should:
- Re-encrypt any secrets that were accessible to that device
- Register a new device if you need to replace it

**中文:**
如果设备被盗用或不再需要：
1. 在列表中找到该设备
2. 点击 **吊销** 按钮（红色图标）
3. 确认吊销操作
4. 该设备将立即失去对所有加密凭证的访问权限

**重要**：吊销设备后，您应该：
- 重新加密该设备可访问的所有密钥
- 如需替换，请注册新设备

---

## 4. Capability Levels / 能力等级

### Understanding Capability Levels / 理解能力等级

**English:**
Capability levels control what operations an Edge Collector can perform. This follows the principle of least privilege - devices only get access to what they need.

**中文:**
能力等级控制Edge Collector可以执行的操作。这遵循最小权限原则 - 设备只能访问其需要的内容。

### The Three Levels / 三个等级

#### Level 1: DISCOVERY / 等级1：发现

**English:**
- Can scan network for miners
- Can detect miner models and basic info
- **Cannot** access credentials
- **Cannot** modify miner settings

**中文:**
- 可以扫描网络中的矿机
- 可以检测矿机型号和基本信息
- **不能** 访问凭证
- **不能** 修改矿机设置

**Use Case / 使用场景:**
Initial setup phase when cataloging miners / 初始设置阶段，用于编目矿机

---

#### Level 2: TELEMETRY / 等级2：遥测

**English:**
- Everything in Level 1
- Can read miner status and metrics
- Can access read-only credentials
- **Cannot** send commands to miners

**中文:**
- 等级1的所有权限
- 可以读取矿机状态和指标
- 可以访问只读凭证
- **不能** 向矿机发送命令

**Use Case / 使用场景:**
Monitoring-only deployments / 仅监控部署

---

#### Level 3: CONTROL / 等级3：控制

**English:**
- Everything in Levels 1 and 2
- Can access full credentials
- Can send commands to miners (reboot, update settings)
- Can perform maintenance operations

**中文:**
- 等级1和2的所有权限
- 可以访问完整凭证
- 可以向矿机发送命令（重启、更新设置）
- 可以执行维护操作

**Use Case / 使用场景:**
Full management access / 完全管理访问

---

### Setting Capability Levels / 设置能力等级

**English:**
1. In the Device Management section, find the device
2. Click the **Capability** dropdown
3. Select the appropriate level (1, 2, or 3)
4. Click **Save**

**中文:**
1. 在设备管理部分找到设备
2. 点击 **能力等级** 下拉菜单
3. 选择适当的等级（1、2或3）
4. 点击 **保存**

### Device Binding / 设备绑定

**English:**
For Level 3 (CONTROL) miners, you can bind specific devices:
- Only bound devices can access that miner's credentials
- Provides an additional layer of security for high-value miners
- Binding is optional but recommended for critical operations

**中文:**
对于等级3（控制）的矿机，您可以绑定特定设备：
- 只有绑定的设备才能访问该矿机的凭证
- 为高价值矿机提供额外的安全层
- 绑定是可选的，但建议用于关键操作

---

## 5. Key Rotation / 密钥轮换

### Why Rotate Keys? / 为什么要轮换密钥？

**English:**
Regular key rotation is a security best practice:
- Limits exposure if a key is compromised
- Complies with security policies
- Reduces the window of vulnerability

**中文:**
定期密钥轮换是安全最佳实践：
- 如果密钥被泄露，可限制暴露范围
- 符合安全策略
- 减少漏洞窗口

### How to Rotate Keys / 如何轮换密钥

**English:**
1. In Device Management, find the device
2. Click **Rotate Key** button
3. The device will generate a new keypair
4. All new secrets will use the new key
5. Existing secrets remain accessible with the old key

**中文:**
1. 在设备管理中找到设备
2. 点击 **轮换密钥** 按钮
3. 设备将生成新的密钥对
4. 所有新密钥将使用新密钥
5. 现有密钥仍可使用旧密钥访问

### Recommended Rotation Schedule / 推荐的轮换计划

| Environment / 环境 | Frequency / 频率 |
|-------------------|-----------------|
| Standard / 标准 | Every 90 days / 每90天 |
| High Security / 高安全 | Every 30 days / 每30天 |
| After Incident / 事件后 | Immediately / 立即 |

---

## 6. Audit Logs / 审计日志

### Accessing Audit Logs / 访问审计日志

**English:**
1. Go to Site Settings → Device Encryption
2. Click **Audit Log** tab
3. View all security events related to device encryption

**中文:**
1. 进入站点设置 → 设备加密
2. 点击 **审计日志** 标签
3. 查看与设备加密相关的所有安全事件

### Event Types / 事件类型

| Event / 事件 | Description / 描述 |
|--------------|-------------------|
| `DEVICE_REGISTERED` | New device registered / 新设备注册 |
| `DEVICE_REVOKED` | Device access revoked / 设备访问权限被吊销 |
| `KEY_ROTATED` | Device key rotated / 设备密钥已轮换 |
| `SECRET_CREATED` | New secret encrypted / 新密钥已加密 |
| `SECRET_ACCESSED` | Secret decrypted by device / 密钥被设备解密 |
| `SECRET_UPDATED` | Secret re-encrypted / 密钥已重新加密 |
| `CAPABILITY_CHANGED` | Device capability level changed / 设备能力等级已更改 |
| `ACCESS_DENIED` | Unauthorized access attempt / 未授权的访问尝试 |

### Filtering Logs / 筛选日志

**English:**
Use the filter options to narrow down events:
- **Date Range**: Select start and end dates
- **Event Type**: Filter by specific event types
- **Device**: Filter by specific device
- **Result**: Show only successes or failures

**中文:**
使用筛选选项缩小事件范围：
- **日期范围**: 选择开始和结束日期
- **事件类型**: 按特定事件类型筛选
- **设备**: 按特定设备筛选
- **结果**: 仅显示成功或失败

### Privacy Protections / 隐私保护

**English:**
The audit log automatically protects sensitive information:
- IP addresses are partially masked (e.g., 192.168.***.***) 
- Passwords and secrets are never logged
- Error messages are redacted to prevent information leakage

**中文:**
审计日志自动保护敏感信息：
- IP地址部分隐藏（例如：192.168.***.***）
- 密码和密钥永远不会被记录
- 错误消息被编辑以防止信息泄露

---

## 7. Troubleshooting / 故障排除

### Device Not Connecting / 设备无法连接

**English:**
1. Check that the Edge Collector has internet access
2. Verify the API token is correctly configured
3. Check if the device has been revoked
4. Review firewall rules for outbound HTTPS

**中文:**
1. 检查Edge Collector是否有互联网访问
2. 验证API令牌是否正确配置
3. 检查设备是否已被吊销
4. 检查出站HTTPS的防火墙规则

### "Access Denied" Errors / "访问被拒绝"错误

**English:**
This usually means:
- Device capability level is too low for the requested operation
- Device is not bound to the miner (for Level 3 operations)
- Device has been revoked

**Solution:**
1. Check the device's capability level
2. Verify device binding if required
3. Check device status in the management panel

**中文:**
这通常意味着：
- 设备能力等级对于请求的操作太低
- 设备未绑定到矿机（对于等级3操作）
- 设备已被吊销

**解决方案：**
1. 检查设备的能力等级
2. 如果需要，验证设备绑定
3. 在管理面板中检查设备状态

### Cannot Decrypt Secrets / 无法解密密钥

**English:**
1. Ensure the Edge Collector has the correct private key
2. Check if keys were rotated after the secret was created
3. Verify the anti-rollback counter is synchronized
4. Contact support if the issue persists

**中文:**
1. 确保Edge Collector具有正确的私钥
2. 检查密钥是否在创建密钥后被轮换
3. 验证防回滚计数器是否同步
4. 如果问题仍然存在，请联系支持

### Browser Shows Encryption Error / 浏览器显示加密错误

**English:**
This may indicate:
- Browser doesn't support required cryptography (use modern browser)
- libsodium library failed to load
- Content Security Policy blocking script

**Solution:**
1. Try a different browser (Chrome recommended)
2. Disable browser extensions temporarily
3. Clear browser cache and reload

**中文:**
这可能表示：
- 浏览器不支持所需的加密（使用现代浏览器）
- libsodium库加载失败
- 内容安全策略阻止脚本

**解决方案：**
1. 尝试不同的浏览器（推荐Chrome）
2. 暂时禁用浏览器扩展
3. 清除浏览器缓存并重新加载

---

## 8. Security Best Practices / 安全最佳实践

### Do's / 应该做的

**English:**
✅ Rotate keys at least every 90 days
✅ Use the minimum capability level needed
✅ Review audit logs regularly
✅ Revoke devices immediately when no longer needed
✅ Use device binding for high-value miners
✅ Keep Edge Collector software updated

**中文:**
✅ 至少每90天轮换一次密钥
✅ 使用所需的最低能力等级
✅ 定期审查审计日志
✅ 不再需要时立即吊销设备
✅ 对高价值矿机使用设备绑定
✅ 保持Edge Collector软件更新

### Don'ts / 不应该做的

**English:**
❌ Never share API tokens between devices
❌ Don't use Level 3 when Level 1 or 2 is sufficient
❌ Never store API tokens in plain text files
❌ Don't ignore "Access Denied" events in audit logs
❌ Never reuse a revoked device's credentials

**中文:**
❌ 切勿在设备之间共享API令牌
❌ 当等级1或2足够时不要使用等级3
❌ 切勿将API令牌存储在纯文本文件中
❌ 不要忽略审计日志中的"访问被拒绝"事件
❌ 切勿重复使用已吊销设备的凭证

### Incident Response / 事件响应

**English:**
If you suspect a security breach:
1. **Immediately** revoke any compromised devices
2. Rotate keys on all remaining devices
3. Review audit logs for unauthorized access
4. Re-encrypt all secrets with new keys
5. Contact support for assistance

**中文:**
如果您怀疑发生安全漏洞：
1. **立即** 吊销任何受损设备
2. 轮换所有剩余设备的密钥
3. 审查审计日志以查找未授权访问
4. 使用新密钥重新加密所有密钥
5. 联系支持获取帮助

---

## Support / 技术支持

**English:**
For additional help:
- Email: support@hashinsight.io
- Documentation: See `architecture/device_envelope_encryption.md` for technical details

**中文:**
如需更多帮助：
- 邮箱：support@hashinsight.io
- 文档：参见 `architecture/device_envelope_encryption.md` 获取技术细节

---

*Last Updated / 最后更新: December 2025*
