# BTC挖矿计算器 - 本地运行指南

本指南将帮助您在本地计算机上设置和运行BTC挖矿计算器。

## 必要条件

1. Python 3.9+ 环境
2. PostgreSQL数据库服务器
3. 所有在requirements-local.txt中列出的依赖包

## 安装步骤

### 1. 克隆或解压代码

将下载的zip文件解压到本地文件夹。

### 2. 创建并激活虚拟环境 (推荐)

```bash
# 在项目根目录
python -m venv venv

# 在Windows上激活
venv\Scripts\activate

# 在MacOS/Linux上激活
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements-local.txt
```

### 4. 设置环境变量

在本地运行时，您需要设置以下环境变量：

```bash
# Windows (CMD)
set DATABASE_URL=postgresql://username:password@localhost:5432/btc_calculator
set FLASK_SECRET_KEY=your_secret_key_here

# Windows (PowerShell)
$env:DATABASE_URL="postgresql://username:password@localhost:5432/btc_calculator"
$env:FLASK_SECRET_KEY="your_secret_key_here"

# MacOS/Linux
export DATABASE_URL="postgresql://username:password@localhost:5432/btc_calculator"
export FLASK_SECRET_KEY="your_secret_key_here"
```

确保替换 `username`, `password`, 和数据库名称为您本地PostgreSQL的实际配置。

### 5. 创建数据库

在PostgreSQL中创建一个新的数据库：

```sql
CREATE DATABASE btc_calculator;
```

### 6. 运行应用

```bash
flask run
# 或
python main.py
```

应用将在 http://127.0.0.1:5000/ 运行。

## 默认用户

如果您想要添加默认的管理员用户，在第一次运行应用程序后，可以使用以下SQL命令：

```sql
INSERT INTO user_access (name, email, company, position, created_at, access_days, expires_at, notes)
VALUES ('管理员', 'admin@example.com', 'BTC Mining', '系统管理员', NOW(), 3650, NOW() + INTERVAL '3650 days', '系统默认管理员账户，10年有效');
```

## 数据库结构初始化

应用程序会在第一次运行时自动创建必要的数据库表。如果您需要手动创建，以下是表结构：

```sql
-- 用户访问权限表
CREATE TABLE user_access (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(256) NOT NULL UNIQUE,
    company VARCHAR(200),
    position VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    access_days INTEGER DEFAULT 30,
    expires_at TIMESTAMP NOT NULL,
    notes TEXT,
    last_login TIMESTAMP
);

-- 登录记录表
CREATE TABLE login_records (
    id SERIAL PRIMARY KEY,
    email VARCHAR(256) NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    successful BOOLEAN DEFAULT TRUE,
    ip_address VARCHAR(50),
    login_location VARCHAR(512)
);
```

## 问题排查

1. 如果遇到数据库连接问题，请检查DATABASE_URL环境变量和PostgreSQL服务是否正确配置。
2. 如遇到其他问题，请查看应用程序日志以获取更详细的错误信息。

## 联系方式

如需技术支持，请联系: hxl2022hao@gmail.com