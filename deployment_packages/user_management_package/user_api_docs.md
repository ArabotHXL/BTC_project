# User Management API Documentation
# 用户管理API文档

## 概述 Overview

User Management Module提供完整的用户管理、CRM和计费API接口，支持用户认证、权限控制、客户关系管理、订阅计费等功能。

## 基础信息 Base Information

- **Base URL**: `http://localhost:5003/api/v1`
- **API Version**: v1.0
- **Content-Type**: `application/json`
- **认证方式**: JWT Bearer Token

## 认证 Authentication

### 获取访问令牌
```http
POST /api/v1/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

**响应:**
```json
{
    "success": true,
    "data": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "expires_in": 3600,
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@hashinsight.net",
            "role": "admin"
        }
    }
}
```

### 使用令牌
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## 用户管理 User Management

### 1. 用户注册
```http
POST /api/v1/auth/register
Content-Type: application/json

{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+1234567890"
}
```

### 2. 获取用户列表
```http
GET /api/v1/users?page=1&per_page=20&role=user&status=active
Authorization: Bearer <token>
```

**响应:**
```json
{
    "success": true,
    "data": {
        "users": [
            {
                "id": 2,
                "username": "john_doe",
                "email": "john@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": "user",
                "is_active": true,
                "created_at": "2025-09-27T12:00:00Z",
                "last_login": "2025-09-27T15:30:00Z"
            }
        ],
        "pagination": {
            "page": 1,
            "per_page": 20,
            "total": 150,
            "pages": 8
        }
    }
}
```

### 3. 更新用户信息
```http
PUT /api/v1/users/{user_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "first_name": "John",
    "last_name": "Smith",
    "phone": "+1234567891",
    "role": "manager"
}
```

### 4. 删除用户
```http
DELETE /api/v1/users/{user_id}
Authorization: Bearer <token>
```

## CRM管理 CRM Management

### 1. 客户管理 Customer Management

#### 创建客户
```http
POST /api/v1/crm/customers
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "ABC Technology Inc.",
    "email": "contact@abc-tech.com",
    "phone": "+1555123456",
    "website": "https://abc-tech.com",
    "industry": "Technology",
    "company_size": "50-100",
    "annual_revenue": 5000000,
    "address": {
        "street": "123 Tech Street",
        "city": "San Francisco",
        "state": "CA",
        "zip_code": "94105",
        "country": "USA"
    },
    "tags": ["enterprise", "saas", "high-value"]
}
```

#### 获取客户列表
```http
GET /api/v1/crm/customers?page=1&industry=Technology&status=active
Authorization: Bearer <token>
```

#### 更新客户信息
```http
PUT /api/v1/crm/customers/{customer_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "industry": "FinTech",
    "annual_revenue": 7500000,
    "status": "hot_lead"
}
```

### 2. 销售机会管理 Deal Management

#### 创建销售机会
```http
POST /api/v1/crm/deals
Authorization: Bearer <token>
Content-Type: application/json

{
    "customer_id": 123,
    "title": "Mining Hosting Service Contract",
    "description": "1000 ASIC miners hosting service",
    "value": 250000,
    "stage": "proposal",
    "probability": 75,
    "expected_close_date": "2025-11-15",
    "assigned_to": 5,
    "products": [
        {
            "name": "Mining Hosting",
            "quantity": 1000,
            "unit_price": 250
        }
    ]
}
```

#### 更新销售机会状态
```http
PUT /api/v1/crm/deals/{deal_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "stage": "negotiation",
    "probability": 85,
    "notes": "Customer requested volume discount"
}
```

### 3. 活动管理 Activity Management

#### 记录活动
```http
POST /api/v1/crm/activities
Authorization: Bearer <token>
Content-Type: application/json

