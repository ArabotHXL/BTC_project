# 系统所有界面和路径列表

## 完整路由汇总（2025年8月14日）

### 🏠 主要页面

#### 1. 首页和登录
- `/` - 主页/首页，根据登录状态显示不同内容
- `/main` - 主页面重定向
- `/dashboard` - 主仪表盘（需要登录）
- `/welcome` - 欢迎页面
- `/login` - 登录页面（GET/POST）
- `/logout` - 登出功能
- `/register` - 注册页面（GET/POST）
- `/verify-email/<token>` - 邮箱验证
- `/unauthorized` - 未授权访问页面

#### 2. 计算器界面
- `/calculator` - 主挖矿计算器
- `/mining-calculator` - 挖矿计算器（别名）
- `/curtailment_calculator` - 停电损失计算器
- `/curtailment-calculator` - 停电损失计算器（别名）
- `/algorithm-test` - 算法测试页面
- `/algorithm_test` - 算法测试页面（别名）

#### 3. 分析和数据界面
- `/analytics` - 分析主页
- `/analytics_dashboard` - 分析仪表盘
- `/analytics/dashboard` - 分析仪表盘（标准路径）
- `/analytics/main` - 主要分析界面
- `/technical-analysis` - 技术分析页面
- `/technical_analysis` - 技术分析页面（别名）
- `/network/history` - 网络历史数据
- `/network-history` - 网络历史数据（别名）
- `/network_history` - 网络历史数据（下划线版）

### 🔧 管理界面

#### 4. 用户管理
- `/admin/user_access` - 用户权限管理
- `/user-access` - 用户权限管理（别名）
- `/admin/user_access/add` - 添加用户（POST）
- `/admin/user_access/view/<user_id>` - 查看用户详情
- `/admin/user_access/edit/<user_id>` - 编辑用户（GET/POST）
- `/admin/user_access/extend/<user_id>/<days>` - 延长用户权限（POST）
- `/admin/user_access/revoke/<user_id>` - 撤销用户权限（POST）
- `/admin/login_records` - 登录记录管理
- `/login-records` - 登录记录管理（别名）
- `/admin/login_dashboard` - 登录状态仪表盘
- `/login-dashboard` - 登录状态仪表盘（别名）

#### 5. 系统管理
- `/debug_info` - 系统调试信息
- `/debug-info` - 系统调试信息（别名）
- `/admin/migrate_to_crm` - CRM数据迁移

### 💼 业务功能界面

#### 6. CRM客户管理（通过蓝图，前缀 /crm）
- `/crm/dashboard` - CRM仪表盘
- `/crm/customers` - 客户列表
- `/crm/customers/add` - 添加客户
- `/crm/customers/edit/<id>` - 编辑客户
- `/crm/customers/view/<id>` - 查看客户详情
- `/crm/leads` - 线索管理
- `/crm/deals` - 交易管理
- `/crm/activities` - 活动记录

#### 7. 批量计算器（通过蓝图）
- `/batch-calculator` - 批量挖矿计算器界面
- `/batch-calculator/calculate` - 批量计算处理
- `/batch-calculator/export` - 数据导出功能

#### 8. 挖矿经纪
- `/mining-broker` - 挖矿经纪界面
- `/mine/customers` - 挖矿客户管理
- `/mine/customers/add` - 添加挖矿客户
- `/mine/customers/view_crm/<user_id>` - 查看CRM客户

#### 9. 订阅和计费（通过蓝图，前缀 /billing）
- `/billing/plans` - 订阅计划页面
- `/billing/subscribe` - 订阅处理
- `/billing/manage` - 订阅管理
- `/subscription` - 用户订阅管理页面
- `/pricing` - 价格页面

### 📊 API端点

#### 10. 网络数据API
- `/api/network-data` - 网络统计数据
- `/api/get_network_stats` - 网络状态（多别名）
- `/api/network-stats` - 网络状态
- `/api/network_stats` - 网络状态
- `/get_network_stats` - 网络状态
- `/network_stats` - 网络状态

