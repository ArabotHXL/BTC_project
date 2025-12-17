#!/usr/bin/env python3
"""
数据库优化脚本 - Database Optimization Script
Database Performance Optimization and Index Management

目标：减少数据库查询时间50%+
Target: Reduce database query time by 50%+

功能：
- 自动创建索引
- 查询优化建议
- N+1查询检测
- 连接池配置优化
"""

import os
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy import text, inspect, Index
from sqlalchemy.pool import QueuePool
from db import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self):
        """初始化数据库优化器"""
        self.db = db
        self.engine = db.engine
        self.inspector = inspect(self.engine)
        self.optimization_log = []
    
    def analyze_slow_queries(self, threshold_ms: int = 100) -> List[Dict]:
        """
        分析慢查询
        
        Parameters:
        -----------
        threshold_ms : int
            慢查询阈值（毫秒）
            
        Returns:
        --------
        List[Dict] : 慢查询列表
        """
        logging.info(f"分析慢查询（阈值: {threshold_ms}ms）...")
        
        slow_queries = []
        
        # PostgreSQL慢查询统计
        try:
            with self.engine.connect() as conn:
                # 检查是否启用了pg_stat_statements扩展
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                    )
                """))
                
                has_pg_stat = result.scalar()
                
                if has_pg_stat:
                    # 获取慢查询
                    slow_query_sql = text("""
                        SELECT 
                            query,
                            calls,
                            mean_exec_time,
                            max_exec_time,
                            total_exec_time
                        FROM pg_stat_statements
                        WHERE mean_exec_time > :threshold
                        ORDER BY mean_exec_time DESC
                        LIMIT 20
                    """)
                    
                    result = conn.execute(slow_query_sql, {'threshold': threshold_ms})
                    
                    for row in result:
                        slow_queries.append({
                            'query': row[0],
                            'calls': row[1],
                            'mean_time_ms': float(row[2]),
                            'max_time_ms': float(row[3]),
                            'total_time_ms': float(row[4])
                        })
                    
                    logging.info(f"发现 {len(slow_queries)} 个慢查询")
                else:
                    logging.warning("pg_stat_statements扩展未启用，无法分析慢查询")
        
        except Exception as e:
            logging.error(f"分析慢查询失败: {e}")
        
        return slow_queries
    
    def create_recommended_indexes(self) -> List[str]:
        """
        创建推荐索引
        
        Returns:
        --------
        List[str] : 创建的索引列表
        """
        logging.info("创建推荐索引...")
        
        created_indexes = []
        
        # 推荐索引列表（基于models.py分析）
        recommended_indexes = [
            # 用户访问记录
            {
                'table': 'user_access',
                'columns': ['user_id', 'timestamp'],
                'name': 'idx_user_access_user_time'
            },
            # 登录记录
            {
                'table': 'login_record',
                'columns': ['user_id', 'login_time'],
                'name': 'idx_login_record_user_time'
            },
            # SLA指标
            {
                'table': 'sla_metrics',
                'columns': ['month_year'],
                'name': 'idx_sla_metrics_month'
            },
            {
                'table': 'sla_metrics',
                'columns': ['recorded_at'],
                'name': 'idx_sla_metrics_time'
            },
            {
                'table': 'sla_metrics',
                'columns': ['composite_sla_score'],
                'name': 'idx_sla_metrics_score'
            },
            # 区块链记录
            {
                'table': 'blockchain_record',
                'columns': ['data_hash'],
                'name': 'idx_blockchain_data_hash'
            },
            {
                'table': 'blockchain_record',
                'columns': ['site_id', 'data_timestamp'],
                'name': 'idx_blockchain_site_time'
            },
            # 矿机型号
            {
                'table': 'miner_models',
                'columns': ['model_name'],
                'name': 'idx_miner_models_name'
            },
            {
                'table': 'miner_models',
                'columns': ['is_active'],
                'name': 'idx_miner_models_active'
            },
            # 市场分析数据
            {
                'table': 'market_analytics',
                'columns': ['recorded_at'],
                'name': 'idx_market_analytics_time'
            },
            {
                'table': 'market_analytics',
                'columns': ['btc_price'],
                'name': 'idx_market_analytics_btc_price'
            },
            # 调度器锁
            {
                'table': 'scheduler_leader_lock',
                'columns': ['lock_key', 'expires_at'],
                'name': 'idx_scheduler_lock_key_expires'
            }
        ]
        
        for index_config in recommended_indexes:
            try:
                # 检查索引是否已存在
                existing_indexes = self.inspector.get_indexes(index_config['table'])
                index_exists = any(
                    idx['name'] == index_config['name'] 
                    for idx in existing_indexes
                )
                
                if index_exists:
                    logging.info(f"索引已存在: {index_config['name']}")
                    continue
                
                # 创建索引
                columns_str = ', '.join(index_config['columns'])
                create_index_sql = text(f"""
                    CREATE INDEX {index_config['name']} 
                    ON {index_config['table']} ({columns_str})
                """)
                
                with self.engine.connect() as conn:
                    conn.execute(create_index_sql)
                    conn.commit()
                
                created_indexes.append(index_config['name'])
                logging.info(f"✓ 创建索引: {index_config['name']}")
                
                self.optimization_log.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'index_created',
                    'index_name': index_config['name'],
                    'table': index_config['table'],
                    'columns': index_config['columns']
                })
            
            except Exception as e:
                logging.error(f"创建索引失败 {index_config['name']}: {e}")
        
        logging.info(f"索引创建完成：{len(created_indexes)} 个新索引")
        return created_indexes
    
    def optimize_connection_pool(self, pool_size: int = 20, 
                                 max_overflow: int = 10,
                                 pool_timeout: int = 30) -> Dict:
        """
        优化数据库连接池配置
        
        Parameters:
        -----------
        pool_size : int
            连接池大小
        max_overflow : int
            最大溢出连接数
        pool_timeout : int
            连接超时（秒）
            
        Returns:
        --------
        Dict : 优化配置
        """
        logging.info("优化数据库连接池配置...")
        
        config = {
            'pool_size': pool_size,
            'max_overflow': max_overflow,
            'pool_timeout': pool_timeout,
            'pool_recycle': 3600,  # 1小时回收连接
            'pool_pre_ping': True,  # 连接前ping检测
            'echo_pool': False
        }
        
        logging.info(f"连接池配置: {config}")
        
        self.optimization_log.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'connection_pool_optimized',
            'config': config
        })
        
        return config
    
    def analyze_n_plus_one_queries(self, model_name: str) -> List[Dict]:
        """
        分析N+1查询问题
        
        Parameters:
        -----------
        model_name : str
            模型名称
            
        Returns:
        --------
        List[Dict] : N+1查询建议
        """
        logging.info(f"分析 {model_name} 的N+1查询问题...")
        
        suggestions = []
        
        # 常见的N+1查询场景和优化建议
        common_n_plus_one = {
            'User': {
                'relationships': ['access_records', 'login_records', 'plan'],
                'optimization': 'joinedload'
            },
            'BlockchainRecord': {
                'relationships': ['site'],
                'optimization': 'joinedload'
            },
            'SLAMetrics': {
                'relationships': [],
                'optimization': 'subqueryload'
            }
        }
        
        if model_name in common_n_plus_one:
            info = common_n_plus_one[model_name]
            for relationship in info['relationships']:
                suggestions.append({
                    'model': model_name,
                    'relationship': relationship,
                    'issue': 'Potential N+1 query',
                    'recommendation': f"Use {info['optimization']}({relationship})",
                    'example_code': f"query.options({info['optimization']}({model_name}.{relationship}))"
                })
        
        return suggestions
    
    def vacuum_analyze_all_tables(self) -> Dict:
        """
        对所有表执行VACUUM ANALYZE（PostgreSQL）
        
        Returns:
        --------
        Dict : 执行结果
        """
        logging.info("执行VACUUM ANALYZE...")
        
        results = {
            'start_time': datetime.now().isoformat(),
            'tables_processed': [],
            'errors': []
        }
        
        try:
            # 获取所有表
            tables = self.inspector.get_table_names()
            
            with self.engine.connect() as conn:
                # 注意：VACUUM不能在事务中执行
                conn.execution_options(isolation_level="AUTOCOMMIT")
                
                for table in tables:
                    try:
                        conn.execute(text(f"VACUUM ANALYZE {table}"))
                        results['tables_processed'].append(table)
                        logging.info(f"✓ VACUUM ANALYZE {table}")
                    except Exception as e:
                        error_msg = f"VACUUM ANALYZE {table} 失败: {e}"
                        logging.error(error_msg)
                        results['errors'].append(error_msg)
        
        except Exception as e:
            logging.error(f"VACUUM ANALYZE执行失败: {e}")
            results['errors'].append(str(e))
        
        results['end_time'] = datetime.now().isoformat()
        results['success_count'] = len(results['tables_processed'])
        results['error_count'] = len(results['errors'])
        
        logging.info(f"VACUUM ANALYZE完成：{results['success_count']} 个表成功")
        
        return results
    
    def get_table_statistics(self) -> List[Dict]:
        """
        获取表统计信息
        
        Returns:
        --------
        List[Dict] : 表统计信息列表
        """
        logging.info("获取表统计信息...")
        
        stats = []
        
        try:
            with self.engine.connect() as conn:
                # PostgreSQL表统计
                stats_sql = text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_live_tup as row_count,
                        n_dead_tup as dead_tuples,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables
                    ORDER BY n_live_tup DESC
                """)
                
                result = conn.execute(stats_sql)
                
                for row in result:
                    stats.append({
                        'schema': row[0],
                        'table': row[1],
                        'row_count': row[2],
                        'dead_tuples': row[3],
                        'last_vacuum': row[4].isoformat() if row[4] else None,
                        'last_autovacuum': row[5].isoformat() if row[5] else None,
                        'last_analyze': row[6].isoformat() if row[6] else None,
                        'last_autoanalyze': row[7].isoformat() if row[7] else None
                    })
        
        except Exception as e:
            logging.error(f"获取表统计信息失败: {e}")
        
        return stats
    
    def generate_optimization_report(self, output_file: str = 'db_optimization_report.json') -> Dict:
        """
        生成优化报告
        
        Parameters:
        -----------
        output_file : str
            输出文件路径
            
        Returns:
        --------
        Dict : 优化报告
        """
        import json
        
        logging.info("生成数据库优化报告...")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'database_info': {
                'dialect': self.engine.dialect.name,
                'driver': self.engine.driver,
                'url': str(self.engine.url).split('@')[1] if '@' in str(self.engine.url) else str(self.engine.url)
            },
            'table_statistics': self.get_table_statistics(),
            'slow_queries': self.analyze_slow_queries(),
            'optimization_log': self.optimization_log,
            'recommendations': [
                {
                    'category': 'Indexing',
                    'priority': 'High',
                    'description': '确保所有外键和常用查询字段都有索引'
                },
                {
                    'category': 'N+1 Queries',
                    'priority': 'High',
                    'description': '使用joinedload/subqueryload优化关联查询'
                },
                {
                    'category': 'Connection Pool',
                    'priority': 'Medium',
                    'description': '根据并发量调整连接池大小'
                },
                {
                    'category': 'Maintenance',
                    'priority': 'Medium',
                    'description': '定期执行VACUUM ANALYZE清理死元组'
                },
                {
                    'category': 'Query Optimization',
                    'priority': 'High',
                    'description': '避免SELECT *，只查询需要的字段'
                }
            ]
        }
        
        # 保存报告
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logging.info(f"✓ 优化报告已保存到: {output_file}")
        
        return report
    
    def run_full_optimization(self) -> Dict:
        """
        运行完整的数据库优化流程
        
        Returns:
        --------
        Dict : 优化结果
        """
        logging.info("=" * 60)
        logging.info("开始数据库完整优化流程")
        logging.info("=" * 60)
        
        start_time = time.time()
        
        results = {
            'start_time': datetime.now().isoformat(),
            'steps': []
        }
        
        # 1. 分析慢查询
        slow_queries = self.analyze_slow_queries()
        results['steps'].append({
            'name': 'analyze_slow_queries',
            'slow_query_count': len(slow_queries)
        })
        
        # 2. 创建推荐索引
        created_indexes = self.create_recommended_indexes()
        results['steps'].append({
            'name': 'create_indexes',
            'created_count': len(created_indexes),
            'indexes': created_indexes
        })
        
        # 3. 优化连接池
        pool_config = self.optimize_connection_pool()
        results['steps'].append({
            'name': 'optimize_connection_pool',
            'config': pool_config
        })
        
        # 4. VACUUM ANALYZE
        vacuum_results = self.vacuum_analyze_all_tables()
        results['steps'].append({
            'name': 'vacuum_analyze',
            'tables_processed': vacuum_results['success_count'],
            'errors': vacuum_results['error_count']
        })
        
        # 5. 生成优化报告
        report = self.generate_optimization_report()
        results['steps'].append({
            'name': 'generate_report',
            'report_file': 'db_optimization_report.json'
        })
        
        elapsed = time.time() - start_time
        results['end_time'] = datetime.now().isoformat()
        results['elapsed_seconds'] = round(elapsed, 2)
        
        logging.info("=" * 60)
        logging.info(f"数据库优化完成！耗时: {elapsed:.2f}秒")
        logging.info("=" * 60)
        
        # 打印摘要
        print("\n优化摘要：")
        print(f"- 慢查询发现: {len(slow_queries)} 个")
        print(f"- 索引创建: {len(created_indexes)} 个")
        print(f"- 表清理: {vacuum_results['success_count']} 个")
        print(f"- 总耗时: {elapsed:.2f} 秒")
        
        return results


def main():
    """主函数"""
    optimizer = DatabaseOptimizer()
    
    # 运行完整优化
    results = optimizer.run_full_optimization()
    
    print("\n数据库优化完成！")
    print("详细报告请查看: db_optimization_report.json")


if __name__ == '__main__':
    main()
