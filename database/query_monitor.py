#!/usr/bin/env python3
"""
慢查询监控系统 - Slow Query Monitor
Real-time Query Performance Monitoring

功能：
- 实时捕获慢查询
- 查询性能分析
- 自动优化建议
- 性能指标导出
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from functools import wraps
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from db import db

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class QueryMonitor:
    """查询监控器"""
    
    def __init__(self, slow_query_threshold_ms: int = 100):
        """
        初始化查询监控器
        
        Parameters:
        -----------
        slow_query_threshold_ms : int
            慢查询阈值（毫秒）
        """
        self.threshold_ms = slow_query_threshold_ms
        self.slow_queries = []
        self.query_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0
        }
        self.is_monitoring = False
        
    def start_monitoring(self):
        """启动查询监控"""
        if self.is_monitoring:
            logging.warning("查询监控已经在运行")
            return
        
        logging.info(f"启动查询监控（慢查询阈值: {self.threshold_ms}ms）...")
        
        # 注册SQLAlchemy事件监听器
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # 记录查询开始时间
            context._query_start_time = time.time()
        
        @event.listens_for(Engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            # 计算查询执行时间
            if hasattr(context, '_query_start_time'):
                execution_time = (time.time() - context._query_start_time) * 1000  # 转换为毫秒
                
                # 更新统计
                self.query_stats['total_queries'] += 1
                self.query_stats['total_execution_time'] += execution_time
                self.query_stats['avg_execution_time'] = (
                    self.query_stats['total_execution_time'] / 
                    self.query_stats['total_queries']
                )
                
                # 检查是否为慢查询
                if execution_time > self.threshold_ms:
                    self._record_slow_query(statement, parameters, execution_time)
        
        self.is_monitoring = True
        logging.info("✓ 查询监控已启动")
    
    def stop_monitoring(self):
        """停止查询监控"""
        if not self.is_monitoring:
            logging.warning("查询监控未运行")
            return
        
        # SQLAlchemy事件监听器会自动保持
        # 这里只是标记状态
        self.is_monitoring = False
        logging.info("✓ 查询监控已停止")
    
    def _record_slow_query(self, statement: str, parameters: dict, execution_time: float):
        """记录慢查询"""
        slow_query = {
            'timestamp': datetime.now().isoformat(),
            'statement': statement,
            'parameters': str(parameters),
            'execution_time_ms': round(execution_time, 2),
            'threshold_ms': self.threshold_ms
        }
        
        self.slow_queries.append(slow_query)
        self.query_stats['slow_queries'] += 1
        
        logging.warning(
            f"慢查询检测 ({execution_time:.2f}ms): {statement[:100]}..."
        )
    
    def get_slow_queries(self, limit: int = 20) -> List[Dict]:
        """
        获取慢查询列表
        
        Parameters:
        -----------
        limit : int
            返回数量限制
            
        Returns:
        --------
        List[Dict] : 慢查询列表
        """
        # 按执行时间倒序排序
        sorted_queries = sorted(
            self.slow_queries,
            key=lambda x: x['execution_time_ms'],
            reverse=True
        )
        
        return sorted_queries[:limit]
    
    def get_statistics(self) -> Dict:
        """获取查询统计信息"""
        slow_query_rate = (
            (self.query_stats['slow_queries'] / self.query_stats['total_queries'] * 100)
            if self.query_stats['total_queries'] > 0
            else 0
        )
        
        return {
            **self.query_stats,
            'slow_query_rate': f"{slow_query_rate:.2f}%",
            'threshold_ms': self.threshold_ms,
            'is_monitoring': self.is_monitoring
        }
    
    def analyze_query_patterns(self) -> Dict:
        """分析查询模式"""
        if not self.slow_queries:
            return {
                'total_slow_queries': 0,
                'patterns': [],
                'recommendations': []
            }
        
        # 提取查询模式（去除参数）
        patterns = {}
        for query in self.slow_queries:
            # 简化查询语句（去除具体值）
            simplified = self._simplify_query(query['statement'])
            
            if simplified not in patterns:
                patterns[simplified] = {
                    'count': 0,
                    'total_time': 0,
                    'avg_time': 0,
                    'max_time': 0,
                    'example': query['statement']
                }
            
            patterns[simplified]['count'] += 1
            patterns[simplified]['total_time'] += query['execution_time_ms']
            patterns[simplified]['max_time'] = max(
                patterns[simplified]['max_time'],
                query['execution_time_ms']
            )
        
        # 计算平均时间
        for pattern in patterns.values():
            pattern['avg_time'] = pattern['total_time'] / pattern['count']
        
        # 生成优化建议
        recommendations = self._generate_recommendations(patterns)
        
        return {
            'total_slow_queries': len(self.slow_queries),
            'unique_patterns': len(patterns),
            'patterns': sorted(
                [{'pattern': k, **v} for k, v in patterns.items()],
                key=lambda x: x['total_time'],
                reverse=True
            ),
            'recommendations': recommendations
        }
    
    def _simplify_query(self, query: str) -> str:
        """简化查询语句（去除具体值）"""
        import re
        
        # 去除数字
        query = re.sub(r'\b\d+\b', '?', query)
        
        # 去除字符串常量
        query = re.sub(r"'[^']*'", "'?'", query)
        
        # 去除多余空白
        query = re.sub(r'\s+', ' ', query)
        
        return query.strip()
    
    def _generate_recommendations(self, patterns: Dict) -> List[Dict]:
        """生成优化建议"""
        recommendations = []
        
        for pattern, stats in patterns.items():
            # 检查常见的性能问题
            
            # 1. SELECT * 查询
            if 'SELECT *' in pattern.upper():
                recommendations.append({
                    'issue': 'SELECT * query',
                    'pattern': pattern,
                    'severity': 'Medium',
                    'recommendation': '只查询需要的字段，避免使用 SELECT *',
                    'expected_improvement': '20-40%'
                })
            
            # 2. 缺少WHERE子句
            if 'WHERE' not in pattern.upper() and 'SELECT' in pattern.upper():
                recommendations.append({
                    'issue': 'Missing WHERE clause',
                    'pattern': pattern,
                    'severity': 'High',
                    'recommendation': '添加WHERE子句限制查询范围',
                    'expected_improvement': '50-90%'
                })
            
            # 3. 多次查询同一表（N+1问题）
            if stats['count'] > 10:
                recommendations.append({
                    'issue': 'Potential N+1 query',
                    'pattern': pattern,
                    'severity': 'High',
                    'recommendation': '使用JOIN或预加载(joinedload/subqueryload)代替多次查询',
                    'expected_improvement': '60-80%',
                    'occurrence_count': stats['count']
                })
            
            # 4. ORDER BY without index
            if 'ORDER BY' in pattern.upper():
                recommendations.append({
                    'issue': 'ORDER BY without index',
                    'pattern': pattern,
                    'severity': 'Medium',
                    'recommendation': '为ORDER BY字段添加索引',
                    'expected_improvement': '30-50%'
                })
        
        return recommendations
    
    def export_report(self, output_file: str = 'query_monitor_report.json') -> Dict:
        """
        导出监控报告
        
        Parameters:
        -----------
        output_file : str
            输出文件路径
            
        Returns:
        --------
        Dict : 监控报告
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'monitoring_duration': 'N/A',  # 可以添加监控持续时间追踪
            'statistics': self.get_statistics(),
            'slow_queries': self.get_slow_queries(),
            'analysis': self.analyze_query_patterns()
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logging.info(f"✓ 监控报告已导出到: {output_file}")
        
        return report
    
    def clear_data(self):
        """清空监控数据"""
        self.slow_queries = []
        self.query_stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'total_execution_time': 0.0,
            'avg_execution_time': 0.0
        }
        logging.info("✓ 监控数据已清空")


