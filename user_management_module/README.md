# 用户管理模块 (User Management Module)

一个完整的、独立运行的用户管理系统，提供用户认证、CRM客户关系管理、订阅计费等功能。

## 🚀 功能特性

### 核心功能
- **用户认证系统** - 完整的用户注册、登录、权限管理
- **角色权限控制** - 支持所有者、管理员、访客等多级权限
- **CRM客户管理** - 客户信息、联系人、销售线索、交易管理
- **订阅计费系统** - 多种订阅计划、支付处理、财务报告
- **管理员面板** - 系统管理、用户管理、数据统计

### 技术特性
- **独立部署** - 完全独立运行，不依赖外部项目
- **响应式设计** - 基于Bootstrap 5的现代化界面
- **数据库支持** - 支持PostgreSQL和SQLite
- **安全保护** - CSRF防护、密码加密、安全头配置
- **API兼容** - RESTful API接口，可供其他模块调用

## 📋 系统要求

- Python 3.8+
- PostgreSQL 12+ (推荐) 或 SQLite 3.x
- 2GB+ RAM
- 1GB+ 磁盘空间

## 🛠 安装部署

### 1. 克隆和准备
```bash
# 进入模块目录
cd user_management_module

# 安装依赖
./run.sh install
```

### 2. 环境配置
创建环境变量或`.env`文件：

```bash
# 必需配置
export SESSION_SECRET="your-secret-key-here"
export DATABASE_URL="postgresql://user:password@localhost/user_management"

# 可选配置
export FLASK_ENV="development"  # 或 "production"
export AUTHORIZED_EMAILS="admin@example.com,user@example.com"
```

### 3. 数据库初始化
```bash
# 初始化数据库表
./run.sh init-db
```

### 4. 启动应用
```bash
# 开发模式启动
./run.sh start

# 或生产模式启动
./run.sh prod
```

应用将在 `http://localhost:5003` 启动。

## 🎯 快速开始

### 第一次运行
1. 启动应用后，访问 `http://localhost:5003`
2. 点击"立即注册"创建第一个用户账户
3. 首个注册用户将自动获得管理员权限
4. 登录后即可访问完整功能

### 默认测试账户
开发环境下可使用以下测试账户：
- **管理员**: `test@localhost` / `password123`
- **普通用户**: `guest@localhost` / `password123`

## 📖 使用指南

### 用户管理
- **注册新用户** - 用户可自主注册或管理员批量创建
- **权限管理** - 支持所有者、管理员、访客三级权限
- **访问控制** - 灵活的访问时间和功能权限控制

### CRM系统
- **客户管理** - 添加、编辑客户信息和公司资料
- **联系人管理** - 管理客户联系人和职位信息
- **销售线索** - 跟踪潜在客户和销售机会
- **交易管理** - 管理销售订单和交易状态
- **活动记录** - 记录客户互动历史

### 订阅计费
- **订阅计划** - 免费版、基础版、专业版、企业版
- **支付处理** - 支持多种支付方式
- **财务报告** - 收入统计和财务分析
- **自动计费** - 自动化的订阅续费管理

## 🔧 配置说明

### 主要配置项

| 配置项 | 描述 | 默认值 |
|--------|------|--------|
| `SESSION_SECRET` | 会话密钥 | 必需设置 |
| `DATABASE_URL` | 数据库连接 | SQLite |
| `FLASK_ENV` | 运行环境 | development |
| `AUTHORIZED_EMAILS` | 授权邮箱列表 | 无 |

### 数据库配置
**PostgreSQL (推荐)**:
```
DATABASE_URL=postgresql://username:password@localhost:5432/user_management
```

**SQLite (开发)**:
```
DATABASE_URL=sqlite:///user_management.db
```

### 安全配置
- HTTPS强制 (生产环境)
- CSRF保护
- 密码加密存储
- 会话安全设置

## 🔌 API接口

### 认证API
```bash
# 用户登录
POST /api/auth/login

# 用户注册
POST /api/auth/register

# 获取用户信息
GET /api/auth/profile
```