{
    "customer_id": 123,
    "deal_id": 456,
    "type": "call",
    "subject": "Follow-up call on mining contract",
    "description": "Discussed pricing options and timeline",
    "status": "completed",
    "scheduled_at": "2025-09-27T14:00:00Z",
    "duration": 30,
    "outcome": "positive",
    "next_action": "Send detailed proposal",
    "next_action_date": "2025-09-28T10:00:00Z"
}
```

#### 获取活动列表
```http
GET /api/v1/crm/activities?customer_id=123&type=call&date_from=2025-09-01
Authorization: Bearer <token>
```

## 订阅计费 Subscription & Billing

### 1. 订阅计划管理 Subscription Plans

#### 创建订阅计划
```http
POST /api/v1/billing/plans
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "Professional Mining Plan",
    "description": "Professional mining hosting with premium support",
    "price": 199.99,
    "billing_cycle": "monthly",
    "currency": "USD",
    "features": [
        "24/7 monitoring",
        "Premium support",
        "Advanced analytics",
        "Priority maintenance"
    ],
    "limits": {
        "miners": 1000,
        "api_calls": 10000,
        "storage_gb": 100
    },
    "is_active": true
}
```

#### 获取计划列表
```http
GET /api/v1/billing/plans?is_active=true
Authorization: Bearer <token>
```

### 2. 订阅管理 Subscription Management

#### 创建订阅
```http
POST /api/v1/billing/subscriptions
Authorization: Bearer <token>
Content-Type: application/json

{
    "user_id": 123,
    "plan_id": 2,
    "billing_cycle": "monthly",
    "start_date": "2025-10-01",
    "trial_days": 14,
    "auto_renew": true,
    "payment_method": "credit_card",
    "coupon_code": "WELCOME20"
}
```

#### 更新订阅
```http
PUT /api/v1/billing/subscriptions/{subscription_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "plan_id": 3,
    "auto_renew": false,
    "billing_cycle": "annual"
}
```

#### 取消订阅
```http
DELETE /api/v1/billing/subscriptions/{subscription_id}
Authorization: Bearer <token>
Content-Type: application/json

{
    "reason": "switching_to_competitor",
    "feedback": "Need better pricing options",
    "cancel_at_period_end": true
}
```

### 3. 发票管理 Invoice Management

#### 生成发票
```http
POST /api/v1/billing/invoices
Authorization: Bearer <token>
Content-Type: application/json

{
    "subscription_id": 456,
    "amount": 199.99,
    "tax_amount": 20.00,
    "discount_amount": 0.00,
    "due_date": "2025-10-31",
    "description": "Professional Mining Plan - October 2025",
    "line_items": [
        {
            "description": "Mining Hosting Service",
            "quantity": 1,
            "unit_price": 199.99,
            "total": 199.99
        }
    ]
}
```

#### 获取发票列表
```http
GET /api/v1/billing/invoices?user_id=123&status=paid&date_from=2025-09-01
Authorization: Bearer <token>
```

## 系统管理 System Administration

### 1. 角色权限管理 Role & Permission Management

#### 创建角色
```http
POST /api/v1/admin/roles
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "sales_manager",
    "display_name": "Sales Manager",
    "description": "Manages sales team and customer relationships",
    "permissions": [
        "crm.read",
        "crm.write",
        "customers.read",
        "customers.write",
        "deals.read",
        "deals.write",
        "activities.read",
        "activities.write"
    ],
    "is_active": true
}
```

#### 分配角色给用户
```http
POST /api/v1/admin/users/{user_id}/roles
Authorization: Bearer <token>
Content-Type: application/json

{
    "role_ids": [2, 3]
}
```

### 2. 系统配置 System Configuration

#### 获取系统设置
```http
GET /api/v1/admin/settings
Authorization: Bearer <token>
```

#### 更新系统设置
```http
PUT /api/v1/admin/settings
Authorization: Bearer <token>
Content-Type: application/json

{
    "allow_registration": true,
    "require_email_verification": true,
    "default_user_role": "user",
    "session_timeout": 7200,
    "max_login_attempts": 5
}
```

## 报表分析 Reports & Analytics

### 1. 用户统计
```http
GET /api/v1/analytics/users/stats?period=30d
Authorization: Bearer <token>
```

**响应:**
```json
{
    "success": true,
    "data": {
        "total_users": 1250,
        "new_users": 45,
        "active_users": 890,
        "user_growth": 3.7,
        "registrations_by_day": [
            {"date": "2025-09-27", "count": 5},
            {"date": "2025-09-26", "count": 8}
        ],
        "users_by_role": {
            "admin": 5,
            "manager": 25,
            "sales": 50,
            "user": 1170
        }
    }
}
```

### 2. CRM统计
```http
GET /api/v1/analytics/crm/stats?period=30d
Authorization: Bearer <token>
```

### 3. 收入统计
```http
GET /api/v1/analytics/revenue/stats?period=12m
Authorization: Bearer <token>
```

## 文件上传 File Upload

### 上传用户头像
```http
POST /api/v1/users/{user_id}/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: avatar.jpg
```

### 上传文档
```http
POST /api/v1/documents
Authorization: Bearer <token>
Content-Type: multipart/form-data

