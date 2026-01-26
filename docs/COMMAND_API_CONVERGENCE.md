# 命令 API 收敛计划

## 审计日期: 2026-01-26

## 现有命令入口

### 1. remote_control_api.py (Legacy UI API - 需要成为兼容层)
| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/sites/<site_id>/commands` | POST | 创建命令 | 待转发到 v1 |
| `/api/sites/<site_id>/commands` | GET | 列出命令 | 待转发到 v1 |
| `/api/commands/<command_id>` | GET | 获取命令详情 | 待转发到 v1 |
| `/api/commands/<command_id>/cancel` | POST | 取消命令 | 待转发到 v1 |
| `/api/commands/<command_id>/approve` | POST | 审批命令 | 待转发到 v1 |

### 2. control_plane_api.py (v1 - 权威真相)

#### Edge API (采集器端)
| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/edge/v1/register` | POST | 设备注册 | 权威 |
| `/api/edge/v1/commands/poll` | GET | 轮询命令 | 权威 |
| `/api/edge/v1/commands/<id>/ack` | POST | 确认命令 | 权威 |
| `/api/edge/v1/telemetry/ingest` | POST | 遥测数据 | 权威 |
| `/api/edge/v1/telemetry/batch` | POST | 遥测数据别名 | 权威 |
| `/api/edge/v1/events/safety/batch` | POST | 安全事件 | 权威 |

#### v1 API (管理端)
| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/v1/commands/propose` | POST | 提议命令 | 权威 |
| `/api/v1/commands/<id>/approve` | POST | 审批命令 | 权威 |
| `/api/v1/commands/<id>/deny` | POST | 拒绝命令 | 权威 |
| `/api/v1/commands/<id>/rollback` | POST | 回滚命令 | 权威 |
| `/api/v1/commands/<id>` | GET | 获取命令 | 权威 |
| `/api/v1/commands` | GET | 列出命令 | 权威 |

### 3. legacy_adapter.py (Legacy Edge - 已标记弃用)
| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/remote/commands/pending` | GET | 轮询命令 | 已弃用 → 转发到 edge/v1 |
| `/api/remote/commands/<id>/result` | POST | 提交结果 | 已弃用 → 转发到 edge/v1 |
| `/api/remote/health` | GET | 健康检查 | 保留 |

### 4. portal_lite_api.py (客户门户 - 已对接 v1)
| 端点 | 方法 | 功能 | 状态 |
|------|------|------|------|
| `/api/v1/portal/my-miners` | GET | 我的矿机 | 已使用 v1 模型 |
| `/api/v1/portal/my-approvals` | GET | 待审批命令 | 已使用 v1 模型 |
| `/api/v1/portal/approvals/<id>/approve` | POST | 审批命令 | 已使用 v1 模型 |
| `/api/v1/portal/approvals/<id>/deny` | POST | 拒绝命令 | 已使用 v1 模型 |

## 收敛策略

### 阶段 1: remote_control_api.py → 兼容层
1. 所有端点保持原有路由
2. 内部逻辑改为调用 control_plane_api.py 的函数
3. 添加 `Deprecation` header
4. 映射表:
   - `create_command` → `propose_command`
   - `list_commands` → `list_commands` (v1)
   - `get_command` → `get_command` (v1)
   - `cancel_command` → `deny_command`
   - `approve_command` → `approve_command` (v1)

### 阶段 2: 统一审计
- 所有命令操作记录到 `AuditEvent` 表
- 统一日志格式: `{actor, action, target, result, evidence}`

### 阶段 3: 弃用时间线
- 2026-01-26: 添加弃用提示
- 2026-06-01: 只读模式
- 2026-12-01: 完全移除

## 命令状态流转 (统一)
```
PENDING → PENDING_APPROVAL → APPROVED → DISPATCHED → ACK_RECEIVED → COMPLETED
                          ↘ DENIED
                                    ↘ FAILED / TIMEOUT
```

## 数据模型 (统一)
使用 `MinerCommand` (control_plane_api) 作为权威模型
`RemoteCommand` (remote_control_api) 保持兼容，同步状态到 `MinerCommand`
