
"""
数据库健康检查模块
Database health check utilities
"""
import os
import logging
import psycopg2
from urllib.parse import urlparse

class DatabaseHealthManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def check_database_connection(self, database_url):
        """检查数据库连接状态"""
        if not database_url:
            return {
                'connected': False,
                'error': 'DATABASE_URL not configured',
                'suggestion': 'Set DATABASE_URL environment variable'
            }
        
        try:
            # 解析数据库URL
            parsed = urlparse(database_url)
            
            # 尝试连接数据库
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            
            # 获取数据库版本
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                'connected': True,
                'database_version': version,
                'host': parsed.hostname,
                'database': parsed.path.lstrip('/')
            }
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            
            # 检查是否是Neon特定错误
            neon_specific = 'endpoint' in error_msg.lower() or 'disabled' in error_msg.lower()
            
            return {
                'connected': False,
                'error': error_msg,
                'neon_specific': neon_specific,
                'suggestion': 'Check if Neon database endpoint is enabled' if neon_specific else 'Verify database credentials and connectivity'
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e),
                'suggestion': 'Check database configuration'
            }
    
    def wait_for_database(self, database_url, timeout=60):
        """等待数据库可用"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.check_database_connection(database_url)
            if status['connected']:
                return True
            
            self.logger.info("Waiting for database... retrying in 5 seconds")
            time.sleep(5)
        
        return False

# 全局实例
db_health_manager = DatabaseHealthManager()
