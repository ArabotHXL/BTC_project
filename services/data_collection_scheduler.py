"""
自动化网络数据收集调度器
定期收集BTC网络数据以建立历史数据库
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from services.network_data_service import network_collector
from app import app

class NetworkDataScheduler:
    """网络数据自动收集调度器"""
    
    def __init__(self, interval_minutes=30):
        self.interval_minutes = interval_minutes
        self.running = False
        self.thread = None
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        """启动定期数据收集"""
        if self.running:
            self.logger.info("数据收集调度器已在运行")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        self.logger.info(f"网络数据收集调度器已启动，间隔{self.interval_minutes}分钟")
        
    def stop(self):
        """停止数据收集"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.logger.info("网络数据收集调度器已停止")
        
    def _run_scheduler(self):
        """调度器主循环"""
        while self.running:
            try:
                with app.app_context():
                    success = network_collector.record_network_snapshot()
                    if success:
                        self.logger.info("定期网络快照记录成功")
                    else:
                        self.logger.warning("定期网络快照记录失败")
                        
            except Exception as e:
                self.logger.error(f"调度器运行错误: {e}")
                
            # 等待下一次收集
            time.sleep(self.interval_minutes * 60)

# 全局调度器实例
scheduler = NetworkDataScheduler(interval_minutes=30)

def start_background_collection():
    """启动后台数据收集"""
    scheduler.start()

def stop_background_collection():
    """停止后台数据收集"""
    scheduler.stop()