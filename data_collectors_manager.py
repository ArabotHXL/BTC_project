#!/usr/bin/env python3
"""
数据收集器统一管理器
Unified Data Collectors Manager

启动和管理所有数据收集pipeline
"""

import logging
import threading
import time
import os
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataCollectorsManager:
    """统一管理所有数据收集器"""
    
    def __init__(self):
        self.collectors = {}
        self.threads = {}
        self.running = False
        
    def start_analytics_engine(self):
        """启动市场数据分析引擎（已在app.py中自动启动）"""
        try:
            from modules.analytics.engines.analytics_engine import AnalyticsEngine
            engine = AnalyticsEngine()
            self.collectors['analytics'] = engine
            logger.info("✅ 市场数据分析引擎已启动")
            return True
        except Exception as e:
            logger.error(f"❌ 市场数据分析引擎启动失败: {e}")
            return False
    
    def start_multi_exchange_collector(self):
        """启动多交易所数据收集器"""
        try:
            from multi_exchange_collector import MultiExchangeCollector
            collector = MultiExchangeCollector()
            
            def run_collector():
                while self.running:
                    try:
                        # 收集所有交易所数据
                        exchange_data = collector.collect_all_exchanges()
                        if exchange_data:
                            # 聚合数据
                            aggregated = collector.aggregate_volume_data(exchange_data)
                            # 保存数据
                            collector.save_enhanced_data(aggregated)
                            logger.info(f"✅ 多交易所数据收集完成: {aggregated.get('exchange_count', 0)}个交易所")
                        time.sleep(300)  # 5分钟一次
                    except Exception as e:
                        logger.error(f"多交易所收集错误: {e}")
                        time.sleep(60)
            
            self.collectors['multi_exchange'] = collector
            thread = threading.Thread(target=run_collector, daemon=True)
            self.threads['multi_exchange'] = thread
            thread.start()
            logger.info("✅ 多交易所数据收集器已启动")
            return True
        except Exception as e:
            logger.error(f"❌ 多交易所收集器启动失败: {e}")
            return False
    
    def start_alternative_sources(self):
        """启动备用数据源收集器"""
        try:
            from alternative_data_sources import AlternativeDataSources
            sources = AlternativeDataSources()
            
            def run_sources():
                while self.running:
                    try:
                        # 每天收集一次历史数据
                        logger.info("开始收集备用数据源...")
                        # 从Blockchain.info获取数据
                        blockchain_data = sources.fetch_blockchain_info_data(180)
                        if blockchain_data:
                            sources.insert_historical_data(blockchain_data)
                        # 生成合成历史数据填补空缺
                        synthetic_data = sources.generate_synthetic_historical_data(90)
                        if synthetic_data:
                            sources.insert_historical_data(synthetic_data)
                        logger.info("✅ 备用数据源收集完成")
                        time.sleep(86400)  # 24小时一次
                    except Exception as e:
                        logger.error(f"备用数据源收集错误: {e}")
                        time.sleep(3600)
            
            self.collectors['alternative'] = sources
            thread = threading.Thread(target=run_sources, daemon=True)
            self.threads['alternative'] = thread
            thread.start()
            logger.info("✅ 备用数据源收集器已启动")
            return True
        except Exception as e:
            logger.error(f"❌ 备用数据源收集器启动失败: {e}")
            return False
    
    def start_blockchain_scheduler(self):
        """启动区块链调度器（已在app.py中启动）"""
        try:
            from scheduler import BlockchainScheduler
            scheduler = BlockchainScheduler()
            self.collectors['blockchain'] = scheduler
            logger.info("✅ 区块链调度器已启动")
            return True
        except Exception as e:
            logger.error(f"❌ 区块链调度器启动失败: {e}")
            return False
    
    def start_sla_collector(self):
        """启动SLA数据收集器"""
        try:
            from sla_collector_engine import SLACollectorEngine
            collector = SLACollectorEngine()
            
            def run_sla():
                while self.running:
                    try:
                        # SLA收集器会自动调度
                        collector.start_collection()
                        logger.info("✅ SLA数据收集器已启动")
                        # 等待，让调度器运行
                        time.sleep(3600)
                    except Exception as e:
                        logger.error(f"SLA收集错误: {e}")
                        time.sleep(600)
            
            self.collectors['sla'] = collector
            thread = threading.Thread(target=run_sla, daemon=True)
            self.threads['sla'] = thread
            thread.start()
            logger.info("✅ SLA数据收集器已启动")
            return True
        except Exception as e:
            logger.error(f"❌ SLA收集器启动失败: {e}")
            return False
    
    def start_all(self):
        """启动所有数据收集器"""
        self.running = True
        results = {}
        
        logger.info("=" * 60)
        logger.info("🚀 启动所有数据收集器...")
        logger.info("=" * 60)
        
        # 启动各个收集器
        results['analytics'] = self.start_analytics_engine()
        results['multi_exchange'] = self.start_multi_exchange_collector()
        # results['alternative'] = self.start_alternative_sources()  # 暂时禁用：数据库架构不匹配
        results['blockchain'] = self.start_blockchain_scheduler()
        # results['sla'] = self.start_sla_collector()  # 暂时禁用：需要app context
        
        # 统计结果
        success = sum(1 for v in results.values() if v)
        total = len(results)
        
        logger.info("=" * 60)
        logger.info(f"📊 启动结果: {success}/{total} 个收集器成功启动")
        logger.info("=" * 60)
        
        for name, status in results.items():
            status_icon = "✅" if status else "❌"
            logger.info(f"{status_icon} {name}: {'运行中' if status else '失败'}")
        
        return results
    
    def stop_all(self):
        """停止所有数据收集器"""
        logger.info("停止所有数据收集器...")
        self.running = False
        
        # 等待所有线程结束
        for name, thread in self.threads.items():
            if thread.is_alive():
                logger.info(f"等待 {name} 线程结束...")
                thread.join(timeout=5)
        
        logger.info("所有数据收集器已停止")
    
    def get_status(self):
        """获取所有收集器状态"""
        status = {}
        for name, collector in self.collectors.items():
            thread = self.threads.get(name)
            status[name] = {
                'running': thread.is_alive() if thread else True,
                'collector': type(collector).__name__
            }
        return status

# 全局实例
collectors_manager = DataCollectorsManager()

def start_all_collectors():
    """启动所有数据收集器的便捷函数"""
    return collectors_manager.start_all()

def stop_all_collectors():
    """停止所有数据收集器的便捷函数"""
    collectors_manager.stop_all()

def get_collectors_status():
    """获取收集器状态的便捷函数"""
    return collectors_manager.get_status()

if __name__ == '__main__':
    # 作为独立脚本运行
    try:
        start_all_collectors()
        logger.info("数据收集器管理器运行中... 按Ctrl+C停止")
        while True:
            time.sleep(60)
            status = get_collectors_status()
            logger.info(f"状态检查: {status}")
    except KeyboardInterrupt:
        logger.info("收到停止信号")
        stop_all_collectors()
