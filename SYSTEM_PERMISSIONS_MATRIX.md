# BTC挖矿计算器系统权限分配矩阵

## 权限级别定义

### 1. 拥有者 (Owner) - 系统超级管理员
**角色代码**: `owner`
**权限级别**: Level 5 (最高)
**描述**: 系统创始人，拥有所有功能的完全访问权限

### 2. 管理者 (Admin) - 高级系统管理员  
**角色代码**: `admin`
**权限级别**: Level 4 (高级)
**描述**: 负责用户管理和系统运营的高级管理人员

### 3. 矿场主 (Mining_site) - 业务运营者
**角色代码**: `mining_site` 
**权限级别**: Level 3 (中级)
**描述**: 矿场运营商，专注于挖矿业务和客户管理

### 4. 经理 (Manager) - CRM专员
**角色代码**: `manager`
**权限级别**: Level 2 (专业)
**描述**: 负责客户关系管理和销售跟进

### 5. 访客 (Guest) - 基础用户
**角色代码**: `guest`
**权限级别**: Level 1 (基础)
**描述**: 基础用户，仅能使用核心计算功能

---

## 功能权限分配表

| 功能模块 | Owner | Admin | Mining_site | Manager | Guest | 路由路径 |
|---------|-------|-------|-------------|---------|-------|---------|
| **🏠 主页仪表盘** | ✅ | ✅ | ✅ | ✅ | ✅ | `/` |
| **🔐 登录/登出** | ✅ | ✅ | ✅ | ✅ | ✅ | `/login`, `/logout` |
| **⚙️ 基础挖矿计算器** | ✅ | ✅ | ✅ | ✅ | ✅ | `/calculator` |
| **📊 批量计算器** | ✅ | ✅ | ✅ | ❌ | ❌ | `/batch-calculator` |
| **🔬 算法测试工具** | ✅ | ✅ | ✅ | ✅ | ✅ | `/algorithm-test` |
| **⚡ 电力削减计算器** | ✅ | ✅ | ✅ | ❌ | ✅ | `/curtailment-calculator` |
| **📈 数据分析平台** | ✅ | ❌ | ❌ | ❌ | ❌ | `/analytics` |
| **🌐 网络历史分析** | ✅ | ✅ | ✅ | ❌ | ❌ | `/network-history` |
| **👥 用户访问管理** | ✅ | ✅ | ❌ | ❌ | ❌ | `/user-access` |
| **📋 登录记录查看** | ✅ | ❌ | ❌ | ❌ | ❌ | `/login-records` |
| **🎯 CRM客户管理** | ✅ | ✅ | ✅* | ✅ | ❌ | `/crm` |
| **📞 CRM联系人管理** | ✅ | ✅ | ✅* | ✅ | ❌ | `/crm/contacts` |
| **💼 CRM商机管理** | ✅ | ✅ | ✅* | ✅ | ❌ | `/crm/leads` |
| **💰 CRM交易管理** | ✅ | ✅ | ✅* | ✅ | ❌ | `/crm/deals` |
| **📊 CRM活动记录** | ✅ | ✅ | ✅* | ✅ | ❌ | `/crm/activities` |
| **🏭 矿场中介管理** | ✅ | ✅ | ✅ | ❌ | ❌ | `/mining-broker` |
| **💳 订阅计费管理** | ✅ | ✅ | ❌ | ❌ | ❌ | `/billing` |

**注释**: 
- ✅ 完全访问权限
- ✅* 受限访问（仅自己创建的数据）
- ❌ 无访问权限

---

## 详细权限规则

### 🔴 Owner (拥有者) 权限
```python
OWNER_PERMISSIONS = [
    'dashboard_access',           # 主页访问
    'calculator_full',           # 完整计算器功能
    'batch_calculator',          # 批量计算器
    'algorithm_testing',         # 算法测试
    'curtailment_calculator',    # 电力削减计算
    'analytics_platform',       # 数据分析平台（专属）
    'network_analysis',          # 网络分析
    'user_management',           # 用户管理（包括创建Owner）
    'login_records',             # 登录记录查看（专属）
    'crm_full_access',          # CRM完全权限
    'mining_broker',            # 矿场中介管理
    'billing_management',       # 计费管理
    'system_monitoring',        # 系统监控
    'all_data_access'           # 所有数据访问
]
```

