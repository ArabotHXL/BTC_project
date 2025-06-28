#!/usr/bin/env python3
"""
分析系统测试脚本
验证数据收集、分析和报告生成功能
"""

import os
import time
import logging
from analytics_engine import AnalyticsEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_collection():
    """测试数据收集功能"""
    logger.info("测试数据收集功能...")
    
    engine = AnalyticsEngine()
    
    # 测试单次数据收集
    market_data = engine.data_collector.collect_all_data()
    if market_data:
        logger.info(f"✓ 数据收集成功: BTC=${market_data.btc_price:,.2f}, 算力={market_data.network_hashrate:.2f}EH/s")
        
        # 保存数据
        engine.data_collector.save_market_data(market_data)
        logger.info("✓ 数据保存成功")
        
        return True
    else:
        logger.error("✗ 数据收集失败")
        return False

def test_technical_analysis():
    """测试技术分析功能"""
    logger.info("测试技术分析功能...")
    
    engine = AnalyticsEngine()
    
    # 计算技术指标
    indicators = engine.technical_analyzer.calculate_technical_indicators()
    if indicators:
        logger.info("✓ 技术指标计算成功")
        logger.info(f"  RSI: {indicators.get('rsi_14', 'N/A')}")
        logger.info(f"  SMA20: {indicators.get('sma_20', 'N/A')}")
        logger.info(f"  MACD: {indicators.get('macd', 'N/A')}")
        
        # 保存技术指标
        engine.technical_analyzer.save_technical_indicators(indicators)
        logger.info("✓ 技术指标保存成功")
        
        return True
    else:
        logger.warning("⚠ 技术指标计算需要更多历史数据")
        return False

def test_report_generation():
    """测试报告生成功能"""
    logger.info("测试报告生成功能...")
    
    engine = AnalyticsEngine()
    
    # 生成分析报告
    report = engine.report_generator.generate_daily_report()
    if report:
        logger.info("✓ 分析报告生成成功")
        logger.info(f"  标题: {report.get('title', 'N/A')}")
        logger.info(f"  摘要: {report.get('summary', 'N/A')[:100]}...")
        logger.info(f"  置信度: {report.get('confidence_score', 0)*100:.1f}%")
        
        # 保存报告
        engine.report_generator.save_report(report)
        logger.info("✓ 分析报告保存成功")
        
        return True
    else:
        logger.warning("⚠ 报告生成需要更多数据")
        return False

def test_database_tables():
    """测试数据库表结构"""
    logger.info("测试数据库表结构...")
    
    engine = AnalyticsEngine()
    conn = engine.db_manager.connect()
    
    if not conn:
        logger.error("✗ 数据库连接失败")
        return False
    
    try:
        cursor = conn.cursor()
        
        # 检查所有表是否存在
        tables = ['market_analytics', 'technical_indicators', 'mining_metrics', 'analysis_reports']
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            logger.info(f"✓ 表 {table}: {count} 条记录")
        
        cursor.close()
        conn.close()
        
        logger.info("✓ 数据库表检查完成")
        return True
        
    except Exception as e:
        logger.error(f"✗ 数据库表检查失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("开始Bitcoin分析系统测试...")
    logger.info("="*50)
    
    results = {
        '数据库表结构': test_database_tables(),
        '数据收集': test_data_collection(),
        '技术分析': test_technical_analysis(),
        '报告生成': test_report_generation()
    }
    
    logger.info("="*50)
    logger.info("测试结果摘要:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n测试完成: {passed}/{total} 通过")
    
    if passed == total:
        logger.info("🎉 所有测试通过！系统可以正常运行。")
        logger.info("\n启动命令:")
        logger.info("  python start_analytics.py")
        logger.info("\n仪表盘地址:")
        logger.info("  http://localhost:5001")
    else:
        logger.warning("⚠️  部分测试失败，请检查配置和网络连接。")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)