#!/usr/bin/env python3
"""
分析系统启动脚本
同时启动数据收集引擎和Web仪表盘
"""

import os
import time
import threading
import subprocess
import logging
from analytics_engine import AnalyticsEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start_analytics_engine():
    """启动分析引擎"""
    logger.info("启动数据分析引擎...")
    engine = AnalyticsEngine()
    
    try:
        engine.start_scheduler()
    except KeyboardInterrupt:
        logger.info("分析引擎接收到停止信号")
        engine.stop()
    except Exception as e:
        logger.error(f"分析引擎异常: {e}")

def start_dashboard():
    """启动仪表盘"""
    logger.info("启动Web仪表盘...")
    try:
        # 等待几秒确保数据库表已创建
        time.sleep(5)
        
        # 启动Flask应用
        subprocess.run([
            "python", "analytics_dashboard.py"
        ])
    except Exception as e:
        logger.error(f"仪表盘启动失败: {e}")

def main():
    """主函数"""
    logger.info("正在启动Bitcoin分析系统...")
    
    # 创建并启动线程
    engine_thread = threading.Thread(target=start_analytics_engine)
    dashboard_thread = threading.Thread(target=start_dashboard)
    
    # 设置为守护线程
    engine_thread.daemon = True
    dashboard_thread.daemon = True
    
    # 启动线程
    engine_thread.start()
    dashboard_thread.start()
    
    logger.info("分析系统已启动")
    logger.info("- 数据收集引擎: 每15分钟收集数据")
    logger.info("- 分析报告生成: 每天8:00和20:00")
    logger.info("- Web仪表盘: http://localhost:5001")
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在关闭系统...")
    
    logger.info("Bitcoin分析系统已关闭")

if __name__ == "__main__":
    main()