# ============================================================================
# 装饰器：查询性能监控
# Query Performance Monitoring Decorator
# ============================================================================

def monitor_query_performance(threshold_ms: int = 100):
    """
    查询性能监控装饰器
    
    Parameters:
    -----------
    threshold_ms : int
        慢查询阈值（毫秒）
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                execution_time = (time.time() - start_time) * 1000
                
                if execution_time > threshold_ms:
                    logging.warning(
                        f"慢查询 [{func.__name__}]: {execution_time:.2f}ms "
                        f"(阈值: {threshold_ms}ms)"
                    )
                else:
                    logging.debug(
                        f"查询 [{func.__name__}]: {execution_time:.2f}ms"
                    )
                
                return result
            
            except Exception as e:
                logging.error(f"查询失败 [{func.__name__}]: {e}")
                raise
        
        return wrapper
    return decorator


# ============================================================================
# 全局查询监控实例
# Global Query Monitor Instance
# ============================================================================

# 从环境变量读取阈值
SLOW_QUERY_THRESHOLD = int(os.getenv('SLOW_QUERY_THRESHOLD_MS', 100))
query_monitor = QueryMonitor(slow_query_threshold_ms=SLOW_QUERY_THRESHOLD)


# ============================================================================
# 实时查询分析器
# Real-time Query Analyzer
# ============================================================================

class QueryAnalyzer:
    """实时查询分析器"""
    
    @staticmethod
    def analyze_explain_plan(query: str) -> Dict:
        """
        分析查询执行计划
        
        Parameters:
        -----------
        query : str
            SQL查询语句
            
        Returns:
        --------
        Dict : 执行计划分析结果
        """
        try:
            with db.engine.connect() as conn:
                # 获取EXPLAIN ANALYZE结果
                explain_query = text(f"EXPLAIN ANALYZE {query}")
                result = conn.execute(explain_query)
                
                plan_lines = [row[0] for row in result]
                
                # 解析执行计划
                analysis = {
                    'query': query,
                    'execution_plan': '\n'.join(plan_lines),
                    'seq_scans': [],
                    'index_scans': [],
                    'cost_estimate': None,
                    'actual_time': None,
                    'warnings': []
                }
                
                for line in plan_lines:
                    # 检查顺序扫描
                    if 'Seq Scan' in line:
                        analysis['seq_scans'].append(line.strip())
                        analysis['warnings'].append({
                            'type': 'Sequential Scan',
                            'message': '发现顺序扫描，考虑添加索引',
                            'severity': 'Medium'
                        })
                    
                    # 检查索引扫描
                    if 'Index Scan' in line or 'Index Only Scan' in line:
                        analysis['index_scans'].append(line.strip())
                    
                    # 提取成本估计
                    if 'cost=' in line:
                        import re
                        cost_match = re.search(r'cost=([\d.]+)\.\.([\d.]+)', line)
                        if cost_match:
                            analysis['cost_estimate'] = {
                                'startup': float(cost_match.group(1)),
                                'total': float(cost_match.group(2))
                            }
                    
                    # 提取实际执行时间
                    if 'actual time=' in line:
                        import re
                        time_match = re.search(r'actual time=([\d.]+)\.\.([\d.]+)', line)
                        if time_match:
                            analysis['actual_time'] = {
                                'startup_ms': float(time_match.group(1)),
                                'total_ms': float(time_match.group(2))
                            }
                
                return analysis
        
        except Exception as e:
            logging.error(f"分析执行计划失败: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def suggest_indexes(table: str, columns: List[str]) -> List[str]:
        """
        建议索引
        
        Parameters:
        -----------
        table : str
            表名
        columns : List[str]
            需要索引的列
            
        Returns:
        --------
        List[str] : 索引创建SQL语句列表
        """
        suggestions = []
        
        for column in columns:
            index_name = f"idx_{table}_{column}"
            sql = f"CREATE INDEX {index_name} ON {table} ({column});"
            suggestions.append(sql)
        
        return suggestions


def main():
    """测试主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='慢查询监控工具')
    parser.add_argument('--threshold', type=int, default=100, help='慢查询阈值（毫秒）')
    parser.add_argument('--duration', type=int, default=60, help='监控持续时间（秒）')
    parser.add_argument('--export', type=str, default='query_monitor_report.json', help='导出报告文件')
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = QueryMonitor(slow_query_threshold_ms=args.threshold)
    
    # 启动监控
    monitor.start_monitoring()
    
    print(f"查询监控已启动，监控 {args.duration} 秒...")
    print(f"慢查询阈值: {args.threshold}ms")
    print("执行数据库操作以触发查询监控...")
    
    # 模拟监控一段时间
    time.sleep(args.duration)
    
    # 停止监控
    monitor.stop_monitoring()
    
    # 导出报告
    report = monitor.export_report(args.export)
    
    # 显示统计
    stats = monitor.get_statistics()
    print("\n查询统计：")
    print(f"  总查询数: {stats['total_queries']}")
    print(f"  慢查询数: {stats['slow_queries']}")
    print(f"  慢查询率: {stats['slow_query_rate']}")
    print(f"  平均执行时间: {stats['avg_execution_time']:.2f}ms")
    
    # 显示优化建议
    analysis = monitor.analyze_query_patterns()
    if analysis['recommendations']:
        print("\n优化建议：")
        for i, rec in enumerate(analysis['recommendations'][:5], 1):
            print(f"  {i}. [{rec['severity']}] {rec['issue']}")
            print(f"     建议: {rec['recommendation']}")
            print(f"     预期提升: {rec.get('expected_improvement', 'N/A')}")
    
    print(f"\n详细报告已保存到: {args.export}")


if __name__ == '__main__':
    main()
