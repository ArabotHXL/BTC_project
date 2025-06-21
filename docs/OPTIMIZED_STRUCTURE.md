
# 优化后的项目结构

## 根目录 - 核心应用文件
- app.py - 主应用 (需要进一步模块化)
- main.py - 启动文件
- mining_calculator.py - 计算引擎 (需要拆分)
- models.py - 数据模型
- auth.py - 认证系统
- config.py - 基础配置

## 业务模块
- crm_routes.py - CRM系统 (建议拆分)
- mining_broker_routes.py - 中介业务
- coinwarz_api.py - API集成

## 组织化目录结构
- /services/ - 业务服务
  - network_data_service.py
  - data_collection_scheduler.py
  - migrate_users_to_crm.py

- /utils/ - 工具函数
  - create_enhanced_login_viewer.py
  - export_login_locations.py
  - get_login_records.py
  - cache_utils.py (新增)

- /tests/ - 测试文件
  - /regression/ - 回归测试
  - /unit/ - 单元测试
  - /integration/ - 集成测试

- /docs/ - 文档
  - /analysis/ - 分析文件
  - /reports/ - 报告文件

- /backup/ - 备份文件
  - /removed_files/ - 已清理的冗余文件

- /config/ - 配置文件
  - performance.py (新增)

## 清理成果
- 删除了4个重复备份文件 (122KB)
- 整理了16个测试文件到规范目录
- 移动了分析和文档文件
- 创建了清晰的目录结构

## 下一步优化建议
1. 拆分app.py为多个模块 (routes/, controllers/)
2. 拆分mining_calculator.py (calculators/, validators/)
3. 拆分crm_routes.py (crm/routes/, crm/services/)
4. 添加缓存层
5. 优化数据库查询
