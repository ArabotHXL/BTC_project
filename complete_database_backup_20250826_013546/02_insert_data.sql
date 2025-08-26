-- ========================================
-- BTC Mining Calculator Database Data Import
-- Generated: 2025-08-26T01:35:46
-- ========================================

-- 注意: 本文件包含数据导入的示例语句
-- 实际数据请使用对应的CSV文件通过COPY命令导入

-- 示例: 导入CSV数据的通用命令
-- COPY table_name FROM '/path/to/table_name.csv' DELIMITER ',' CSV HEADER;

-- 为了安全起见，建议使用以下方式导入数据：

-- 1. 导入用户数据
-- COPY users FROM '/path/to/users.csv' DELIMITER ',' CSV HEADER;

-- 2. 导入矿机型号数据
-- COPY miner_models FROM '/path/to/miner_models.csv' DELIMITER ',' CSV HEADER;

-- 3. 导入市场分析数据
-- COPY market_analytics FROM '/path/to/market_analytics.csv' DELIMITER ',' CSV HEADER;

-- 4. 导入技术指标数据
-- COPY technical_indicators FROM '/path/to/technical_indicators.csv' DELIMITER ',' CSV HEADER;

-- 5. 导入历史价格数据
-- COPY historical_prices FROM '/path/to/historical_prices.csv' DELIMITER ',' CSV HEADER;

-- 6. 导入网络快照数据
-- COPY network_snapshots FROM '/path/to/network_snapshots.csv' DELIMITER ',' CSV HEADER;

-- 7. 导入分析报告数据
-- COPY analysis_reports FROM '/path/to/analysis_reports.csv' DELIMITER ',' CSV HEADER;

-- 8. 导入登录记录数据
-- COPY login_records FROM '/path/to/login_records.csv' DELIMITER ',' CSV HEADER;

-- 9. 导入用户访问权限数据
-- COPY user_access FROM '/path/to/user_access.csv' DELIMITER ',' CSV HEADER;

-- 10. 导入CRM相关数据
-- COPY crm_customers FROM '/path/to/crm_customers.csv' DELIMITER ',' CSV HEADER;
-- COPY crm_contacts FROM '/path/to/crm_contacts.csv' DELIMITER ',' CSV HEADER;
-- COPY crm_activities FROM '/path/to/crm_activities.csv' DELIMITER ',' CSV HEADER;
-- COPY crm_leads FROM '/path/to/crm_leads.csv' DELIMITER ',' CSV HEADER;
-- COPY crm_deals FROM '/path/to/crm_deals.csv' DELIMITER ',' CSV HEADER;

-- 注意事项:
-- 1. 请确保CSV文件路径正确
-- 2. 数据导入顺序很重要，先导入被引用的表（如users），再导入引用其他表的表
-- 3. 如果遇到外键约束错误，请检查数据的完整性
-- 4. 建议在导入前备份现有数据