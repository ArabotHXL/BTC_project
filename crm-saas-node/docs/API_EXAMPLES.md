# HashInsight CRM Platform API Examples
# HashInsight CRM平台API示例

[English](#english) | [中文](#chinese)

---

<a name="english"></a>
## English Documentation

### Table of Contents
1. [Authentication Flow](#auth-flow-en)
2. [Complete Business Flow: Lead → Deal → Invoice](#business-flow-en)
3. [CRM Core Operations](#crm-operations-en)
4. [Billing Operations](#billing-operations-en)
5. [Asset Management](#asset-management-en)
6. [Operations Tickets](#ops-tickets-en)

---

<a name="auth-flow-en"></a>
### 1. Authentication Flow

#### 1.1 User Login
Obtain JWT token for API authentication:

```bash
curl -X POST https://api.hashinsight.net/v1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@hashinsight.net",
    "password": "SecureP@ssw0rd"
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "admin@hashinsight.net",
      "name": "System Admin",
      "roleId": "admin-role-id",
      "status": "ACTIVE"
    }
  },
  "timestamp": "2025-10-07T10:00:00Z"
}
```

#### 1.2 User Registration
Create a new user account:

```bash
curl -X POST https://api.hashinsight.net/v1/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecureP@ssw0rd",
    "name": "Zhang San"
  }'
```

---

<a name="business-flow-en"></a>
### 2. Complete Business Flow: Lead → Deal → Invoice

This example demonstrates the complete customer lifecycle from lead capture to invoice payment.

#### Step 1: Capture New Lead
```bash
curl -X POST https://api.hashinsight.net/v1/api/leads \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "WEBSITE",
    "company": "Bitcoin Mining Corp",
    "contactName": "John Doe",
    "email": "john@btcmining.com",
    "phone": "+86-138-0000-0000"
  }'
```

**Response:** Lead ID `550e8400-e29b-41d4-a716-446655440000`

#### Step 2: Qualify and Update Lead
```bash
curl -X PUT https://api.hashinsight.net/v1/api/leads/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "QUALIFIED",
    "score": 85
  }'
```

#### Step 3: Convert Lead to Deal
```bash
curl -X POST https://api.hashinsight.net/v1/api/leads/550e8400-e29b-41d4-a716-446655440000/convert \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "dealTitle": "Q1 2025 Mining Equipment Deal",
    "dealValue": 500000.00,
    "expectedClose": "2025-03-31"
  }'
```

**Response:** Deal ID `770e8400-e29b-41d4-a716-446655440000`

#### Step 4: Progress Deal Through Sales Stages
```bash
# Move to Proposal Stage
curl -X PUT https://api.hashinsight.net/v1/api/deals/770e8400-e29b-41d4-a716-446655440000/stage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "PROPOSAL",
    "probability": 65,
    "notes": "Proposal sent to client"
  }'

# Move to Negotiation Stage
curl -X PUT https://api.hashinsight.net/v1/api/deals/770e8400-e29b-41d4-a716-446655440000/stage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "NEGOTIATION",
    "probability": 85,
    "notes": "Price negotiation in progress"
  }'

# Close Deal - Won
curl -X PUT https://api.hashinsight.net/v1/api/deals/770e8400-e29b-41d4-a716-446655440000/stage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "CLOSED_WON",
    "probability": 100,
    "notes": "Contract signed"
  }'
```

#### Step 5: Create Invoice for the Deal
```bash
curl -X POST https://api.hashinsight.net/v1/api/invoices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "issueDate": "2025-10-01",
    "dueDate": "2025-10-31",
    "lineItems": [
      {
        "description": "Mining Hosting Fee - 100 Units",
        "quantity": 100,
        "unitPrice": 50.00,
        "type": "HOSTING_FEE"
      },
      {
        "description": "Electricity - 72,000 kWh",
        "quantity": 72000,
        "unitPrice": 0.05,
        "type": "ELECTRICITY"
      },
      {
        "description": "Equipment Purchase - Antminer S19 Pro",
        "quantity": 100,
        "unitPrice": 4000.00,
        "type": "EQUIPMENT"
      }
    ]
  }'
```

**Response:** Invoice ID `880e8400-e29b-41d4-a716-446655440000`, Total: $409,600.00

#### Step 6: Record Payment
```bash
curl -X POST https://api.hashinsight.net/v1/api/payments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invoiceId": "880e8400-e29b-41d4-a716-446655440000",
    "amount": 409600.00,
    "paymentDate": "2025-10-15T10:30:00Z",
    "method": "BANK_TRANSFER",
    "reference": "TXN-2025-10-15-001"
  }'
```

---

<a name="crm-operations-en"></a>
### 3. CRM Core Operations

#### 3.1 List Leads with Filters
```bash
curl -X GET "https://api.hashinsight.net/v1/api/leads?page=1&pageSize=20&status=QUALIFIED&source=WEBSITE" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 3.2 List Deals by Stage
```bash
curl -X GET "https://api.hashinsight.net/v1/api/deals?page=1&pageSize=20&stage=PROPOSAL" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

<a name="billing-operations-en"></a>
### 4. Billing Operations

#### 4.1 List Invoices
```bash
curl -X GET "https://api.hashinsight.net/v1/api/invoices?page=1&pageSize=20&status=SENT" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 4.2 Find Overdue Invoices
```bash
curl -X GET "https://api.hashinsight.net/v1/api/invoices?status=OVERDUE" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

<a name="asset-management-en"></a>
### 5. Asset Management

#### 5.1 List Mining Assets
```bash
curl -X GET "https://api.hashinsight.net/v1/api/assets?page=1&pageSize=50&status=OPERATIONAL" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 5.2 Batch Import Mining Equipment
```bash
curl -X POST https://api.hashinsight.net/v1/api/assets/batch-import \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "assets": [
      {
        "model": "Antminer S19 Pro",
        "serialNumber": "S19PRO-2025-001234",
        "hashrate": 110.00,
        "power": 3250.00,
        "location": "DC-Beijing-Rack-A01"
      },
      {
        "model": "Antminer S19 Pro",
        "serialNumber": "S19PRO-2025-001235",
        "hashrate": 110.00,
        "power": 3250.00,
        "location": "DC-Beijing-Rack-A02"
      }
    ]
  }'
```

---

<a name="ops-tickets-en"></a>
### 6. Operations Tickets

#### 6.1 Create Hardware Issue Ticket
```bash
curl -X POST https://api.hashinsight.net/v1/api/tickets \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "assetId": "990e8400-e29b-41d4-a716-446655440000",
    "type": "HARDWARE_ISSUE",
    "priority": "HIGH",
    "subject": "Miner S19-001234 hashrate dropped",
    "description": "Hashrate dropped from 110TH/s to 85TH/s over the past 24 hours. Urgent investigation required."
  }'
```

#### 6.2 List High Priority Tickets
```bash
curl -X GET "https://api.hashinsight.net/v1/api/tickets?status=OPEN&priority=HIGH" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---
---

<a name="chinese"></a>
## 中文文档

### 目录
1. [认证流程](#auth-flow-cn)
2. [完整业务流程：线索 → 商机 → 发票](#business-flow-cn)
3. [CRM核心操作](#crm-operations-cn)
4. [计费操作](#billing-operations-cn)
5. [资产管理](#asset-management-cn)
6. [运维工单](#ops-tickets-cn)

---

<a name="auth-flow-cn"></a>
### 1. 认证流程

#### 1.1 用户登录
获取JWT令牌进行API认证：

```bash
curl -X POST https://api.hashinsight.net/v1/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@hashinsight.net",
    "password": "SecureP@ssw0rd"
  }'
```

**响应示例：**
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "email": "admin@hashinsight.net",
      "name": "系统管理员",
      "roleId": "admin-role-id",
      "status": "ACTIVE"
    }
  },
  "timestamp": "2025-10-07T10:00:00Z"
}
```

#### 1.2 用户注册
创建新用户账户：

```bash
curl -X POST https://api.hashinsight.net/v1/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "SecureP@ssw0rd",
    "name": "张三"
  }'
```

---

<a name="business-flow-cn"></a>
### 2. 完整业务流程：线索 → 商机 → 发票

此示例展示从线索捕获到发票付款的完整客户生命周期。

#### 步骤1：捕获新线索
```bash
curl -X POST https://api.hashinsight.net/v1/api/leads \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "WEBSITE",
    "company": "比特币矿业公司",
    "contactName": "张三",
    "email": "zhangsan@btcmining.com",
    "phone": "+86-138-0000-0000"
  }'
```

**响应：** 线索ID `550e8400-e29b-41d4-a716-446655440000`

#### 步骤2：认证并更新线索
```bash
curl -X PUT https://api.hashinsight.net/v1/api/leads/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "QUALIFIED",
    "score": 85
  }'
```

#### 步骤3：转换线索为商机
```bash
curl -X POST https://api.hashinsight.net/v1/api/leads/550e8400-e29b-41d4-a716-446655440000/convert \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "dealTitle": "2025年Q1矿机设备采购",
    "dealValue": 500000.00,
    "expectedClose": "2025-03-31"
  }'
```

**响应：** 商机ID `770e8400-e29b-41d4-a716-446655440000`

#### 步骤4：推进商机销售阶段
```bash
# 移至提案阶段
curl -X PUT https://api.hashinsight.net/v1/api/deals/770e8400-e29b-41d4-a716-446655440000/stage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "PROPOSAL",
    "probability": 65,
    "notes": "已向客户发送提案"
  }'

# 移至谈判阶段
curl -X PUT https://api.hashinsight.net/v1/api/deals/770e8400-e29b-41d4-a716-446655440000/stage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "NEGOTIATION",
    "probability": 85,
    "notes": "价格谈判进行中"
  }'

# 成交 - 赢单
curl -X PUT https://api.hashinsight.net/v1/api/deals/770e8400-e29b-41d4-a716-446655440000/stage \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "stage": "CLOSED_WON",
    "probability": 100,
    "notes": "合同已签署"
  }'