#### 11. 价格数据API
- `/api/get_btc_price` - BTC价格（多别名）
- `/api/btc-price` - BTC价格
- `/api/btc_price` - BTC价格
- `/get_btc_price` - BTC价格
- `/btc_price` - BTC价格

#### 12. 矿机数据API
- `/api/get_miners` - 矿机数据（多别名）
- `/api/miners` - 矿机数据
- `/api/get_miners_data` - 矿机数据
- `/get_miners` - 矿机数据
- `/miners` - 矿机页面
- `/api/miner-data` - 矿机数据
- `/api/miner-models` - 矿机型号

#### 13. 计算API
- `/api/calculate` - 主要计算API（POST）
- `/calculate` - 计算处理（POST）
- `/api/test/calculate` - 测试计算API（POST）
- `/api/profit-chart-data` - 利润图表数据（POST）
- `/profit_chart_data` - 利润图表数据（POST）
- `/calculate_curtailment` - 停电损失计算（POST）

#### 14. 分析数据API
- `/api/analytics/data` - 统一分析数据
- `/api/analytics/market-data` - 市场数据
- `/analytics/api/market-data` - 市场数据（别名）
- `/analytics/market-data` - 市场数据
- `/analytics/api/technical-indicators` - 技术指标
- `/api/analytics/latest-report` - 最新报告
- `/analytics/latest-report` - 最新报告
- `/analytics/api/latest-report` - 最新报告
- `/api/analytics/price-history` - 价格历史
- `/analytics/api/price-history` - 价格历史
- `/api/analytics/detailed-report` - 详细报告

#### 15. 专业报告API
- `/api/professional-report/generate` - 生成专业报告（POST）
- `/api/professional-report/download/<file_type>` - 下载报告
- `/api/professional-report` - 专业报告

#### 16. 趋势分析API
- `/api/price-trend` - 价格趋势
- `/api/difficulty-trend` - 难度趋势
- `/api/get_sha256_mining_comparison` - SHA256挖矿对比（多别名）
- `/api/sha256_mining_comparison` - SHA256挖矿对比
- `/api/sha256-comparison` - SHA256挖矿对比
- `/get_sha256_mining_comparison` - SHA256挖矿对比
- `/mining/sha256_comparison` - SHA256挖矿对比

### 🔧 系统监控

#### 17. 健康检查和状态
- `/health` - 系统健康检查
- `/api/health` - API健康检查
- `/status` - 系统状态

#### 18. 其他页面
- `/legal` - 法律条款页面

### 🎯 功能访问控制

#### 角色权限分布：
- **Owner（拥有者）**: 所有功能无限制访问
- **Admin（管理员）**: 大部分管理功能，CRM系统访问
- **Manager（经理）**: 客户管理、基础分析功能
- **Mining_site（矿场主）**: 挖矿计算器、自己的客户数据
- **Customer（客户）**: 基础计算器功能
- **Guest（访客）**: 公开页面和基础计算器

#### 订阅计划限制：
- **Free**: 1台矿机，7天历史数据
- **Basic ($29/月)**: ≤100台矿机，30天历史数据，批量计算、Excel导出
- **Pro ($99/月)**: 无限矿机，365天历史数据，全功能访问

### 📝 模板文件对应

主要模板文件：
- `base.html` - 基础模板
- `index.html` - 主页模板
- `login.html` - 登录页面
- `calculator.html` - 计算器模板
- `analytics_main.html` - 分析主页
- `batch_calculator.html` - 批量计算器
- `user_access.html` - 用户管理
- `crm_dashboard.html` - CRM仪表盘
- `network_history.html` - 网络历史
- `curtailment_calculator.html` - 停电计算器

### 🚀 性能优化状态

所有主要API端点已实施智能缓存：
- 网络数据缓存：30秒
- BTC价格缓存：20秒  
- 矿机数据缓存：300秒（5分钟）
- 分析数据缓存：35秒
- 网络统计缓存：40秒

---

**统计概要**：
- 总路由数：100+ 个
- 主要功能模块：8个
- API端点：50+ 个
- 管理界面：10+ 个
- 用户界面：15+ 个