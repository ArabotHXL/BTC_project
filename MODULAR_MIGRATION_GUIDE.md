# 模块化架构迁移指南

## 🎯 架构目标
实现完全的页面隔离，每个页面/功能作为独立模块运行，通过数据库层共享数据。

## 📁 新的目录结构
```
项目根目录/
├── modules/                      # 所有模块的根目录
│   ├── __init__.py
│   ├── config.py                 # 模块配置和注册
│   ├── app_integration.py        # 集成到主应用
│   │
│   ├── calculator/               # 计算器模块
│   │   ├── __init__.py          # 模块初始化和蓝图定义
│   │   ├── routes.py            # 路由处理
│   │   ├── models.py            # 模块特定的数据模型
│   │   ├── static/              # 模块独立的静态资源
│   │   │   ├── css/
│   │   │   │   └── calculator.css
│   │   │   └── js/
│   │   │       └── calculator.js
│   │   └── templates/           # 模块独立的模板
│   │       └── calculator/
│   │           └── index.html
│   │
│   ├── crm/                     # CRM模块（相同结构）
│   ├── batch/                   # 批量计算模块
│   ├── analytics/               # 数据分析模块
│   └── shared/                  # 共享组件
│       ├── __init__.py
│       ├── database.py          # 共享数据库操作
│       ├── auth.py              # 共享认证功能
│       └── utils.py             # 共享工具函数
│
├── templates/                    # 全局模板（逐步迁移到模块中）
├── static/                       # 全局静态资源（逐步迁移）
├── app.py                        # 主应用入口
└── models.py                     # 全局数据模型
```

## 🚀 迁移步骤

### 第1步：创建模块目录结构
```bash
# 已完成 - 创建基础模块结构
modules/
├── calculator/
├── crm/
└── shared/
```

### 第2步：迁移现有功能到模块

#### 示例：迁移计算器功能
1. **创建模块蓝图** (`modules/calculator/__init__.py`)
2. **迁移路由** - 从 `app.py` 移动到 `modules/calculator/routes.py`
3. **迁移模板** - 从 `templates/` 移动到 `modules/calculator/templates/`
4. **迁移静态文件** - CSS/JS 移动到 `modules/calculator/static/`
5. **创建模块数据模型** - 模块特定的数据结构

### 第3步：集成到主应用
```python
# 在 app.py 中添加
from modules.app_integration import integrate_modules, add_module_context_processor

# 在应用初始化后调用
integrate_modules(app)
add_module_context_processor(app)
```

### 第4步：数据库连接策略

所有模块通过共享的数据库层通信：

```python
# modules/shared/database.py
def get_network_data():
    """所有模块统一获取网络数据"""
    pass

def save_calculation_log(user_id, module_name, params, results):
    """所有模块的计算都记录到统一日志"""
    pass
```

## 🔄 渐进式迁移

### 阶段1：保持兼容性
- 保留原有路由作为重定向
- 新旧系统并行运行

```python
@app.route('/mining-calculator')
def redirect_to_calculator():
    return redirect(url_for('calculator.index'))
```

### 阶段2：逐步迁移
- 一次迁移一个模块
- 测试每个模块的独立性
- 确保数据库连接正常

### 阶段3：完全切换
- 移除旧路由
- 删除冗余代码
- 优化模块间通信

## 📊 模块间通信

### 通过数据库共享数据
```python
# 模块A写入数据
calculation = CalculationLog(...)
db.session.add(calculation)
db.session.commit()

# 模块B读取数据
calculations = CalculationLog.query.filter_by(user_id=user.id).all()
```

### 通过API端点通信
```python
# 模块提供API
@calculator_bp.route('/api/calculate')
def calculate_api():
    return jsonify(result)

# 其他模块调用
response = requests.get('/calculator/api/calculate')
```

## ✅ 验证清单

- [ ] 每个模块可以独立运行
- [ ] 修改模块A不影响模块B
- [ ] 所有模块共享用户认证
- [ ] 数据通过数据库正确共享
- [ ] 静态资源完全隔离
- [ ] 模板文件独立管理
- [ ] 错误不会跨模块传播
- [ ] 模块可以动态启用/禁用

## 🎯 最终目标

1. **完全隔离** - 每个页面独立开发和部署
2. **数据一致** - 通过数据库保证数据一致性
3. **易于维护** - 清晰的模块边界
4. **灵活扩展** - 轻松添加新模块
5. **团队协作** - 不同开发者负责不同模块

## 📝 注意事项

- 保持模块间的松耦合
- 避免直接引用其他模块的代码
- 使用共享层处理公共功能
- 记录模块间的依赖关系
- 为每个模块编写独立的测试