### 🟠 Admin (管理者) 权限  
```python
ADMIN_PERMISSIONS = [
    'dashboard_access',           # 主页访问
    'calculator_full',           # 完整计算器功能
    'batch_calculator',          # 批量计算器
    'algorithm_testing',         # 算法测试
    'curtailment_calculator',    # 电力削减计算
    'network_analysis',          # 网络分析
    'user_management_limited',   # 用户管理（不能管理Owner）
    'crm_full_access',          # CRM完全权限
    'mining_broker',            # 矿场中介管理
    'billing_management'        # 计费管理
]
```

### 🟢 Mining_site (矿场主) 权限
```python
MINING_SITE_PERMISSIONS = [
    'dashboard_access',           # 主页访问
    'calculator_full',           # 完整计算器功能
    'batch_calculator',          # 批量计算器
    'algorithm_testing',         # 算法测试
    'curtailment_calculator',    # 电力削减计算
    'network_analysis',          # 网络分析
    'crm_own_customers_only',   # CRM受限访问（仅自己的客户）
    'mining_broker'             # 矿场中介管理
]
```

### 🔵 Manager (经理) 权限
```python
MANAGER_PERMISSIONS = [
    'dashboard_access',           # 主页访问
    'calculator_basic',          # 基础计算器
    'algorithm_testing',         # 算法测试
    'crm_full_access'           # CRM完全权限
]
```

### 🟣 Guest (访客) 权限
```python
GUEST_PERMISSIONS = [
    'dashboard_access',           # 主页访问（功能受限）
    'calculator_basic',          # 基础计算器
    'algorithm_testing',         # 算法测试
    'curtailment_calculator'     # 电力削减计算器
]
```

---

## 权限检查函数实现

### 当前系统权限检查函数
```python
# 在 app.py 中实现
def user_has_crm_access():
    role = session.get('role')
    return role in ['owner', 'admin', 'manager', 'mining_site']

def user_has_network_analysis_access():
    role = session.get('role')
    return role in ['owner', 'admin', 'mining_site']

def user_has_analytics_access():
    role = session.get('role')
    return role == 'owner'

def user_has_user_management_access():
    role = session.get('role')
    return role in ['owner', 'admin']

def user_has_batch_calculator_access():
    role = session.get('role')
    return role in ['owner', 'admin', 'mining_site']

def user_has_billing_access():
    role = session.get('role')
    return role in ['owner', 'admin']
```

---

## 数据访问权限规则

### CRM数据访问规则
- **Owner**: 访问所有客户数据
- **Admin**: 访问所有客户数据  
- **Mining_site**: 仅访问自己创建的客户数据
- **Manager**: 访问所有客户数据
- **Guest**: 无权访问

### 用户管理数据访问规则
- **Owner**: 可以管理所有用户（包括其他Owner）
- **Admin**: 可以管理除Owner外的所有用户
- **其他角色**: 无用户管理权限

### 系统监控数据访问规则
- **Owner**: 完全访问所有系统日志和监控数据
- **其他角色**: 无系统监控权限

---

## 实现状态

✅ **已实现功能**:
- 基础权限检查函数
- CRM权限控制
- 网络分析权限控制  
- 数据分析平台权限控制

🔄 **需要完善功能**:
- 批量计算器权限控制
- 用户管理细粒度权限
- 计费管理权限控制
- 矿场中介权限控制

📋 **权限控制装饰器建议**:
```python
# 建议创建更多专用装饰器
@requires_role(['owner', 'admin', 'mining_site'])
@requires_batch_calculator_access
@requires_billing_access
@requires_own_data_only  # 仅访问自己的数据
```

---

**当前用户**: Owner (拥有者)
**可访问功能**: 所有系统功能 ✅
**特殊权限**: 系统监控、用户管理、数据分析平台