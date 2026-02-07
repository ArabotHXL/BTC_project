#!/usr/bin/env python3
"""
数据库索引优化脚本
Database Index Optimization Script

为关键表添加索引以提升查询性能
Add indexes to critical tables for performance improvement

目标：
- 查询响应时间 p95 ≤250ms
- 支持5000+矿机高效查询
- 优化历史数据查询
- 提升报表生成速度

Targets:
- Query response time p95 ≤250ms
- Efficient queries for 5000+ miners
- Optimized historical data queries
- Faster report generation
"""

import logging
import os
import sys
import re
from sqlalchemy import create_engine, text, inspect
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self, database_url: str = None):
        """
        初始化数据库优化器
        
        Parameters:
        -----------
        database_url : str
            数据库连接URL
        """
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable must be set")
        
        self.engine = create_engine(self.database_url)
        self.inspector = inspect(self.engine)
        logger.info(f"✅ 已连接到数据库")
    
    def get_existing_indexes(self, table_name: str) -> list:
        """获取表的现有索引"""
        try:
            indexes = self.inspector.get_indexes(table_name)
            return [idx['name'] for idx in indexes]
        except Exception as e:
            logger.warning(f"获取表 {table_name} 索引失败: {e}")
            return []
    
    def create_index_if_not_exists(self, table_name: str, index_name: str, 
                                   columns: list, unique: bool = False):
        """
        创建索引（如果不存在）
        
        Parameters:
        -----------
        table_name : str
            表名
        index_name : str
            索引名
        columns : list
            列名列表
        unique : bool
            是否唯一索引
        """
        try:
            existing_indexes = self.get_existing_indexes(table_name)
            
            if index_name in existing_indexes:
                logger.info(f"⏭️  索引已存在: {index_name} on {table_name}")
                return False
            
            identifier_re = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')
            for ident in [table_name, index_name] + list(columns):
                if not identifier_re.match(ident):
                    raise ValueError(f"Invalid SQL identifier: {ident}")
            
            columns_str = ', '.join(columns)
            unique_str = 'UNIQUE ' if unique else ''
            sql = f"CREATE {unique_str}INDEX {index_name} ON {table_name} ({columns_str})"
            
            with self.engine.connect() as conn:
                conn.execute(text(sql))
                conn.commit()
            
            logger.info(f"✅ 创建索引成功: {index_name} on {table_name}({columns_str})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 创建索引失败 {index_name}: {e}")
            return False
    
    def optimize_user_miner_table(self):
        """优化 user_miner 表（用户矿机数据）"""
        logger.info("🔧 优化 user_miner 表...")
        
        # 用户ID索引（最常用的查询条件）
        self.create_index_if_not_exists(
            'user_miner', 'idx_user_miner_user_id', ['user_id']
        )
        
        # 创建时间索引（用于时间范围查询）
        self.create_index_if_not_exists(
            'user_miner', 'idx_user_miner_created_at', ['created_at']
        )
        
        # 复合索引：user_id + created_at（用于用户历史查询）
        self.create_index_if_not_exists(
            'user_miner', 'idx_user_miner_user_created', ['user_id', 'created_at']
        )
        
        # 矿机型号索引（用于按型号筛选）
        self.create_index_if_not_exists(
            'user_miner', 'idx_user_miner_model', ['model']
        )
    
    def optimize_network_snapshot_table(self):
        """优化 network_snapshot 表（网络快照数据）"""
        logger.info("🔧 优化 network_snapshot 表...")
        
        # 时间戳索引（用于历史数据查询）
        self.create_index_if_not_exists(
            'network_snapshot', 'idx_network_snapshot_timestamp', ['timestamp']
        )
        
        # 数据来源索引（用于按来源筛选）
        self.create_index_if_not_exists(
            'network_snapshot', 'idx_network_snapshot_source', ['source']
        )
        
        # 复合索引：timestamp + source（用于数据对比）
        self.create_index_if_not_exists(
            'network_snapshot', 'idx_network_snapshot_ts_source', ['timestamp', 'source']
        )
    
    def optimize_miner_telemetry_table(self):
        """优化 miner_telemetry 表（矿机遥测数据）"""
        logger.info("🔧 优化 miner_telemetry 表...")
        
        # 矿机ID索引
        self.create_index_if_not_exists(
            'miner_telemetry', 'idx_miner_telemetry_miner_id', ['miner_id']
        )
        
        # 时间戳索引（用于时间序列查询）
        self.create_index_if_not_exists(
            'miner_telemetry', 'idx_miner_telemetry_timestamp', ['timestamp']
        )
        
        # 复合索引：miner_id + timestamp（用于单矿机历史查询）
        self.create_index_if_not_exists(
            'miner_telemetry', 'idx_miner_telemetry_miner_ts', ['miner_id', 'timestamp']
        )
        
        # 状态索引（用于告警查询）
        self.create_index_if_not_exists(
            'miner_telemetry', 'idx_miner_telemetry_status', ['status']
        )
    
    def optimize_blockchain_record_table(self):
        """优化 blockchain_record 表（区块链记录）"""
        logger.info("🔧 优化 blockchain_record 表...")
        
        # 交易哈希唯一索引
        self.create_index_if_not_exists(
            'blockchain_record', 'idx_blockchain_record_tx_hash', ['tx_hash'], unique=True
        )
        
        # 状态索引（用于查询待处理/失败的记录）
        self.create_index_if_not_exists(
            'blockchain_record', 'idx_blockchain_record_status', ['status']
        )
        
        # 创建时间索引
        self.create_index_if_not_exists(
            'blockchain_record', 'idx_blockchain_record_created', ['created_at']
        )
        
        # 用户ID索引
        self.create_index_if_not_exists(
            'blockchain_record', 'idx_blockchain_record_user_id', ['user_id']
        )
    
    def optimize_hosting_miner_table(self):
        """优化 hosting_miner 表（托管矿机）"""
        logger.info("🔧 优化 hosting_miner 表...")
        
        # 站点ID索引
        self.create_index_if_not_exists(
            'hosting_miner', 'idx_hosting_miner_site_id', ['site_id']
        )
        
        # 状态索引
        self.create_index_if_not_exists(
            'hosting_miner', 'idx_hosting_miner_status', ['status']
        )
        
        # 客户ID索引
        self.create_index_if_not_exists(
            'hosting_miner', 'idx_hosting_miner_customer_id', ['customer_id']
        )
        
        # 复合索引：site_id + status（用于站点监控）
        self.create_index_if_not_exists(
            'hosting_miner', 'idx_hosting_miner_site_status', ['site_id', 'status']
        )
    
    def optimize_login_record_table(self):
        """优化 login_record 表（登录记录）"""
        logger.info("🔧 优化 login_record 表...")
        
        # 用户ID索引
        self.create_index_if_not_exists(
            'login_record', 'idx_login_record_user_id', ['user_id']
        )
        
        # 时间戳索引
        self.create_index_if_not_exists(
            'login_record', 'idx_login_record_timestamp', ['login_time']
        )
        
        # 复合索引：user_id + timestamp（用于用户登录历史）
        self.create_index_if_not_exists(
            'login_record', 'idx_login_record_user_time', ['user_id', 'login_time']
        )
    
    def optimize_user_access_table(self):
        """优化 user_access 表（用户访问记录）"""
        logger.info("🔧 优化 user_access 表...")
        
        # 用户ID索引
        self.create_index_if_not_exists(
            'user_access', 'idx_user_access_user_id', ['user_id']
        )
        
        # 访问时间索引
        self.create_index_if_not_exists(
            'user_access', 'idx_user_access_timestamp', ['access_time']
        )
        
        # 端点索引（用于API使用分析）
        self.create_index_if_not_exists(
            'user_access', 'idx_user_access_endpoint', ['endpoint']
        )
    
    def optimize_sla_metrics_table(self):
        """优化 sla_metrics 表（SLA指标）"""
        logger.info("🔧 优化 sla_metrics 表...")
        
        # 时间戳索引
        self.create_index_if_not_exists(
            'sla_metrics', 'idx_sla_metrics_timestamp', ['recorded_at']
        )
        
        # 站点ID索引
        self.create_index_if_not_exists(
            'sla_metrics', 'idx_sla_metrics_site_id', ['site_id']
        )
        
        # 复合索引：site_id + timestamp
        self.create_index_if_not_exists(
            'sla_metrics', 'idx_sla_metrics_site_time', ['site_id', 'recorded_at']
        )
    
    def analyze_table_stats(self, table_name: str):
        """分析表统计信息"""
        try:
            with self.engine.connect() as conn:
                # 获取表大小
                result = conn.execute(text(f"""
                    SELECT 
                        pg_size_pretty(pg_total_relation_size('{table_name}')) as total_size,
                        pg_size_pretty(pg_relation_size('{table_name}')) as table_size,
                        pg_size_pretty(pg_indexes_size('{table_name}')) as indexes_size
                """))
                row = result.fetchone()
                
                if row:
                    logger.info(f"📊 {table_name} - 总大小: {row[0]}, 表大小: {row[1]}, 索引大小: {row[2]}")
        except Exception as e:
            logger.warning(f"分析表 {table_name} 失败: {e}")
    
    def vacuum_analyze_all(self):
        """对所有表执行VACUUM ANALYZE"""
        logger.info("🧹 执行VACUUM ANALYZE...")
        
        critical_tables = [
            'user_miner', 'network_snapshot', 'miner_telemetry',
            'blockchain_record', 'hosting_miner', 'login_record',
            'user_access', 'sla_metrics'
        ]
        
        try:
            # 需要autocommit模式来执行VACUUM
            with self.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                for table in critical_tables:
                    try:
                        conn.execute(text(f"VACUUM ANALYZE {table}"))
                        logger.info(f"✅ VACUUM ANALYZE {table} 完成")
                    except Exception as e:
                        logger.warning(f"⚠️  VACUUM ANALYZE {table} 失败: {e}")
        except Exception as e:
            logger.error(f"❌ VACUUM ANALYZE 执行失败: {e}")
    
    def optimize_all(self):
        """执行所有优化"""
        logger.info("=" * 60)
        logger.info("🚀 开始数据库优化")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # 优化各个表
        self.optimize_user_miner_table()
        self.optimize_network_snapshot_table()
        self.optimize_miner_telemetry_table()
        self.optimize_blockchain_record_table()
        self.optimize_hosting_miner_table()
        self.optimize_login_record_table()
        self.optimize_user_access_table()
        self.optimize_sla_metrics_table()
        
        # 分析表统计信息
        logger.info("\n" + "=" * 60)
        logger.info("📊 表统计信息")
        logger.info("=" * 60)
        for table in ['user_miner', 'network_snapshot', 'miner_telemetry', 
                      'blockchain_record', 'hosting_miner']:
            self.analyze_table_stats(table)
        
        # 执行VACUUM ANALYZE
        logger.info("\n" + "=" * 60)
        self.vacuum_analyze_all()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        
        logger.info("\n" + "=" * 60)
        logger.info(f"✅ 数据库优化完成！耗时: {elapsed:.2f}秒")
        logger.info("=" * 60)
    
    def generate_optimization_report(self):
        """生成优化报告"""
        logger.info("\n" + "=" * 60)
        logger.info("📋 优化建议报告")
        logger.info("=" * 60)
        
        recommendations = [
            "1. 定期执行 VACUUM ANALYZE 以更新统计信息",
            "2. 监控慢查询日志，识别需要优化的查询",
            "3. 考虑对大表进行分区（如按时间分区）",
            "4. 定期清理历史数据，保持表大小合理",
            "5. 使用连接池优化数据库连接",
            "6. 考虑使用只读副本分担查询负载",
            "7. 配置合适的 work_mem 和 shared_buffers",
            "8. 启用 pg_stat_statements 扩展监控查询性能"
        ]
        
        for rec in recommendations:
            logger.info(rec)


def main():
    """主函数"""
    try:
        optimizer = DatabaseOptimizer()
        optimizer.optimize_all()
        optimizer.generate_optimization_report()
        
        logger.info("\n🎉 所有优化任务完成!")
        return 0
    
    except Exception as e:
        logger.error(f"❌ 优化失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