file: contract.pdf
title: Service Contract
description: Mining hosting service contract
category: contracts
```

## 通知管理 Notification Management

### 发送邮件通知
```http
POST /api/v1/notifications/email
Authorization: Bearer <token>
Content-Type: application/json

{
    "to": ["user@example.com"],
    "cc": ["manager@example.com"],
    "subject": "Mining Service Update",
    "template": "service_update",
    "variables": {
        "user_name": "John Doe",
        "service_type": "Mining Hosting",
        "update_details": "Hashrate increased by 10%"
    },
    "priority": "normal"
}
```

### 发送系统通知
```http
POST /api/v1/notifications/system
Authorization: Bearer <token>
Content-Type: application/json

{
    "user_ids": [123, 456],
    "title": "System Maintenance Notice",
    "message": "Scheduled maintenance on Sunday 2AM-4AM UTC",
    "type": "warning",
    "action_url": "/maintenance-schedule"
}
```

## WebHook集成 Webhook Integration

### 注册WebHook
```http
POST /api/v1/webhooks
Authorization: Bearer <token>
Content-Type: application/json

{
    "url": "https://your-app.com/webhook/user-events",
    "events": [
        "user.created",
        "user.updated",
        "subscription.created",
        "payment.completed"
    ],
    "secret": "your-webhook-secret",
    "is_active": true
}
```

## 错误码 Error Codes

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| INVALID_CREDENTIALS | 401 | 用户名或密码错误 |
| TOKEN_EXPIRED | 401 | 访问令牌已过期 |
| INSUFFICIENT_PRIVILEGES | 403 | 权限不足 |
| USER_NOT_FOUND | 404 | 用户不存在 |
| EMAIL_ALREADY_EXISTS | 409 | 邮箱已被使用 |
| VALIDATION_ERROR | 422 | 数据验证失败 |
| RATE_LIMIT_EXCEEDED | 429 | 请求频率超限 |

## SDK示例 SDK Examples

### Python SDK
```python
import requests

class UserManagementAPI:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {api_key}'
            })
    
    def login(self, username, password):
        response = self.session.post(
            f"{self.base_url}/auth/login",
            json={'username': username, 'password': password}
        )
        if response.ok:
            data = response.json()
            token = data['data']['access_token']
            self.session.headers.update({
                'Authorization': f'Bearer {token}'
            })
        return response.json()
    
    def create_customer(self, customer_data):
        return self.session.post(
            f"{self.base_url}/crm/customers",
            json=customer_data
        ).json()
    
    def get_user_stats(self, period='30d'):
        return self.session.get(
            f"{self.base_url}/analytics/users/stats",
            params={'period': period}
        ).json()

# 使用示例
api = UserManagementAPI('http://localhost:5003/api/v1')
api.login('admin', 'admin123')

customer = api.create_customer({
    'name': 'New Mining Company',
    'email': 'contact@newmining.com',
    'industry': 'Cryptocurrency'
})
```

### JavaScript SDK
```javascript
class UserManagementAPI {
    constructor(baseUrl, apiKey = null) {
        this.baseUrl = baseUrl;
        this.headers = {
            'Content-Type': 'application/json'
        };
        if (apiKey) {
            this.headers['Authorization'] = `Bearer ${apiKey}`;
        }
    }
    
    async login(username, password) {
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            headers: this.headers,
            body: JSON.stringify({ username, password })
        });
        
        if (response.ok) {
            const data = await response.json();
            this.headers['Authorization'] = `Bearer ${data.data.access_token}`;
        }
        return response.json();
    }
    
    async getUsers(params = {}) {
        const query = new URLSearchParams(params);
        const response = await fetch(`${this.baseUrl}/users?${query}`, {
            headers: this.headers
        });
        return response.json();
    }
}
```

---

**技术支持**: user-api-support@hashinsight.net  
**文档更新**: 2025-09-27  
**API版本**: v1.0