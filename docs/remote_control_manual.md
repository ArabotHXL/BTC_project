# Remote Miner Control Manual / 矿机远程控制手册

## Overview / 概述

The Remote Control feature allows mining farm operators to remotely manage and control individual miners from anywhere through the web interface. Commands are routed through Edge Collector devices deployed at mining facilities.

远程控制功能允许矿场运营者通过Web界面从任何地方远程管理和控制单个矿机。命令通过部署在矿场的Edge Collector设备进行路由。

---

## Accessing Remote Control / 访问远程控制

1. **Login** to your account at `/login`
   登录您的账户

2. **Navigate** to Hosting → Devices (`/hosting/host/devices`)
   导航到 托管 → 设备管理

3. **Click** on any miner row to open the Miner Detail page
   点击任意矿机行打开矿机详情页

4. **Scroll down** and click "Remote Control" section header to expand
   向下滚动并点击"Remote Control"区域标题展开

---

## Available Control Actions / 可用控制操作

### 1. Reboot / 重启

**Purpose**: Restart the miner when it's unresponsive or needs a refresh.

**用途**: 当矿机无响应或需要刷新时重启矿机。

**Options**:
- **Soft Reboot** (Recommended): Graceful restart, allows pending operations to complete
- **Hard Reboot**: Immediate restart, may interrupt mining operations

**选项**:
- **软重启** (推荐): 优雅重启，允许待处理操作完成
- **硬重启**: 立即重启，可能中断挖矿操作

**Warning**: The miner will be temporarily offline during reboot (typically 1-3 minutes).

---

### 2. Power Mode / 功率模式

**Purpose**: Adjust the miner's power consumption and performance level.

**用途**: 调整矿机的功耗和性能水平。

**Options**:
| Mode | Description | Use Case |
|------|-------------|----------|
| High Performance ⚡ | Maximum hashrate, highest power | When electricity is cheap |
| Normal | Balanced performance | Default operation |
| Eco Mode 🌱 | Reduced power, lower hashrate | During high electricity rates |

**选项**:
| 模式 | 描述 | 使用场景 |
|------|------|----------|
| 高性能 ⚡ | 最大算力，最高功耗 | 电费便宜时 |
| 正常 | 平衡性能 | 默认运行 |
| 节能模式 🌱 | 降低功耗，算力下降 | 电费高峰期 |

---

### 3. Change Pool / 更改矿池

**Purpose**: Switch the miner to a different mining pool.

**用途**: 将矿机切换到不同的矿池。

**Required Fields**:
- **Pool URL**: The stratum address (e.g., `stratum+tcp://pool.example.com:3333`)
- **Worker Name**: Your worker identifier (e.g., `farm1.worker001`)
- **Password**: Pool password (usually `x` for most pools)

**必填字段**:
- **矿池URL**: Stratum地址 (例如: `stratum+tcp://pool.example.com:3333`)
- **Worker名称**: 您的worker标识 (例如: `farm1.worker001`)
- **密码**: 矿池密码 (大多数矿池使用 `x`)

---

### 4. Frequency / 频率调整

**Purpose**: Adjust the ASIC chip operating frequency.

**用途**: 调整ASIC芯片运行频率。

**Options**:
| Profile | Frequency | Effect |
|---------|-----------|--------|
| Stock | 600 MHz | Default factory settings |
| Overclock | 700 MHz | Higher hashrate, more heat |
| Underclock | 500 MHz | Lower power, cooler operation |

**Warning**: Overclocking may increase power consumption and temperature. Monitor your miner closely after changes.

**警告**: 超频可能增加功耗和温度。更改后请密切监控矿机。

---

### 5. Thermal / 温控策略

**Purpose**: Control fan speed and cooling behavior.

**用途**: 控制风扇速度和散热行为。

**Fan Mode Options**:
- **Auto**: System manages fan speed based on temperature
- **Manual**: Set a fixed fan speed percentage
- **Aggressive Cooling**: Maximum cooling for hot environments

**Fan Speed**: Adjustable from 30% to 100% (in Manual mode)

**风扇模式选项**:
- **自动**: 系统根据温度管理风扇速度
- **手动**: 设置固定风扇速度百分比
- **强力散热**: 适用于高温环境的最大散热

---

### 6. LED / LED控制

**Purpose**: Turn the miner's LED indicator on or off.

**用途**: 开启或关闭矿机的LED指示灯。

**Use Case**: Locate a specific miner in a large facility by turning on its LED.

**使用场景**: 通过开启LED在大型矿场中定位特定矿机。

---

## Command History / 命令历史

The Command History table shows recent commands sent to this miner:

命令历史表显示发送到此矿机的最近命令：

| Column | Description |
|--------|-------------|
| Time | When the command was sent |
| Command | Type of action (Reboot, Power Mode, etc.) |
| Status | Current state (Queued, Running, Succeeded, Failed) |
| Result | Execution summary |

### Status Meanings / 状态含义

| Status | Meaning |
|--------|---------|
| `QUEUED` | Command waiting to be picked up by Edge Collector |
| `RUNNING` | Edge Collector is executing the command |
| `SUCCEEDED` | Command completed successfully |
| `FAILED` | Command execution failed |

---

## Architecture / 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │────▶│  Cloud API  │◀────│    Edge     │
│  (User UI)  │     │   Server    │     │  Collector  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Miners    │
                                        │ (CGMiner)   │
                                        └─────────────┘
```

1. User clicks a control button in the browser
2. Browser sends command to Cloud API
3. Edge Collector polls Cloud API for pending commands
4. Edge Collector executes command on miner via CGMiner API
5. Results are reported back to Cloud API
6. Browser displays updated status in Command History

---

## Security / 安全性

- **RBAC Permission**: Requires `miner:control` permission
- **Device Envelope Encryption**: Miner credentials are E2E encrypted
- **Audit Logging**: All commands are logged with user, timestamp, and result
- **Approval Workflow**: Optional approval requirement for sensitive commands

---

## Troubleshooting / 故障排除

### Command Stuck in "Queued"
- Check if Edge Collector is online and connected
- Verify the miner is associated with an active Edge device

### Command Failed
- Check miner connectivity (is it online?)
- Review the error message in command results
- Verify CGMiner API is accessible on the miner

### Cannot Access Remote Control
- Confirm your user role has `miner:control` permission
- Contact administrator to grant necessary RBAC permissions

---

## API Reference / API参考

### Create Command
```
POST /api/sites/{site_id}/commands
Content-Type: application/json

{
  "command_type": "REBOOT",
  "payload": { "mode": "soft" },
  "target_scope": "MINER",
  "target_ids": ["miner_serial_number"]
}
```

### Get Command History
```
GET /api/sites/{site_id}/commands?limit=10
```

### Cancel Command
```
DELETE /api/sites/{site_id}/commands/{command_id}
```

---

*Last Updated: December 2025*
