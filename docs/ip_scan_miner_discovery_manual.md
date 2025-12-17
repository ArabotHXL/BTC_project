# IP Scan Miner Discovery Manual / IP扫描发现矿机用户手册

---

## Table of Contents / 目录

1. [Overview / 功能概述](#1-overview--功能概述)
2. [Prerequisites / 使用前提](#2-prerequisites--使用前提)
3. [Permissions & Tenant Isolation / 权限与租户隔离](#3-permissions--tenant-isolation--权限与租户隔离)
4. [UI Workflow / 界面操作流程](#4-ui-workflow--界面操作流程)
5. [Edge Device Delegation / 边缘设备委托扫描](#5-edge-device-delegation--边缘设备委托扫描)
6. [API Reference / API参考](#6-api-reference--api参考)
7. [Result Interpretation & Import / 结果解读与导入](#7-result-interpretation--import--结果解读与导入)
8. [Troubleshooting / 故障排除](#8-troubleshooting--故障排除)

---

## 1. Overview / 功能概述

### English

The IP Scan Miner Discovery feature allows you to automatically discover Bitcoin miners on your local network by scanning IP address ranges. This feature is essential for:

- **Initial Setup**: Quickly find all miners in your facility
- **Inventory Management**: Detect new miners added to the network
- **Troubleshooting**: Find miners with changed IP addresses
- **Batch Import**: Import discovered miners directly into the hosting system

#### Key Features

| Feature | Description |
|---------|-------------|
| Multiple IP Formats | CIDR, range notation, or explicit start/end IPs |
| Cloud or Edge Scanning | Scan from cloud or delegate to Edge Collector |
| Concurrent Scanning | Up to 50 concurrent probes for fast discovery |
| Auto-Detection | Detects miner model, firmware, and hashrate |
| One-Click Import | Import discovered miners to hosting system |
| Audit Logging | All scan activities are logged for compliance |

#### How It Works

```
1. User creates a scan job with IP range
2. System (cloud or edge device) probes each IP on port 4028 (CGMiner API)
3. Responding miners are detected and their info is collected
4. User reviews discovered miners and imports selected ones
```

### 中文

IP扫描发现矿机功能允许您通过扫描IP地址范围自动发现局域网中的比特币矿机。此功能适用于：

- **初始部署**：快速发现矿场中的所有矿机
- **库存管理**：检测新加入网络的矿机
- **故障排查**：找到IP地址变更的矿机
- **批量导入**：将发现的矿机直接导入托管系统

#### 核心特性

| 特性 | 说明 |
|------|------|
| 多种IP格式 | 支持CIDR、范围表示法或起止IP |
| 云端或边缘扫描 | 从云端扫描或委托边缘采集器执行 |
| 并发扫描 | 最高50个并发探测，快速发现 |
| 自动检测 | 检测矿机型号、固件和算力 |
| 一键导入 | 发现的矿机可直接导入托管系统 |
| 审计日志 | 所有扫描活动均记录在案 |

#### 工作原理

```
1. 用户创建扫描任务，指定IP范围
2. 系统（云端或边缘设备）探测每个IP的4028端口（CGMiner API）
3. 响应的矿机被检测，收集其信息
4. 用户审查发现的矿机并选择导入
```

---

## 2. Prerequisites / 使用前提

### English

Before using the IP Scan feature, ensure:

1. **Network Access**: The scanning device must have network access to the target IP range
2. **CGMiner API**: Miners must have CGMiner API enabled on port 4028
3. **Firewall Rules**: Port 4028 must not be blocked by firewalls
4. **User Account**: You must be logged in with appropriate permissions
5. **Site Created** (optional): If you want to associate scans with a site

#### Supported Miner Types

The scanner detects miners with CGMiner-compatible APIs:

- Bitmain Antminer series (S9, S17, S19, etc.)
- MicroBT Whatsminer series (M20, M30, M50, etc.)
- Canaan Avalon series
- Other CGMiner-compatible ASIC miners

### 中文

使用IP扫描功能前，请确保：

1. **网络访问**：扫描设备必须能访问目标IP范围
2. **CGMiner API**：矿机必须启用4028端口的CGMiner API
3. **防火墙规则**：4028端口不能被防火墙阻止
4. **用户账户**：您必须登录并具有相应权限
5. **已创建站点**（可选）：如需将扫描与站点关联

#### 支持的矿机类型

扫描器检测具有CGMiner兼容API的矿机：

- 比特大陆蚂蚁矿机系列（S9, S17, S19等）
- 微比特神马矿机系列（M20, M30, M50等）
- 嘉楠阿瓦隆系列
- 其他CGMiner兼容的ASIC矿机

---

## 3. Permissions & Tenant Isolation / 权限与租户隔离

### English

#### Access Control

| Role | Permissions |
|------|-------------|
| Admin | Create/view/delete all scans, import miners |
| Manager | Create/view scans for assigned sites |
| Operator | View scan results only |
| Client | No access to scan features |

#### Tenant Isolation

- Each user can only see their own scan jobs
- Scan results are isolated by tenant ID
- Imported miners are assigned to the user's account
- Edge devices are tenant-specific

#### Security Considerations

- Only scan IP ranges you own or have authorization to scan
- Scanning unauthorized networks may violate laws
- All scan activities are logged in the audit trail
- Maximum 65,536 IPs per scan job to prevent abuse

### 中文

#### 访问控制

| 角色 | 权限 |
|------|------|
| 管理员 | 创建/查看/删除所有扫描，导入矿机 |
| 经理 | 创建/查看所分配站点的扫描 |
| 操作员 | 仅查看扫描结果 |
| 客户 | 无扫描功能访问权限 |

#### 租户隔离

- 每个用户只能看到自己的扫描任务
- 扫描结果按租户ID隔离
- 导入的矿机分配给用户账户
- 边缘设备按租户隔离

#### 安全注意事项

- 仅扫描您拥有或获得授权的IP范围
- 扫描未授权网络可能违反法律
- 所有扫描活动记录在审计日志中
- 每个扫描任务最多65,536个IP，防止滥用

---

## 4. UI Workflow / 界面操作流程

### English

#### Step 1: Navigate to Site Management

1. Log in to the system
2. Go to **Hosting** → **Site Management**
3. Select the site where you want to scan for miners

#### Step 2: Open the Miner Discovery Dialog

1. Click the **"Find Miners"** button (or "发现矿机")
2. The IP Scan dialog will open

#### Step 3: Configure the Scan

| Field | Description | Example |
|-------|-------------|---------|
| IP Range | CIDR or range format | `192.168.1.0/24` |
| Edge Device | (Optional) Select device to perform scan | `Edge-Collector-01` |

**Supported IP Range Formats:**

```
CIDR:       192.168.1.0/24          (256 IPs)
Range:      192.168.1.1-192.168.1.254  (254 IPs)
Short:      192.168.1.1-254         (254 IPs)
```

#### Step 4: Start the Scan

1. Click **"Start Scan"**
2. The scan job will be created and start processing
3. Progress is shown in real-time

#### Step 5: Review Results

1. Once completed, view the list of discovered miners
2. Each miner shows: IP, Model, Firmware, Hashrate, MAC Address
3. Check miners you want to import

#### Step 6: Import Miners

1. Select miners to import (or click "Select All")
2. Choose the target site (if not pre-selected)
3. Click **"Import Selected"**
4. Miners are added to the hosting system

### 中文

#### 步骤1：进入站点管理

1. 登录系统
2. 前往 **托管** → **站点管理**
3. 选择要扫描矿机的站点

#### 步骤2：打开矿机发现对话框

1. 点击 **"发现矿机"** 按钮
2. IP扫描对话框将打开

#### 步骤3：配置扫描

| 字段 | 说明 | 示例 |
|------|------|------|
| IP范围 | CIDR或范围格式 | `192.168.1.0/24` |
| 边缘设备 | （可选）选择执行扫描的设备 | `Edge-Collector-01` |

**支持的IP范围格式：**

```
CIDR:       192.168.1.0/24          (256个IP)
范围:       192.168.1.1-192.168.1.254  (254个IP)
简写:       192.168.1.1-254         (254个IP)
```

#### 步骤4：开始扫描

1. 点击 **"开始扫描"**
2. 扫描任务创建并开始处理
3. 实时显示进度

#### 步骤5：查看结果

1. 完成后，查看发现的矿机列表
2. 每台矿机显示：IP、型号、固件、算力、MAC地址
3. 勾选要导入的矿机

#### 步骤6：导入矿机

1. 选择要导入的矿机（或点击"全选"）
2. 选择目标站点（如未预选）
3. 点击 **"导入选中"**
4. 矿机被添加到托管系统

---

## 5. Edge Device Delegation / 边缘设备委托扫描

### English

For networks not directly accessible from the cloud, you can delegate scanning to an Edge Collector device installed on-premises.

#### Why Use Edge Device Scanning?

- **Private Networks**: Scan miners on private/internal networks
- **Firewall Bypass**: No need to open cloud access to miner networks
- **Faster Scanning**: Edge device has lower latency to local miners
- **Security**: Miner IPs never exposed to cloud directly

#### Setting Up Edge Device for Scanning

1. **Register Edge Device** (see Device Envelope Encryption manual)
2. **Ensure Network Access**: Edge device must reach target IP range
3. **Device Must Be Active**: Status = "ACTIVE"

#### Edge Scanning Workflow

```
1. User creates scan job with device_id specified
2. Scan job status = PENDING
3. Edge Collector polls for pending jobs
4. Edge Collector starts scan, updates status = RUNNING
5. Edge Collector probes each IP concurrently
6. Edge Collector reports results back to cloud
7. Status = COMPLETED, discovered miners saved
8. User imports miners via web UI
```

#### Edge Collector Commands

The Edge Collector periodically checks for pending scans:

```bash
# Edge Collector auto-polls for scan jobs
python edge_collector/main.py --mode scan

# Or trigger specific scan
curl -X POST https://your-server/api/edge/scan \
  -H "X-Device-Token: <device_token>" \
  -d '{"scan_job_id": 123}'
```

### 中文

对于云端无法直接访问的网络，您可以将扫描任务委托给安装在本地的边缘采集器设备执行。

#### 为什么使用边缘设备扫描？

- **私有网络**：扫描私有/内部网络中的矿机
- **绕过防火墙**：无需开放云端对矿机网络的访问
- **更快扫描**：边缘设备到本地矿机延迟更低
- **安全性**：矿机IP不直接暴露给云端

#### 设置边缘设备用于扫描

1. **注册边缘设备**（参见设备信封加密手册）
2. **确保网络访问**：边缘设备必须能访问目标IP范围
3. **设备必须处于活动状态**：状态 = "ACTIVE"

#### 边缘扫描工作流程

```
1. 用户创建扫描任务，指定device_id
2. 扫描任务状态 = PENDING
3. 边缘采集器轮询待处理任务
4. 边缘采集器开始扫描，状态更新为 RUNNING
5. 边缘采集器并发探测每个IP
6. 边缘采集器将结果报告给云端
7. 状态 = COMPLETED，发现的矿机已保存
8. 用户通过Web界面导入矿机
```

#### 边缘采集器命令

边缘采集器定期检查待处理的扫描任务：

```bash
# 边缘采集器自动轮询扫描任务
python edge_collector/main.py --mode scan

# 或触发特定扫描
curl -X POST https://your-server/api/edge/scan \
  -H "X-Device-Token: <device_token>" \
  -d '{"scan_job_id": 123}'
```

---

## 6. API Reference / API参考

### Scan Job Management APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scans` | POST | Create new scan job |
| `/api/scans` | GET | List scan jobs |
| `/api/scans/<id>` | GET | Get scan job details |
| `/api/scans/<id>/miners` | GET | Get discovered miners |
| `/api/scans/<id>/import` | POST | Import discovered miners |
| `/api/scans/<id>` | DELETE | Cancel/delete scan job |

### Edge Collector APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/edge/scan` | POST | Edge device starts scan |
| `/api/edge/scan/<id>/progress` | POST | Report scan progress |
| `/api/edge/scan/<id>/results` | POST | Report scan results |

---

### POST `/api/scans` - Create Scan Job

创建扫描任务 / Create a new scan job

**Request:**
```json
{
  "cidr": "192.168.1.0/24",
  "site_id": 123,
  "device_id": 456
}
```

**Alternative IP formats / 其他IP格式:**
```json
{
  "ip_range": "192.168.1.1-192.168.1.254"
}
```
```json
{
  "ip_range_start": "192.168.1.1",
  "ip_range_end": "192.168.1.254"
}
```

**Response:**
```json
{
  "success": true,
  "scan_job": {
    "id": 789,
    "site_id": 123,
    "ip_range_start": "192.168.1.1",
    "ip_range_end": "192.168.1.254",
    "scan_type": "DISCOVERY",
    "status": "PENDING",
    "total_ips": 254,
    "scanned_ips": 0,
    "discovered_miners": 0,
    "progress_percent": 0,
    "started_at": null,
    "completed_at": null,
    "created_at": "2025-01-01T00:00:00Z"
  }
}
```

**Error Response / 错误响应:**
```json
{
  "error": "IP range too large. Maximum 65536 IPs per scan."
}
```

**Parameters / 参数:**

| Field | Type | Required | Description / 说明 |
|-------|------|----------|-------------|
| `cidr` | string | One of 3 | CIDR notation / CIDR表示法 |
| `ip_range` | string | One of 3 | Range notation / 范围表示法 |
| `ip_range_start` | string | Pair | Start IP address / 起始IP |
| `ip_range_end` | string | Pair | End IP address / 结束IP |
| `site_id` | int | No | Associate with hosting site / 关联托管站点 |
| `device_id` | int | No | Delegate to edge device / 委托边缘设备 |

**Limits / 限制:**
- Maximum 65,536 IPs per scan job / 每次扫描最多65,536个IP
- `site_id` must be owned by current user / `site_id`必须属于当前用户
- `device_id` must be ACTIVE / `device_id`必须处于活动状态

---

### GET `/api/scans` - List Scan Jobs

查询扫描任务列表 / List scan jobs for current tenant

**Query Parameters / 查询参数:**

| Parameter | Type | Description / 说明 |
|-----------|------|-------------|
| `status` | string | Filter: PENDING, RUNNING, COMPLETED, FAILED, CANCELLED |
| `site_id` | int | Filter by site ID / 按站点过滤 |
| `limit` | int | Max results (default 50, max 100) / 最大结果数 |
| `offset` | int | Pagination offset / 分页偏移量 |

**Response:**
```json
{
  "scan_jobs": [
    {
      "id": 789,
      "site_id": 123,
      "ip_range_start": "192.168.1.1",
      "ip_range_end": "192.168.1.254",
      "scan_type": "DISCOVERY",
      "status": "COMPLETED",
      "total_ips": 254,
      "scanned_ips": 254,
      "discovered_miners": 15,
      "progress_percent": 100.0,
      "started_at": "2025-01-01T00:01:00Z",
      "completed_at": "2025-01-01T00:05:00Z",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

---

### GET `/api/scans/<id>` - Get Scan Job Details

获取扫描任务详情 / Get scan job details with progress

**Response:**
```json
{
  "scan_job": {
    "id": 789,
    "site_id": 123,
    "ip_range_start": "192.168.1.1",
    "ip_range_end": "192.168.1.254",
    "scan_type": "DISCOVERY",
    "status": "RUNNING",
    "total_ips": 254,
    "scanned_ips": 150,
    "discovered_miners": 8,
    "progress_percent": 59.1,
    "started_at": "2025-01-01T00:01:00Z",
    "completed_at": null,
    "created_at": "2025-01-01T00:00:00Z",
    "device": {
      "id": 456,
      "device_name": "Edge-Collector-01",
      "status": "ACTIVE"
    }
  }
}
```

---

### GET `/api/scans/<id>/miners` - Get Discovered Miners

获取发现的矿机列表 / Get discovered miners for a scan job

**Query Parameters / 查询参数:**

| Parameter | Type | Description / 说明 |
|-----------|------|-------------|
| `imported` | boolean | Filter by import status / 按导入状态过滤 |
| `limit` | int | Max results (default 100, max 500) / 最大结果数 |
| `offset` | int | Pagination offset / 分页偏移量 |

**Response:**
```json
{
  "miners": [
    {
      "id": 1,
      "ip_address": "192.168.1.10",
      "api_port": 4028,
      "detected_model": "Bitmain Antminer S19 Pro",
      "detected_firmware": "20230415",
      "detected_hashrate_ghs": 110000,
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "hostname": "miner-rack1-10",
      "is_imported": false,
      "imported_miner_id": null,
      "discovered_at": "2025-01-01T00:03:00Z"
    }
  ],
  "total": 15,
  "limit": 100,
  "offset": 0
}
```

---

### POST `/api/scans/<id>/import` - Import Miners

导入发现的矿机到托管系统 / Import discovered miners to hosting_miners table

**Request:**
```json
{
  "miner_ids": [1, 2, 3],
  "customer_id": 100,
  "miner_model_id": 5
}
```

**Or import all / 或导入全部:**
```json
{
  "all": true
}
```

**Parameters / 参数:**

| Field | Type | Required | Description / 说明 |
|-------|------|----------|-------------|
| `miner_ids` | array | One of | Specific miner IDs to import / 指定导入的矿机ID |
| `all` | boolean | One of | Import all unimported miners / 导入所有未导入的矿机 |
| `customer_id` | int | No | Assign to customer (default: current user) / 分配给客户 |
| `miner_model_id` | int | No | Override detected model / 覆盖检测到的型号 |

**Response:**
```json
{
  "success": true,
  "imported_count": 3,
  "errors": []
}
```

**Error Response / 错误响应:**
```json
{
  "error": "Scan must be completed or running to import miners"
}
```

**Notes / 注意:**
- Miners with existing IPs in the same site are automatically skipped
- 同一站点中已存在相同IP的矿机会自动跳过
- Serial number is auto-generated as `SCAN-{job_id}-{ip}`
- 序列号自动生成为 `SCAN-{任务ID}-{IP}`

---

### DELETE `/api/scans/<id>` - Cancel/Delete Scan Job

取消或删除扫描任务 / Cancel or delete a scan job

**Behavior / 行为:**
- If status is RUNNING: Changes to CANCELLED
- 如果状态为运行中：变更为已取消
- If status is other: Deletes the scan job
- 如果状态为其他：删除扫描任务

**Response:**
```json
{
  "success": true,
  "message": "Scan job cancelled"
}
```

---

### POST `/api/edge/scan` - Start Edge Scan (Edge Device)

边缘设备获取待处理扫描任务 / Edge device requests to start a scan

**Request:**
```json
{
  "scan_job_id": 123
}
```

**Response:**
```json
{
  "scan_job": {...},
  "ip_list": ["192.168.1.1", "192.168.1.2", "..."]
}
```

**Headers:**
```
X-Device-Token: <edge_device_token>
```

---

### POST `/api/edge/scan/<id>/progress` - Report Progress (Edge Device)

边缘设备报告扫描进度 / Edge device reports scan progress

**Request:**
```json
{
  "scanned_ips": 150,
  "discovered_miners": 5
}
```

**Response:**
```json
{
  "success": true
}
```

**Headers:**
```
X-Device-Token: <edge_device_token>
```

---

### POST `/api/edge/scan/<id>/results` - Report Scan Results (Edge Device)

边缘设备报告扫描结果 / Edge device reports scan results

**Request:**
```json
{
  "status": "COMPLETED",
  "miners": [
    {
      "ip_address": "192.168.1.10",
      "api_port": 4028,
      "detected_model": "Bitmain Antminer S19",
      "detected_firmware": "20230415",
      "detected_hashrate_ghs": 95000,
      "mac_address": "AA:BB:CC:DD:EE:FF",
      "hostname": "miner-10"
    }
  ]
}
```

**Or for failed scan / 或扫描失败时:**
```json
{
  "status": "FAILED",
  "error_message": "Network timeout"
}
```

**Headers:**
```
X-Device-Token: <edge_device_token>
```

---

## 7. Result Interpretation & Import / 结果解读与导入

### English

#### Scan Job Lifecycle / 扫描任务生命周期

```
                     ┌─────────────┐
                     │   PENDING   │  ← Job created
                     └─────┬───────┘
                           │ Edge/Cloud picks up job
                           ▼
                     ┌─────────────┐
                     │   RUNNING   │  ← Scanning in progress
                     └──┬───────┬──┘
                        │       │
           Completed    │       │  Error/User cancel
                        ▼       ▼
              ┌───────────┐   ┌───────────┐
              │ COMPLETED │   │  FAILED   │
              └───────────┘   └───────────┘
                                    │
                                    ▼
                             ┌───────────┐
                             │ CANCELLED │ ← User deleted RUNNING job
                             └───────────┘
```

#### Scan Job Statuses

| Status | Description / 说明 |
|--------|-------------|
| PENDING | Scan job created, waiting to start / 任务已创建，等待开始 |
| RUNNING | Scan in progress / 扫描进行中 |
| COMPLETED | Scan finished successfully / 扫描成功完成 |
| FAILED | Scan failed (check `error_message` field) / 扫描失败（查看error_message字段） |
| CANCELLED | Scan was cancelled by user / 用户取消了扫描 |

#### Error Handling / 错误处理

When a scan fails, check the `error_message` field in the scan job response:

```json
{
  "scan_job": {
    "status": "FAILED",
    "error_message": "Network timeout: unable to reach 192.168.1.0/24"
  }
}
```

Common errors / 常见错误:
- `Network timeout` - Edge device cannot reach target network / 边缘设备无法访问目标网络
- `Device offline` - Edge device went offline during scan / 扫描期间边缘设备离线
- `Range validation failed` - Invalid IP range format / IP范围格式无效

#### Audit Log Review / 审计日志查看

All scan operations generate audit events. View them at `/api/audit/events`:

| Event Type | Description |
|------------|-------------|
| SCAN_JOB_CREATED | New scan job created |
| SCAN_JOB_STARTED | Edge device started scanning |
| SCAN_JOB_CANCELLED | User cancelled scan |
| SCAN_JOB_DELETED | User deleted scan job |
| MINERS_IMPORTED | Miners imported from scan |

#### Understanding Discovered Miner Data

| Field | Description | Auto-Detection |
|-------|-------------|----------------|
| `ip_address` | Miner's IP address | Yes |
| `api_port` | CGMiner API port (usually 4028) | Yes |
| `detected_model` | Miner model name | Yes (from API) |
| `detected_firmware` | Firmware version | Yes (from API) |
| `detected_hashrate_ghs` | Current hashrate in GH/s | Yes (from API) |
| `mac_address` | MAC address | If available |
| `hostname` | Miner hostname | If available |

#### Import Considerations

1. **Duplicate Check**: Miners with existing IPs in the same site are skipped
2. **Model Mapping**: System attempts to match detected model to known models
3. **Customer Assignment**: You can assign miners to a customer during import
4. **Serial Number**: Auto-generated if not provided

### 中文

#### 扫描任务状态

| 状态 | 说明 |
|------|------|
| PENDING | 扫描任务已创建，等待开始 |
| RUNNING | 扫描进行中 |
| COMPLETED | 扫描成功完成 |
| FAILED | 扫描失败（查看error_message） |
| CANCELLED | 用户取消了扫描 |

#### 理解发现的矿机数据

| 字段 | 说明 | 自动检测 |
|------|------|----------|
| `ip_address` | 矿机IP地址 | 是 |
| `api_port` | CGMiner API端口（通常4028） | 是 |
| `detected_model` | 矿机型号名称 | 是（来自API） |
| `detected_firmware` | 固件版本 | 是（来自API） |
| `detected_hashrate_ghs` | 当前算力（GH/s） | 是（来自API） |
| `mac_address` | MAC地址 | 如可用 |
| `hostname` | 矿机主机名 | 如可用 |

#### 导入注意事项

1. **重复检查**：同一站点中已存在相同IP的矿机将被跳过
2. **型号映射**：系统尝试将检测到的型号匹配到已知型号
3. **客户分配**：导入时可将矿机分配给客户
4. **序列号**：如未提供，将自动生成

---

## 8. Troubleshooting / 故障排除

### English

#### "IP range too large" Error

**Cause:** Requested scan exceeds 65,536 IPs.

**Solution:** Split the scan into smaller ranges:
```
Instead of: 10.0.0.0/8 (16M IPs)
Use: 10.0.0.0/16 (65K IPs) - one per scan
```

#### No Miners Discovered

**Causes:**
1. Miners are not powered on
2. CGMiner API is disabled on miners
3. Port 4028 is blocked by firewall
4. Wrong IP range specified

**Solutions:**
1. Verify miners are online and accessible
2. Enable CGMiner API in miner settings
3. Check firewall rules
4. Verify IP range is correct

#### Scan Stuck in "RUNNING" State

**Cause:** Edge device may have lost connection or crashed.

**Solutions:**
1. Check edge device status
2. Restart edge collector service
3. Cancel the scan and create a new one

#### Edge Device Not Picking Up Scans

**Causes:**
1. Device token expired or revoked
2. Device not in ACTIVE status
3. Network connectivity issue

**Solutions:**
1. Check device status in web UI
2. Rotate device token if needed
3. Verify edge collector is running

#### Import Fails with "Duplicate IP"

**Cause:** A miner with the same IP already exists in the target site.

**Solution:** 
- Skip the duplicate miner, or
- Delete/update the existing miner first

### 中文

#### "IP范围过大"错误

**原因：** 请求的扫描超过65,536个IP。

**解决方案：** 将扫描拆分为较小的范围：
```
避免: 10.0.0.0/8 (1600万IP)
使用: 10.0.0.0/16 (6.5万IP) - 每次扫描一个
```

#### 未发现任何矿机

**可能原因：**
1. 矿机未开机
2. 矿机上未启用CGMiner API
3. 防火墙阻止了4028端口
4. 指定的IP范围错误

**解决方案：**
1. 确认矿机在线且可访问
2. 在矿机设置中启用CGMiner API
3. 检查防火墙规则
4. 确认IP范围正确

#### 扫描卡在"运行中"状态

**原因：** 边缘设备可能断开连接或崩溃。

**解决方案：**
1. 检查边缘设备状态
2. 重启边缘采集器服务
3. 取消扫描并创建新任务

#### 边缘设备未获取扫描任务

**可能原因：**
1. 设备令牌过期或被撤销
2. 设备未处于活动状态
3. 网络连接问题

**解决方案：**
1. 在Web界面检查设备状态
2. 如需要，轮换设备令牌
3. 确认边缘采集器正在运行

#### 导入失败："IP重复"

**原因：** 目标站点中已存在相同IP的矿机。

**解决方案：**
- 跳过重复的矿机，或
- 先删除/更新现有矿机

---

## Version History / 版本历史

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12 | Initial release |

---

*This manual is part of HashInsight Enterprise documentation.*
*本手册是HashInsight Enterprise文档的一部分。*
