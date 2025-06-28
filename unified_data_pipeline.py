"""
统一数据管道 (Unified Data Pipeline)
整合所有数据收集服务，确保自动更新的一致性和可靠性
"""

import threading
import time
import logging
import schedule
from datetime import datetime, timedelta
from analytics_engine import AnalyticsEngine
from services.network_data_service import network_collector
from app import app

class UnifiedDataPipeline:
    """统一数据收集管道"""
    
    def __init__(self):
        self.running = False
        self.analytics_engine = None
        self.logger = logging.getLogger(__name__)
        
    def start_pipeline(self):
        """启动统一数据管道"""
        if self.running:
            self.logger.info("数据管道已在运行")
            return
            
        self.running = True
        
        # 初始化analytics引擎
        try:
            self.analytics_engine = AnalyticsEngine()
            self.logger.info("Analytics引擎初始化成功")
        except Exception as e:
            self.logger.error(f"Analytics引擎初始化失败: {e}")
            
        # 设置定时任务
        self._setup_scheduled_tasks()
        
        # 启动调度器
        self._start_scheduler()
        
        self.logger.info("统一数据管道已启动")
        
    def _setup_scheduled_tasks(self):
        """设置定时任务"""
        # 每30分钟收集网络数据
        schedule.every(30).minutes.do(self._collect_network_data)
        
        # 每30分钟更新analytics数据
        schedule.every(30).minutes.do(self._collect_analytics_data)
        
        # 每天生成分析报告
        schedule.every().day.at("00:00").do(self._generate_analytics_report)
        
        # 立即执行一次数据收集
        self._collect_network_data()
        self._collect_analytics_data()
        
    def _collect_network_data(self):
        """收集网络数据"""
        try:
            with app.app_context():
                success = network_collector.record_network_snapshot()
                if success:
                    self.logger.info("网络数据收集成功")
                else:
                    self.logger.warning("网络数据收集失败")
        except Exception as e:
            self.logger.error(f"网络数据收集错误: {e}")
            
    def _collect_analytics_data(self):
        """收集analytics数据"""
        try:
            if self.analytics_engine:
                self.analytics_engine.collect_and_analyze()
                self.logger.info("Analytics数据收集成功")
        except Exception as e:
            self.logger.error(f"Analytics数据收集错误: {e}")
            
    def _generate_analytics_report(self):
        """生成分析报告"""
        try:
            if self.analytics_engine:
                self.analytics_engine.generate_daily_report()
                self.logger.info("分析报告生成成功")
        except Exception as e:
            self.logger.error(f"分析报告生成错误: {e}")
            
    def _start_scheduler(self):
        """启动调度器线程"""
        def run_scheduler():
            while self.running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # 每分钟检查一次
                except Exception as e:
                    self.logger.error(f"调度器运行错误: {e}")
                    
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
    def stop_pipeline(self):
        """停止数据管道"""
        self.running = False
        schedule.clear()
        if self.analytics_engine:
            self.analytics_engine.stop()
        self.logger.info("统一数据管道已停止")
        
    def get_status(self):
        """获取管道状态"""
        return {
            "running": self.running,
            "next_run": schedule.next_run() if schedule.jobs else None,
            "jobs_count": len(schedule.jobs)
        }

# 全局管道实例
unified_pipeline = UnifiedDataPipeline()

def start_unified_pipeline():
    """启动统一数据管道"""
    unified_pipeline.start_pipeline()
    
def stop_unified_pipeline():
    """停止统一数据管道"""
    unified_pipeline.stop_pipeline()
    
def get_pipeline_status():
    """获取管道状态"""
    return unified_pipeline.get_status()

if __name__ == "__main__":
    # 测试运行
    logging.basicConfig(level=logging.INFO)
    start_unified_pipeline()
    
    try:
        while True:
            time.sleep(10)
            status = get_pipeline_status()
            print(f"管道状态: {status}")
    except KeyboardInterrupt:
        stop_unified_pipeline()