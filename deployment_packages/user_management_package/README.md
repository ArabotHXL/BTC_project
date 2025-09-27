# User Management Module 用户管理模块

## 概述 Overview

User Management Module是一个全功能的用户管理平台，提供用户注册登录、CRM客户关系管理、订阅计费、权限控制等企业级功能。该模块专注于用户生命周期管理，支持多角色权限体系和完整的客户关系管理流程。

The User Management Module is a full-featured user management platform that provides user registration/login, CRM customer relationship management, subscription billing, access control and other enterprise-level features. This module focuses on user lifecycle management, supporting multi-role permission systems and complete customer relationship management processes.

## 主要功能 Key Features

- 👥 **用户管理** - 用户注册、登录、权限控制和角色管理
- 📧 **邮件系统** - 自动邮件通知、模板管理和批量发送
- 💼 **CRM系统** - 客户关系管理、销售机会跟踪和活动管理
- 💰 **订阅计费** - 订阅计划管理、自动计费和发票生成
- 🔐 **安全认证** - JWT认证、密码策略和登录保护
- 📊 **数据分析** - 用户行为分析、业务报表和统计面板
- 🔔 **通知系统** - 邮件、短信和推送通知集成
- 📁 **文件管理** - 头像上传、文档管理和文件存储

## 快速开始 Quick Start

### 1. 下载和解压
```bash
unzip user_management_package.zip
cd user_management_package
```

### 2. 配置环境
```bash
cp database_config.env.template .env
nano .env  # 编辑配置文件
```

**必需配置：**
```env
DATABASE_URL=postgresql://username:password@localhost:5432/user_management_db
SMTP_SERVER=smtp.gmail.com
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. 启动应用
```bash
# Linux/macOS
./start_user_management.sh

# Windows
start_user_management.bat
```

### 4. 访问系统
- 用户门户: http://localhost:5003/
- 管理后台: http://localhost:5003/admin
- CRM系统: http://localhost:5003/crm
- API文档: http://localhost:5003/api/v1/docs

**默认登录信息：**
- 用户名: admin
- 密码: admin123

## 核心功能模块 Core Modules

### 1. 用户认证 (Authentication)
- 用户注册和邮箱验证
- 密码安全策略
- JWT令牌认证
- 多因素认证 (2FA)
- 社交登录集成

### 2. 权限管理 (Authorization)
- 基于角色的访问控制 (RBAC)
- 细粒度权限配置
- 用户组管理
- API访问控制

### 3. CRM系统 (Customer Relationship Management)
- 客户信息管理
- 销售机会跟踪
- 活动记录和跟进
- 客户沟通历史

### 4. 订阅计费 (Subscription & Billing)
- 订阅计划管理
- 自动续费处理
- 发票生成和发送
- 支付网关集成

## 系统架构 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Frontend  │    │   Admin Panel   │    │   CRM Dashboard │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ User Portal     │    │ User Management │    │ Customer Mgmt   │
│ Registration    │    │ Role & Perms    │    │ Sales Pipeline  │
│ Profile Mgmt    │    │ System Config   │    │ Activity Track  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Flask API     │
                    │   (Port 5003)   │
                    └─────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                       │                        │
┌───────▼───────┐    ┌─────────▼─────────┐    ┌─────────▼─────────┐
│  PostgreSQL   │    │      Redis        │    │   Email Service   │
│   Database    │    │   Cache/Session   │    │   (SMTP/SendGrid) │
└───────────────┘    └───────────────────┘    └───────────────────┘
```

## 详细配置 Detailed Configuration

### 数据库配置 Database Configuration

#### PostgreSQL (推荐)
```env
DATABASE_URL=postgresql://user:password@localhost:5432/user_mgmt_db
DB_POOL_SIZE=10
DB_POOL_TIMEOUT=30
```

#### SQLite (开发环境)
```env
DATABASE_URL=sqlite:///user_management.db
```

### 邮件服务配置 Email Service Configuration

#### Gmail SMTP
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

#### SendGrid
```env
SENDGRID_API_KEY=your-sendgrid-api-key
MAIL_FROM_EMAIL=noreply@yourdomain.com
```

### Redis配置 Redis Configuration
```env
REDIS_URL=redis://localhost:6379/3
CACHE_DEFAULT_TIMEOUT=300
SESSION_TIMEOUT=7200
```

