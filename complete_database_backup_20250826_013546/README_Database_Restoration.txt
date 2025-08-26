========================================
BTC Mining Calculator - Complete Database Backup
Generated: 2025-08-26T01:35:46
========================================

本文件夹包含完整的数据库备份，包括：

📁 文件清单:
========================================

🔧 SQL架构文件:
- 01_create_database_schema.sql    # 完整的数据库架构创建脚本
- 02_insert_data.sql              # 数据导入示例脚本
- database_schema_summary.json    # 数据库架构摘要信息

📊 数据文件 (CSV格式):
- *.csv                          # 31个表的数据文件 (Excel可直接打开)

📋 数据文件 (JSON格式):
- *.json                         # 31个表的数据文件 (程序友好格式)

📄 导出摘要:
- export_summary.json            # 完整的导出统计信息

🚀 数据库恢复步骤:
========================================

步骤1: 创建新数据库
CREATE DATABASE btc_mining_calculator;

步骤2: 连接到新数据库并执行架构脚本
\c btc_mining_calculator;
\i 01_create_database_schema.sql

步骤3: 导入数据 (选择以下方式之一)

方式A - 使用CSV文件 (推荐):
COPY users FROM '/path/to/users.csv' DELIMITER ',' CSV HEADER;
COPY miner_models FROM '/path/to/miner_models.csv' DELIMITER ',' CSV HEADER;
... (按照02_insert_data.sql中的顺序导入所有表)

方式B - 使用应用程序批量导入:
编写程序读取JSON文件并插入数据库

📊 数据库统计信息:
========================================
- 数据库表总数: 31个
- 数据记录总数: 9,043条
- 主要数据表:
  * technical_indicators: 4,716条记录
  * market_analytics: 2,865条记录
  * login_records: 790条记录
  * historical_prices: 365条记录
  * analysis_reports: 62条记录
  * miner_models: 42条记录

🔐 重要提醒:
========================================
1. 数据导入顺序很重要，先导入基础表（如users, miner_models）
2. 导入前请确保数据库连接正常
3. 建议在生产环境导入前先在测试环境验证
4. 所有密码字段已经过哈希处理，安全可靠
5. 时间戳数据保持原始时区信息

💡 技术支持:
========================================
如果在数据库恢复过程中遇到问题，请检查：
- PostgreSQL版本兼容性 (建议12+)
- 文件路径权限
- 数据格式完整性
- 外键约束依赖关系

本备份文件完整保存了系统的所有数据，可用于：
- 数据迁移
- 灾难恢复  
- 开发环境搭建
- 数据分析和报表