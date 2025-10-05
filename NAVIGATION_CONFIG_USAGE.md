# 导航配置系统使用指南

## 概述

`navigation_config.py` 提供了一个统一的、基于角色的权限分级导航菜单系统。

## 权限层级

系统定义了5个角色层级（从高到低）：

1. **owner** (等级5) - 系统拥有者，拥有所有权限
2. **admin** (等级4) - 管理员，拥有CRM、用户管理等权限
3. **mining_site** (等级3) - 矿场用户，拥有批量计算、网络分析、矿机管理权限
4. **user** (等级2) - 普通登录用户，拥有基础计算器、投资组合权限
5. **guest** (等级1) - 访客，仅可访问公开页面

## 主要功能

### 1. 获取用户导航菜单

```python
from navigation_config import get_user_navigation

# 获取中文导航菜单
menu_zh = get_user_navigation(role='admin', lang='zh')

# 获取英文导航菜单
menu_en = get_user_navigation(role='admin', lang='en')
```

### 2. 获取用户菜单（右上角下拉菜单）

```python
from navigation_config import get_user_menu

# 获取用户下拉菜单
user_menu = get_user_menu(role='user', lang='zh')
```

### 3. 生成面包屑导航

```python
from navigation_config import get_breadcrumb

# 根据当前URL生成面包屑
breadcrumb = get_breadcrumb(
    current_url='/crm/customers',
    role='admin',
    lang='zh'
)
# 返回: [{'name': '客户管理中心', 'url': '#', 'icon': 'bi-people'}, 
#        {'name': '客户管理', 'url': '/crm/customers', 'icon': 'bi-person-lines-fill'}]
```

### 4. 权限检查

```python
from navigation_config import has_permission

# 检查用户是否有权限
if has_permission(user_role='mining_site', required_role='user'):
    # 矿场用户可以访问需要user权限的功能
    pass
```

### 5. 获取角色权限描述

```python
from navigation_config import get_role_permissions

# 获取角色权限描述
perms = get_role_permissions('admin')
print(perms['zh'])  # 输出: "管理员 - CRM、用户管理权限"
print(perms['en'])  # 输出: "Admin - CRM & User Management"
print(perms['features'])  # 输出: ['crm', 'user_management', ...]
```

## Flask应用集成示例

### 在模板中使用

**base.html**

```html
<!-- 注入导航菜单到模板 -->
{% from 'navigation_config.py' import get_user_navigation %}

<nav class="navbar">
  <ul class="nav-menu">
    {% for item in get_user_navigation(session.get('role', 'guest'), session.get('lang', 'zh')) %}
    <li class="nav-item">
      <a href="{{ item.url }}" class="nav-link">
        <i class="{{ item.icon }}"></i>
        <span>{{ item.name }}</span>
      </a>
      
      {% if item.children %}
      <ul class="dropdown-menu">
        {% for child in item.children %}
        <li>
          <a href="{{ child.url }}">
            <i class="{{ child.icon }}"></i>
            {{ child.name }}
          </a>
        </li>
        {% endfor %}
      </ul>
      {% endif %}
    </li>
    {% endfor %}
  </ul>
</nav>
```

### 在Flask视图中使用

**app.py**

```python
from flask import Flask, session, render_template
from navigation_config import get_user_navigation, get_breadcrumb

@app.context_processor
def inject_navigation():
    """将导航菜单注入到所有模板"""
    user_role = session.get('role', 'guest')
    user_lang = session.get('lang', 'zh')
    
    return {
        'navigation_menu': get_user_navigation(user_role, user_lang),
        'user_menu': get_user_menu(user_role, user_lang)
    }

@app.route('/some-page')
def some_page():
    # 生成面包屑
    breadcrumb = get_breadcrumb(
        current_url=request.path,
        role=session.get('role', 'guest'),
        lang=session.get('lang', 'zh')
    )
    
    return render_template('page.html', breadcrumb=breadcrumb)
```

### 权限装饰器集成