```

#### 步骤5：为商机创建发票
```bash
curl -X POST https://api.hashinsight.net/v1/api/invoices \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "issueDate": "2025-10-01",
    "dueDate": "2025-10-31",
    "lineItems": [
      {
        "description": "矿机托管费 - 100台",
        "quantity": 100,
        "unitPrice": 50.00,
        "type": "HOSTING_FEE"
      },
      {
        "description": "电费 - 72,000度",
        "quantity": 72000,
        "unitPrice": 0.05,
        "type": "ELECTRICITY"
      },
      {
        "description": "设备采购 - 蚂蚁矿机S19 Pro",
        "quantity": 100,
        "unitPrice": 4000.00,
        "type": "EQUIPMENT"
      }
    ]
  }'
```

**响应：** 发票ID `880e8400-e29b-41d4-a716-446655440000`，总计：$409,600.00

#### 步骤6：记录付款
```bash
curl -X POST https://api.hashinsight.net/v1/api/payments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "invoiceId": "880e8400-e29b-41d4-a716-446655440000",
    "amount": 409600.00,
    "paymentDate": "2025-10-15T10:30:00Z",
    "method": "BANK_TRANSFER",
    "reference": "TXN-2025-10-15-001"
  }'
```

---

<a name="crm-operations-cn"></a>
### 3. CRM核心操作

#### 3.1 带过滤条件的线索列表
```bash
curl -X GET "https://api.hashinsight.net/v1/api/leads?page=1&pageSize=20&status=QUALIFIED&source=WEBSITE" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 3.2 按阶段查询商机列表
```bash
curl -X GET "https://api.hashinsight.net/v1/api/deals?page=1&pageSize=20&stage=PROPOSAL" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

<a name="billing-operations-cn"></a>
### 4. 计费操作

#### 4.1 查询发票列表
```bash
curl -X GET "https://api.hashinsight.net/v1/api/invoices?page=1&pageSize=20&status=SENT" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 4.2 查找逾期发票
```bash
curl -X GET "https://api.hashinsight.net/v1/api/invoices?status=OVERDUE" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

<a name="asset-management-cn"></a>
### 5. 资产管理

#### 5.1 查询矿机资产列表
```bash
curl -X GET "https://api.hashinsight.net/v1/api/assets?page=1&pageSize=50&status=OPERATIONAL" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### 5.2 批量导入矿机设备
```bash
curl -X POST https://api.hashinsight.net/v1/api/assets/batch-import \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "assets": [
      {
        "model": "蚂蚁矿机S19 Pro",
        "serialNumber": "S19PRO-2025-001234",
        "hashrate": 110.00,
        "power": 3250.00,
        "location": "DC-北京-机架-A01"
      },
      {
        "model": "蚂蚁矿机S19 Pro",
        "serialNumber": "S19PRO-2025-001235",
        "hashrate": 110.00,
        "power": 3250.00,
        "location": "DC-北京-机架-A02"
      }
    ]
  }'
```

