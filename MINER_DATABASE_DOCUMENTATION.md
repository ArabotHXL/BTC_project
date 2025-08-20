# 矿机数据库系统文档 / Miner Database System Documentation

## 概述 / Overview

成功创建了一个完整的数据库驱动的矿机信息管理系统，替代了原来的硬编码矿机数据。系统包含17个矿机型号的详细规格信息，支持完整的CRUD操作和高级管理功能。

Successfully created a complete database-driven miner information management system that replaces the previous hardcoded miner data. The system contains detailed specifications for 17 miner models and supports full CRUD operations and advanced management features.

## 数据库架构 / Database Architecture

### MinerModel 表结构 / Table Structure
```sql
CREATE TABLE miner_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    manufacturer VARCHAR(50) NOT NULL,
    hashrate DECIMAL(10,2) NOT NULL,           -- TH/s
    power_consumption INTEGER NOT NULL,         -- Watts
    efficiency DECIMAL(6,2) NOT NULL,          -- W/TH
    price_usd DECIMAL(10,2),                   -- USD price
    is_liquid_cooled BOOLEAN DEFAULT FALSE,    -- Cooling type
    is_active BOOLEAN DEFAULT TRUE,            -- Active status
    notes TEXT,                                -- Additional notes
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 矿机型号列表 / Miner Models List

### Bitmain 比特大陆 (11个型号)
1. **Antminer S19** - 95TH/s, 3250W, 34.21 W/TH
2. **Antminer S19 Pro** - 110TH/s, 3250W, 29.55 W/TH
3. **Antminer S19j Pro** - 100TH/s, 3068W, 30.68 W/TH
4. **Antminer S19 XP** - 140TH/s, 3010W, 21.50 W/TH
5. **Antminer S21** - 200TH/s, 3550W, 17.75 W/TH
6. **Antminer S21 Hyd** - 335TH/s, 5360W, 16.00 W/TH (液冷)
7. **Antminer S21 Pro** - 234TH/s, 3531W, 15.09 W/TH
8. **Antminer S21 Pro Hyd** - 319TH/s, 5445W, 17.07 W/TH (液冷)
9. **Antminer S21 XP** - 270TH/s, 3645W, 13.50 W/TH
10. **Antminer S21 XP Hyd** - 473TH/s, 5676W, 12.00 W/TH (液冷)
11. **Antminer T21** - 190TH/s, 3610W, 19.00 W/TH

### MicroBT 神马矿机 (6个型号)
1. **WhatsMiner M50** - 114TH/s, 3306W, 29.00 W/TH
2. **WhatsMiner M50S** - 126TH/s, 3276W, 26.00 W/TH
3. **WhatsMiner M53** - 226TH/s, 6554W, 29.00 W/TH
4. **WhatsMiner M53S** - 230TH/s, 6440W, 28.00 W/TH
5. **WhatsMiner M56** - 230TH/s, 5550W, 24.13 W/TH
6. **WhatsMiner M56S** - 236TH/s, 5550W, 23.52 W/TH

## API接口 / API Endpoints

### 公开接口 / Public Endpoints
- **GET /miners** - 获取所有活跃矿机列表 (无需登录)
  - 返回格式: JSON with miners array, count, source
  - 支持前端计算器直接调用

### 管理接口 / Admin Endpoints (需要登录)
- **GET /admin/miners/** - 矿机管理主页面
- **GET /admin/miners/api/list** - 获取矿机列表API
- **GET /admin/miners/api/search** - 搜索矿机
- **POST /admin/miners/api/create** - 创建新矿机
- **PUT /admin/miners/api/update/<id>** - 更新矿机信息
- **DELETE /admin/miners/api/delete/<id>** - 删除矿机（软删除）

## 核心功能 / Core Features

### 1. 数据库集成 / Database Integration
- ✅ 完全替代硬编码MINER_DATA
- ✅ 从数据库动态加载矿机信息
- ✅ 备用机制：数据库为空时使用基础硬编码数据

### 2. 矿机管理 / Miner Management
- ✅ 完整CRUD操作支持
- ✅ 按制造商和型号搜索
- ✅ 液冷标识和效率计算
- ✅ 软删除机制（保持数据完整性）

### 3. 前端集成 / Frontend Integration
- ✅ /miners API提供矿机列表给前端
- ✅ 保持向后兼容性
- ✅ 支持实时数据更新

### 4. 数据验证 / Data Validation
- ✅ 模型名称唯一性检查
- ✅ 必填字段验证
- ✅ 数值范围验证
- ✅ 效率自动计算

## 测试结果 / Test Results

```
矿机数据库系统测试报告：
✅ 矿机API接口 - 17个矿机型号正常返回
✅ 数据库直接连接 - Bitmain: 11个型号, MicroBT: 6个型号
✅ 矿机管理API - 正常响应（需要登录认证）
✅ 矿机搜索功能 - 支持按制造商和型号搜索

所有测试通过：4/4 ✅
```

## 技术实现 / Technical Implementation

### 模型定义 / Model Definition
```python
class MinerModel(db.Model):
    __tablename__ = 'miner_models'
    
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False, unique=True)
    manufacturer = db.Column(db.String(50), nullable=False)
    hashrate = db.Column(db.Numeric(10, 2), nullable=False)
    power_consumption = db.Column(db.Integer, nullable=False)
    efficiency = db.Column(db.Numeric(6, 2), nullable=False)
    # ... 其他字段
```

### API更新 / API Updates
```python
@app.route('/miners', methods=['GET'])
def get_miners():
    # 从数据库获取活跃矿机
    miners_from_db = MinerModel.get_active_miners()
    # 转换为前端需要的格式
    # 包含备用机制
```

## 部署状态 / Deployment Status

### 已完成 / Completed
- ✅ 数据库表创建和数据初始化
- ✅ 矿机管理蓝图注册
- ✅ API接口集成和测试
- ✅ 前端兼容性维护
- ✅ 备用数据机制

### 架构优势 / Architecture Benefits
1. **可扩展性** - 支持动态添加新矿机型号
2. **数据一致性** - 统一的数据源和管理
3. **维护效率** - 通过管理界面更新而非代码修改
4. **向前兼容** - 保持现有API接口不变
5. **企业级** - 支持用户权限管理和数据审计

## 下一步计划 / Next Steps

1. **前端管理界面** - 创建用户友好的矿机管理界面
2. **数据导入工具** - 支持批量导入矿机数据
3. **历史版本管理** - 跟踪矿机规格变更历史
4. **性能优化** - 添加缓存机制提高查询性能
5. **API扩展** - 支持更多筛选和排序选项

---

*该文档记录了矿机数据库系统从硬编码数据到数据库驱动系统的完整迁移过程和当前状态。*