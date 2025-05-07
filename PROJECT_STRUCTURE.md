# BTC挖矿计算器系统 - 项目结构文档

## 项目概述

这是一个基于Flask的BTC挖矿盈利能力计算系统，集成了用户管理、CRM客户关系管理和电力管理功能。该系统旨在为矿场主和客户提供全面的挖矿盈利分析工具。

## 核心功能模块

### 1. 挖矿计算器模块

- **主文件**: `mining_calculator.py`, `app.py`
- **功能**:
  - 根据矿机型号、数量、电费成本等参数计算挖矿盈利能力
  - 支持实时获取BTC价格和网络难度数据
  - 提供矿场主和客户视角的收益分析
  - 生成收益热力图和ROI预测

### 2. 用户认证模块

- **主文件**: `auth.py`, `models.py` (UserAccess部分)
- **功能**:
  - 基于邮箱的认证系统
  - 角色权限管理 (拥有者、管理员、矿场管理员、客户)
  - 记录登录历史和地理位置

### 3. CRM客户管理模块

- **主文件**: `crm_routes.py`, `models.py` (CRM相关模型)
- **功能**:
  - 客户信息管理
  - 商机跟踪与状态管理
  - 交易记录管理
  - 客户活动记录
  - 支持从用户系统迁移数据

### 4. 电力管理模块

- **主文件**: `db_power_manager.py`, `power_management_models.py`
- **功能**:
  - 矿机健康状态监控 (A-D级分类)
  - 智能电力削减策略
  - 矿机轮换计划管理
  - 操作历史记录与分析

### 5. 多语言支持

- **主文件**: `translations.py`
- **功能**:
  - 支持中文和英文界面
  - 用户可自由切换语言
  
## 系统架构

系统采用了分层架构设计:

1. **用户界面层**: 基于Bootstrap的响应式前端
2. **应用逻辑层**: Flask路由和业务逻辑
3. **数据访问层**: SQLAlchemy ORM模型
4. **数据存储层**: PostgreSQL数据库

## 文件结构说明

```
./
├── app.py               # 主应用入口和路由定义
├── main.py              # 应用程序入口点
├── auth.py              # 认证系统
├── models.py            # 数据库模型定义
├── db.py                # 数据库连接管理
├── mining_calculator.py # 挖矿计算逻辑核心
├── crm_routes.py        # CRM系统路由
├── translations.py      # 多语言翻译支持
├── docs/                # 系统流程图和文档
├── templates/           # HTML模板
├── static/              # 静态资源 (CSS, JS, 图片)
└── backup/              # 备份和历史文件
```

## 数据库结构

主要数据表:

1. `user_access`: 用户访问权限
2. `login_records`: 用户登录记录
3. `crm_customers`: CRM客户记录
4. `crm_contacts`: 客户联系人
5. `crm_leads`: 商机记录
6. `crm_deals`: 交易记录
7. `crm_activities`: 客户活动记录
8. `power_miner_status`: 矿机状态
9. `power_miner_operations`: 矿机操作记录
10. `power_reduction_plans`: 电力削减计划
11. `power_rotation_schedules`: 轮换计划

## 流程图

系统流程图位于 `docs/` 目录下:

1. `system_architecture_flow.svg`: 系统架构流程图
2. `system_process_flow.svg`: 系统流程图
3. `system_data_flow.svg`: 数据流图

## 使用指南

1. 确保已安装所有依赖 (见 `requirements-local.txt`)
2. 启动应用: `gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app`
3. 访问 `http://localhost:5000` 开始使用系统

## 部署与维护

- 系统设计为在Replit环境运行，配置在 `.replit` 文件中
- 生产环境部署详见 `github_upload_guide.md` 和 `local_run_guide.md`
- 数据库迁移和更新可通过Flask-SQLAlchemy ORM完成