---

<a name="ops-tickets-cn"></a>
### 6. 运维工单

#### 6.1 创建硬件故障工单
```bash
curl -X POST https://api.hashinsight.net/v1/api/tickets \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": "660e8400-e29b-41d4-a716-446655440000",
    "assetId": "990e8400-e29b-41d4-a716-446655440000",
    "type": "HARDWARE_ISSUE",
    "priority": "HIGH",
    "subject": "矿机S19-001234算力下降",
    "description": "过去24小时内算力从110TH/s下降到85TH/s，需要紧急调查处理。"
  }'
```

#### 6.2 查询高优先级工单
```bash
curl -X GET "https://api.hashinsight.net/v1/api/tickets?status=OPEN&priority=HIGH" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Additional Notes / 补充说明

### Environment Variables / 环境变量
For all examples above, replace the following placeholders:
对于上述所有示例，请替换以下占位符：

- `YOUR_JWT_TOKEN`: Your actual JWT token obtained from login / 从登录获取的实际JWT令牌
- `https://api.hashinsight.net/v1`: Your API base URL / 您的API基础URL

### Error Handling / 错误处理

All API endpoints return standard error responses:
所有API端点返回标准错误响应：

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": [
      {
        "field": "fieldName",
        "message": "Validation error message"
      }
    ]
  },
  "timestamp": "2025-10-07T10:00:00Z"
}
```

### Common HTTP Status Codes / 常见HTTP状态码
- `200`: Success / 成功
- `201`: Created / 已创建
- `400`: Bad Request / 请求错误
- `401`: Unauthorized / 未授权
- `403`: Forbidden / 禁止访问
- `404`: Not Found / 未找到
- `422`: Validation Error / 验证错误
- `500`: Internal Server Error / 服务器内部错误

### Pagination / 分页
All list endpoints support pagination using:
所有列表端点支持使用以下参数分页：

- `page`: Page number (starts from 1) / 页码（从1开始）
- `pageSize`: Items per page (max 100) / 每页条数（最多100）

Response includes pagination metadata:
响应包含分页元数据：

```json
{
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "pageSize": 20,
      "total": 156,
      "totalPages": 8
    }
  }
}
```

---

## Quick Reference / 快速参考

### API Endpoints Summary / API端点汇总

| Method | Endpoint | Description (EN) | 描述 (CN) |
|--------|----------|------------------|-----------|
| POST | /api/auth/login | User login | 用户登录 |
| POST | /api/auth/register | User registration | 用户注册 |
| GET | /api/leads | List leads | 获取线索列表 |
| POST | /api/leads | Create lead | 创建线索 |
| PUT | /api/leads/{id} | Update lead | 更新线索 |
| POST | /api/leads/{id}/convert | Convert lead to deal | 转换线索为商机 |
| GET | /api/deals | List deals | 获取商机列表 |
| PUT | /api/deals/{id}/stage | Update deal stage | 更新商机阶段 |
| GET | /api/invoices | List invoices | 获取发票列表 |
| POST | /api/invoices | Create invoice | 创建发票 |
| POST | /api/payments | Record payment | 记录付款 |
| GET | /api/assets | List miner assets | 获取矿机资产列表 |
| POST | /api/assets/batch-import | Batch import assets | 批量导入资产 |
| GET | /api/tickets | List tickets | 获取工单列表 |
| POST | /api/tickets | Create ticket | 创建工单 |

---

**For more information, please refer to:**
**更多信息，请参考：**

- OpenAPI Specification: `crm-saas-node/docs/openapi.yaml`
- AsyncAPI Specification: `crm-saas-node/docs/asyncapi.yaml`
- Postman Collection: `crm-saas-node/docs/postman-collection.json`