```python
from functools import wraps
from flask import session, redirect, url_for
from navigation_config import has_permission

def require_permission(required_role):
    """需要特定角色权限的装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = session.get('role', 'guest')
            
            if not has_permission(user_role, required_role):
                return redirect(url_for('unauthorized'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/admin/dashboard')
@require_permission('admin')
def admin_dashboard():
    # 仅管理员及以上角色可访问
    return render_template('admin/dashboard.html')
```

## 菜单结构

### 1. 挖矿运营中心
- 基础计算器 (user+)
- 批量计算器 (mining_site+)
- 限电策略计算器 (mining_site+)
- 矿机管理 (mining_site+)
- 网络历史分析 (mining_site+)

### 2. 数据分析中心 (mining_site+)
- 分析仪表盘
- 高级算法引擎
- ROI热力图
- 市场数据分析

### 3. Treasury智能决策
- Treasury概览 (user+)
- 投资组合管理 (user+)
- 策略模板 (user+)
- 信号聚合 (mining_site+)

### 4. Web3仪表盘 (mining_site+)
- Web3概览
- 区块链验证
- SLA NFT管理
- 透明度验证中心
- 加密支付管理 (admin+)

### 5. 客户管理中心 (admin+)
- CRM仪表盘
- 客户管理
- 矿场客户
- 用户权限管理
- 登录记录

### 6. 系统管理 (owner only)
- 系统配置
- 数据库管理
- API管理
- 安全中心
- 备份与恢复
- 调试信息

## Bootstrap Icons 图标

系统使用 Bootstrap Icons，主要图标包括：

- `bi-house-door` - 首页
- `bi-speedometer2` - 仪表盘
- `bi-minecart` - 挖矿运营
- `bi-calculator` - 计算器
- `bi-bar-chart-line` - 数据分析
- `bi-bank` - Treasury
- `bi-diagram-3` - Web3
- `bi-people` - 客户管理
- `bi-gear` - 系统管理

确保在HTML中引入Bootstrap Icons：

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
```

## 兼容性

该配置文件与现有的 `decorators.py` 权限控制逻辑完全兼容：

- 角色定义一致：owner > admin > mining_site > user > guest
- 权限检查逻辑相同
- 可与现有装饰器配合使用

## 测试

运行测试脚本验证配置：

```bash
python test_navigation_config.py
```

测试包括：
- 角色层级验证
- 权限检查功能
- 导航菜单生成（中英文）
- 用户菜单生成
- 面包屑导航
- 角色权限描述

## 扩展

### 添加新菜单项

在 `NAVIGATION_MENU` 列表中添加新项：

```python
{
    'id': 'new_feature',
    'name': {
        'zh': '新功能',
        'en': 'New Feature'
    },
    'url': '/new-feature',
    'icon': 'bi-star',
    'min_role': 'user',  # 最低权限要求
    'order': 10  # 排序
}
```

### 添加子菜单

```python
{
    'id': 'parent_menu',
    'name': {'zh': '父菜单', 'en': 'Parent Menu'},
    'icon': 'bi-folder',
    'min_role': 'user',
    'children': [
        {
            'id': 'child_menu',
            'name': {'zh': '子菜单', 'en': 'Child Menu'},
            'url': '/child',
            'icon': 'bi-file',
            'min_role': 'user'
        }
    ]
}
```

## 最佳实践

1. **始终使用 `get_user_navigation()` 获取菜单**，而不是直接访问 `NAVIGATION_MENU`
2. **在模板中注入导航**，使用 `@app.context_processor`
3. **结合权限装饰器使用**，确保路由和菜单权限一致
4. **保持菜单项和路由同步更新**
5. **使用语言参数支持国际化**

## 故障排除

### 菜单不显示
- 检查用户角色是否正确设置在 session 中
- 验证 `min_role` 设置是否正确
- 确认 `has_permission()` 返回预期结果

### 翻译缺失
- 确保 `name` 字段包含 `zh` 和 `en` 键
- 提供 fallback 语言（默认为中文）

### 权限不一致
- 确保 `ROLE_HIERARCHY` 中的角色等级设置正确
- 验证装饰器中的角色检查逻辑与导航配置一致
