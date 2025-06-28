#!/usr/bin/env python3
"""
启动独立的Analytics引擎进程
确保15分钟数据收集持续运行
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime
import analytics_engine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analytics_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AnalyticsService:
    """独立的Analytics服务"""
    
    def __init__(self):
        self.engine = analytics_engine.AnalyticsEngine()
        self.running = False
        self.last_collection = None
        
    def start(self):
        """启动服务"""
        self.running = True
        logger.info("Analytics服务启动中...")
        
        # 在后台线程中运行调度器
        scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # 主线程监控服务状态
        try:
            while self.running:
                self._monitor_service()
                time.sleep(300)  # 每5分钟检查一次服务状态
        except KeyboardInterrupt:
            logger.info("接收到停止信号")
            self.stop()
            
    def _run_scheduler(self):
        """运行调度器"""
        try:
            self.engine.start_scheduler()
        except Exception as e:
            logger.error(f"调度器异常: {e}")
            
    def _monitor_service(self):
        """监控服务状态"""
        try:
            # 检查最近的数据收集时间
            import psycopg2
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT recorded_at FROM market_analytics 
                ORDER BY recorded_at DESC LIMIT 1
            """)
            
            result = cursor.fetchone()
            if result:
                latest_time = result[0]
                time_diff = datetime.now() - latest_time.replace(tzinfo=None)
                minutes_ago = time_diff.total_seconds() / 60
                
                logger.info(f"最新数据收集时间: {latest_time} ({minutes_ago:.1f}分钟前)")
                
                # 如果超过20分钟没有新数据，手动触发收集
                if minutes_ago > 20:
                    logger.warning(f"数据收集延迟，手动触发收集...")
                    self.engine.collect_and_analyze()
            else:
                logger.warning("未找到历史数据，触发初始收集...")
                self.engine.collect_and_analyze()
                
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"服务监控异常: {e}")
    
    def stop(self):
        """停止服务"""
        self.running = False
        self.engine.stop()
        logger.info("Analytics服务已停止")

def main():
    """主函数"""
    print("启动Bitcoin Analytics服务...")
    print("数据收集频率: 每15分钟")
    print("服务监控: 每5分钟")
    print("按Ctrl+C停止服务")
    
    service = AnalyticsService()
    service.start()

if __name__ == "__main__":
    main()