#!/usr/bin/env python3
"""
Analytics Engine后台服务启动器
确保分析引擎持续运行，每15分钟收集数据
"""

import time
import schedule
import logging
from analytics_engine import AnalyticsEngine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('analytics_service.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def run_analytics_service():
    """运行分析服务"""
    logger.info("启动Analytics Engine后台服务...")
    
    try:
        # 初始化分析引擎
        engine = AnalyticsEngine()
        
        # 立即执行一次数据收集
        logger.info("执行初始数据收集...")
        engine.collect_and_analyze()
        
        # 设置15分钟间隔的数据收集
        schedule.every(15).minutes.do(engine.collect_and_analyze)
        logger.info("已设置15分钟间隔的数据收集任务")
        
        # 主循环
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
            
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务...")
    except Exception as e:
        logger.error(f"Analytics服务发生错误: {e}")
        time.sleep(300)  # 出错时等待5分钟再重试
        run_analytics_service()  # 重新启动

if __name__ == "__main__":
    run_analytics_service()