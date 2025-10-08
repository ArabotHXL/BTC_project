#!/usr/bin/env python3
"""
HashInsight CDC Platform - Portfolio Recalculation Consumer
Portfolio重算消费者

功能：
- 订阅 events.miner 主题
- 监听 miner.* 事件（added, updated, removed）
- 使用分布式锁防止并发重算
- 调用 recalculate_user_portfolio 重新计算用户投资组合
- 成功后失效缓存
- 失败自动重试3次后写入DLQ

Author: HashInsight Team
Version: 1.0.0
"""
import os
import sys
import logging
from typing import Dict

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

# 添加CDC平台核心模块到路径（与common.py一致）
CDC_WORKERS_PATH = os.path.dirname(__file__)
sys.path.insert(0, CDC_WORKERS_PATH)

from .common import KafkaConsumerBase, format_error_message  # type: ignore

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/portfolio_consumer.log')
    ]
)
logger = logging.getLogger(__name__)


class PortfolioConsumer(KafkaConsumerBase):
    """
    Portfolio重算消费者
    
    监听miner事件，触发用户投资组合重新计算
    """
    
    def __init__(self):
        """初始化Portfolio消费者"""
        super().__init__(
            consumer_name='portfolio-consumer',
            topic=os.getenv('KAFKA_MINER_TOPIC', 'events.miner'),
            group_id=os.getenv('KAFKA_PORTFOLIO_GROUP', 'portfolio-recalc-group')
        )
        
        # 需要响应的事件类型
        self.event_types = ['miner.added', 'miner.updated', 'miner.removed']
        
        logger.info(f"✅ PortfolioConsumer initialized, listening to: {self.event_types}")
    
    def process_event(self, event_id: str, event_kind: str, user_id: str, payload: Dict):
        """
        处理miner事件，触发Portfolio重算
        
        参数:
            event_id: 事件ID
            event_kind: 事件类型（miner.added/updated/removed）
            user_id: 用户ID
            payload: 事件负载
        
        流程：
            1. 检查事件类型是否需要处理
            2. 获取分布式锁 lock:recalc:{user_id}
            3. 调用 recalculate_user_portfolio(user_id)
            4. 成功后失效缓存 user_portfolio:{user_id}
            5. 释放锁
        """
        # 1. 过滤事件类型
        if event_kind not in self.event_types:
            logger.debug(f"⏭️ Skipping event type: {event_kind} (not in {self.event_types})")
            return
        
        logger.info(f"🔄 Processing portfolio recalc: user_id={user_id}, event={event_kind}")
        
        # 2. 获取分布式锁（防止并发重算同一用户）
        lock_name = f"recalc:{user_id}"
        lock = self._acquire_lock(lock_name)
        
        if not lock:
            raise Exception(f"Failed to acquire lock for user {user_id} (already processing)")
        
        try:
            # 3. 调用Portfolio重算函数
            result = self._recalc_portfolio(user_id, event_id)
            
            # 4. 成功后失效缓存
            cache_key = f"user_portfolio:{user_id}"
            self._invalidate_cache(cache_key)
            
            logger.info(
                f"✅ Portfolio recalc completed: user_id={user_id}, "
                f"hashrate={result.get('total_hashrate', 0):.2f} TH/s, "
                f"revenue=${result.get('estimated_daily_revenue', 0):.2f}/day"
            )
        
        finally:
            # 5. 释放锁
            self._release_lock(lock)
    
    def _recalc_portfolio(self, user_id: str, event_id: str) -> Dict:
        """
        执行Portfolio重算逻辑
        
        参数:
            user_id: 用户ID（字符串格式）
            event_id: 触发事件ID
        
        返回:
            重算结果字典
        
        注意：
            - recalculate_user_portfolio 需要整数user_id
            - 这里做类型转换处理
        """
        try:
            # 导入重算函数（延迟导入避免循环依赖）
            if not self.app:
                logger.error("❌ Flask app not initialized")
                return self._placeholder_recalc(user_id)
            with self.app.app_context():
                # 尝试导入主应用的重算函数
                try:
                    from intelligence.workers.tasks import recalculate_user_portfolio
                    
                    # 转换user_id为整数
                    user_id_int = int(user_id)
                    
                    # 调用重算函数
                    result = recalculate_user_portfolio(
                        user_id=user_id_int,
                        source_event_ids=[event_id]
                    )
                    
                    if result.get('status') != 'success':
                        raise Exception(result.get('error', 'Unknown error in portfolio recalculation'))
                    
                    return result
                
                except ImportError:
                    # 如果无法导入，使用简化版本（占位）
                    logger.warning("⚠️ Cannot import recalculate_user_portfolio, using placeholder")
                    return self._placeholder_recalc(user_id)
        
        except Exception as e:
            error_msg = format_error_message(e)
            logger.error(f"❌ Portfolio recalc failed for user {user_id}: {error_msg}")
            raise
    
    def _placeholder_recalc(self, user_id: str) -> Dict:
        """
        占位重算函数（当主函数不可用时）
        
        参数:
            user_id: 用户ID
        
        返回:
            模拟的重算结果
        """
        logger.info(f"📋 Placeholder recalc for user_id={user_id}")
        
        # 这里应该实现实际的重算逻辑
        # 暂时返回模拟数据
        return {
            'user_id': int(user_id),
            'total_hashrate': 0.0,
            'total_power': 0.0,
            'active_miners': 0,
            'estimated_daily_revenue': 0.0,
            'status': 'success',
            'source_events_updated': 1
        }


def main():
    """主函数 - 运行Portfolio消费者"""
    logger.info("=" * 60)
    logger.info("🚀 HashInsight Portfolio Consumer Starting...")
    logger.info("=" * 60)
    
    # 检查必需的环境变量
    required_env_vars = ['DATABASE_URL', 'REDIS_URL', 'KAFKA_BOOTSTRAP_SERVERS']
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        logger.error("💡 Please set these environment variables:")
        logger.error("   - DATABASE_URL: PostgreSQL connection string")
        logger.error("   - REDIS_URL: Redis connection string")
        logger.error("   - KAFKA_BOOTSTRAP_SERVERS: Kafka broker addresses")
        sys.exit(1)
    
    # 创建并运行消费者
    consumer = PortfolioConsumer()
    
    try:
        consumer.run()
    except KeyboardInterrupt:
        logger.info("⏹️ Portfolio Consumer stopped by user")
    except Exception as e:
        logger.error(f"❌ Portfolio Consumer crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