## API接口 API Endpoints

### 用户管理 User Management
```http
# 用户注册
POST /api/v1/auth/register
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123"
}

# 用户登录
POST /api/v1/auth/login
{
    "username": "john_doe",
    "password": "SecurePass123"
}

# 获取用户信息
GET /api/v1/users/profile
Authorization: Bearer <jwt_token>
```

### CRM管理 CRM Management
```http
# 创建客户
POST /api/v1/crm/customers
{
    "name": "ABC Company",
    "email": "contact@abc.com",
    "phone": "+1234567890",
    "industry": "Technology"
}

# 记录活动
POST /api/v1/crm/activities
{
    "customer_id": 123,
    "type": "call",
    "description": "Follow-up call",
    "status": "completed"
}
```

### 订阅计费 Subscription & Billing
```http
# 创建订阅
POST /api/v1/billing/subscriptions
{
    "user_id": 123,
    "plan_id": 1,
    "billing_cycle": "monthly"
}

# 生成发票
POST /api/v1/billing/invoices
{
    "subscription_id": 456,
    "amount": 99.99,
    "due_date": "2025-10-27"
}
```

## 部署方式 Deployment Options

### 1. 直接部署
```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库
python manage.py db upgrade

# 启动应用
gunicorn --bind 0.0.0.0:5003 main:app
```

### 2. Docker部署
```bash
# 构建镜像
docker build -t user-management .

# 运行容器
docker run -p 5003:5003 user-management
```

### 3. Docker Compose部署
```bash
# 启动完整堆栈
docker-compose up -d

# 包含后台任务
docker-compose --profile with-worker up -d

# 包含管理界面
docker-compose --profile with-admin up -d
```

## 权限系统 Permission System

### 角色定义 Role Definitions
- **Super Admin**: 系统超级管理员
- **Admin**: 管理员
- **Manager**: 经理
- **Sales**: 销售人员
- **User**: 普通用户

### 权限矩阵 Permission Matrix
| 功能 | Super Admin | Admin | Manager | Sales | User |
|------|-------------|-------|---------|-------|------|
| 用户管理 | ✅ | ✅ | ❌ | ❌ | ❌ |
| CRM管理 | ✅ | ✅ | ✅ | ✅ | ❌ |
| 财务管理 | ✅ | ✅ | ✅ | ❌ | ❌ |
| 系统配置 | ✅ | ❌ | ❌ | ❌ | ❌ |
| 个人信息 | ✅ | ✅ | ✅ | ✅ | ✅ |

## 安全最佳实践 Security Best Practices

### 密码策略
```env
MIN_PASSWORD_LENGTH=8
REQUIRE_UPPERCASE=true
REQUIRE_LOWERCASE=true
REQUIRE_NUMBERS=true
REQUIRE_SPECIAL_CHARS=true
```

### 登录保护
```env
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_DURATION=1800
SESSION_TIMEOUT=7200
```

### 数据保护
- 敏感数据加密存储
- HTTPS强制传输
- CSRF保护启用
- SQL注入防护

## 监控和维护 Monitoring & Maintenance

### 健康检查
```bash
curl http://localhost:5003/health
```

### 日志监控
```bash
# 应用日志
tail -f logs/user_management.log

# 访问日志
tail -f logs/access.log

# 错误日志
tail -f logs/error.log
```

### 数据备份
```bash
# 数据库备份
pg_dump user_management_db > backup.sql

# 自动备份脚本
python scripts/backup.py
```

## 常见问题 FAQ

### Q: 如何重置管理员密码？
```bash
python manage.py reset-admin-password
```

### Q: 如何导入用户数据？
```bash
python manage.py import-users --file users.csv
```

### Q: 如何配置邮件模板？
编辑 `templates/emails/` 目录下的HTML模板文件。

### Q: 如何启用SSL？
```env
SSL_ENABLED=true
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/key.pem
```

## 技术支持 Support

- 📧 Email: user-support@hashinsight.net
- 📖 文档: https://docs.hashinsight.net/user-management
- 🔧 GitHub: https://github.com/hashinsight/user-management

---

**HashInsight User Management Platform**  
User Management Module v2.1.0  
© 2025 HashInsight Technologies