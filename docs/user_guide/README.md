# HashInsight Enterprise 文档中心

> 企业级比特币矿场管理平台 - 完整文档索引

---

## 📚 文档目录

| 文档 | 描述 | 适用对象 |
|------|------|----------|
| [用户手册](./USER_MANUAL.md) | 完整的功能说明和操作指南 | 所有用户 |
| [API参考](./API_REFERENCE.md) | 所有API端点详细文档 | 开发者/集成 |

---

## 🚀 快速导航

### 按角色查看

#### 平台管理员 (Admin/Owner)
- [站点所有者管理](./USER_MANUAL.md#43-托管服务管理-hosting-services)
- [系统监控](./USER_MANUAL.md#43-托管服务管理-hosting-services)

#### 矿场站点所有者 (Mining Site Owner)
- [客户管理](./USER_MANUAL.md#42-crm客户管理-crm-module)
- [托管仪表板](./USER_MANUAL.md#43-托管服务管理-hosting-services)
- [事件监控与AI诊断](./USER_MANUAL.md#45-ai智能诊断-ai-features)
- [限电管理](./USER_MANUAL.md#46-限电管理-curtailment-management)

#### 客户 (Client)
- [托管服务仪表板](./USER_MANUAL.md#43-托管服务管理-hosting-services)
- [收益计算器](./USER_MANUAL.md#44-收益计算器-calculator)

---

## 📖 主要功能模块

### 1. 认证与登录
- 邮箱密码登录
- Web3钱包登录
- 角色权限管理

➡️ [查看详情](./USER_MANUAL.md#41-登录认证-authentication)

### 2. CRM客户管理
- 客户列表与详情
- 商机跟踪
- 交易管理
- 数据分析仪表板

➡️ [查看详情](./USER_MANUAL.md#42-crm客户管理-crm-module)

### 3. 托管服务管理
- 站点管理
- 矿机监控
- 事件告警
- 工单系统

➡️ [查看详情](./USER_MANUAL.md#43-托管服务管理-hosting-services)

### 4. 收益计算器
- 单机计算
- 批量计算
- ROI分析
- 报告导出

➡️ [查看详情](./USER_MANUAL.md#44-收益计算器-calculator)

### 5. AI智能诊断
- 告警根因分析
- Top3假设生成
- 证据链展示
- 建议动作

➡️ [查看详情](./USER_MANUAL.md#45-ai智能诊断-ai-features)

### 6. 限电管理
- 计划调度
- 手动限电
- AI优化建议
- 自动执行

➡️ [查看详情](./USER_MANUAL.md#46-限电管理-curtailment-management)

---

## 🔗 常用路由速查表

| 功能 | 路径 | 权限 |
|------|------|------|
| 登录 | `/login` | 公开 |
| CRM客户列表 | `/crm/customers` | Site Owner+ |
| CRM仪表板 | `/crm/dashboard` | Site Owner+ |
| 托管仪表板 | `/hosting/host/dashboard` | Site Owner+ |
| 矿机列表 | `/hosting/host/miners` | Site Owner+ |
| 事件监控 | `/hosting/host/event-monitoring` | Site Owner+ |
| 工单管理 | `/hosting/host/tickets` | Site Owner+ |
| 我的客户 | `/hosting/host/my-customers` | Site Owner |
| 限电管理 | `/hosting/host/curtailment` | Site Owner+ |
| 收益计算器 | `/calculator` | 登录用户 |
| 批量计算 | `/batch-calculator` | 登录用户 |
| 首页 | `/` | 公开 |

---

## 🛠️ API集成

如需通过API集成系统，请参阅：

- [认证API](./API_REFERENCE.md#1-认证-api-authentication)
- [CRM API](./API_REFERENCE.md#2-crm-api)
- [托管API](./API_REFERENCE.md#3-托管服务-api-hosting)
- [AI功能API](./API_REFERENCE.md#4-ai-功能-api)
- [计算器API](./API_REFERENCE.md#5-计算器-api-calculator)
- [遥测API](./API_REFERENCE.md#6-遥测数据-api-telemetry)

---

## 📞 技术支持

如有问题，请联系：
- 📧 邮箱: support@hashinsight.com
- 📱 电话: +1-XXX-XXX-XXXX
- 🌐 在线支持: 登录后点击右下角"帮助"按钮

---

## 📝 更新日志

| 日期 | 版本 | 更新内容 |
|------|------|----------|
| 2026-01-28 | v1.0 | 初始文档发布 |

---

*HashInsight Enterprise - 让矿场管理更智能*