### 用户管理API
```bash
# 获取用户列表
GET /api/users

# 创建用户
POST /api/users

# 更新用户
PUT /api/users/{id}

# 删除用户
DELETE /api/users/{id}
```

### CRM API
```bash
# 获取客户列表
GET /api/crm/customers

# 创建客户
POST /api/crm/customers

# 获取销售线索
GET /api/crm/leads

# 创建交易
POST /api/crm/deals
```

## 🛠 管理命令

### 运行脚本命令
```bash
./run.sh start      # 启动应用 (开发模式)
./run.sh prod       # 生产模式启动
./run.sh install    # 安装依赖
./run.sh init-db    # 初始化数据库
./run.sh test       # 运行测试
./run.sh stop       # 停止应用
./run.sh restart    # 重启应用
./run.sh status     # 查看状态
./run.sh help       # 显示帮助
```

### Python命令
```bash
# 直接启动
python main.py

# 使用Gunicorn (生产环境)
gunicorn --bind 0.0.0.0:5003 main:app

# 初始化数据库
python -c "from app import create_app; from database import create_tables; app = create_app(); create_tables(app)"
```

## 📁 项目结构

```
user_management_module/
├── app.py                 # Flask应用主文件
├── main.py               # 应用入口点
├── config.py             # 配置文件
├── database.py           # 数据库配置
├── models.py             # 数据模型
├── requirements.txt      # Python依赖
├── run.sh               # 启动脚本
├── README.md            # 说明文档
├── auth/                # 认证模块
│   ├── __init__.py
│   ├── authentication.py
│   ├── decorators.py
│   └── session_manager.py
├── routes/              # 路由模块
│   ├── __init__.py
│   ├── admin.py         # 管理员路由
│   ├── users.py         # 用户路由
│   ├── crm.py           # CRM路由
│   └── billing.py       # 计费路由
├── services/            # 业务服务
│   ├── __init__.py
│   ├── user_service.py
│   ├── crm_service.py
│   └── billing_service.py
├── templates/           # HTML模板
│   ├── base.html
│   ├── index.html
│   ├── auth/           # 认证页面
│   ├── admin/          # 管理员页面
│   ├── crm/            # CRM页面
│   ├── billing/        # 计费页面
│   └── errors/         # 错误页面
├── static/             # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
└── utils/              # 工具模块
    └── __init__.py
```

## 🔍 故障排除

### 常见问题

**1. 数据库连接失败**
```bash
# 检查数据库URL配置
echo $DATABASE_URL

# 测试数据库连接
python -c "from database import db; print('数据库连接正常')"
```

**2. 端口被占用**
```bash
# 查看端口占用
lsof -i :5003

# 停止占用进程
./run.sh stop
```

**3. 依赖安装失败**
```bash
# 更新pip
pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

**4. 权限问题**
```bash
# 赋予脚本执行权限
chmod +x run.sh

# 检查文件权限
ls -la run.sh
```

### 日志查看
```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

## 🤝 开发指南

### 开发环境设置
1. 克隆项目到本地
2. 创建Python虚拟环境
3. 安装开发依赖
4. 配置开发数据库
5. 启动开发服务器

### 代码贡献
1. Fork项目
2. 创建功能分支
3. 提交代码变更
4. 创建Pull Request

### 测试
```bash
# 运行单元测试
./run.sh test

# 运行特定测试
python -m pytest tests/test_auth.py
```

## 📞 技术支持

- **问题反馈**: 创建GitHub Issue
- **功能建议**: 提交Feature Request
- **安全问题**: 发送邮件至 security@example.com

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🔄 版本历史

### v1.0.0 (2025-09-27)
- ✨ 初始版本发布
- 🔐 完整的用户认证系统
- 👥 CRM客户关系管理
- 💳 订阅计费功能
- 🛡️ 安全防护机制
- 📱 响应式界面设计

---

**用户管理模块** - 为您的应用提供强大的用户管理能力。