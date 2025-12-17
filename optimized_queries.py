"""
优化的数据库查询函数
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, desc
from cache_manager import cache, cached, CacheKeys
from performance_monitor import measure_performance

logger = logging.getLogger(__name__)

class OptimizedQueries:
    """优化的数据库查询类"""
    
    @staticmethod
    @cached(ttl=60, key_prefix='market_data')
    @measure_performance('database')
    def get_latest_market_data(db_session):
        """获取最新市场数据（缓存60秒）"""
        try:
            from models import NetworkSnapshot
            
            # 使用索引优化的查询
            latest = db_session.query(NetworkSnapshot)\
                .order_by(NetworkSnapshot.recorded_at.desc())\
                .limit(1)\
                .first()
            
            if latest:
                return {
                    'btc_price': latest.btc_price,
                    'network_hashrate': latest.network_hashrate,
                    'network_difficulty': latest.network_difficulty,
                    'timestamp': latest.recorded_at.isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    @staticmethod
    @cached(ttl=300, key_prefix='price_history')
    @measure_performance('database')
    def get_price_history(db_session, hours: int = 24):
        """获取价格历史（缓存5分钟）"""
        try:
            from models import NetworkSnapshot
            
            time_threshold = datetime.utcnow() - timedelta(hours=hours)
            
            # 优化：只选择需要的字段
            snapshots = db_session.query(
                NetworkSnapshot.btc_price,
                NetworkSnapshot.network_hashrate,
                NetworkSnapshot.network_difficulty,
                NetworkSnapshot.recorded_at
            ).filter(
                NetworkSnapshot.recorded_at >= time_threshold
            ).order_by(
                NetworkSnapshot.recorded_at.desc()
            ).limit(hours * 2).all()  # 限制结果数量
            
            return [{
                'btc_price': s.btc_price,
                'network_hashrate': s.network_hashrate,
                'network_difficulty': s.network_difficulty,
                'timestamp': s.recorded_at.isoformat()
            } for s in snapshots]
            
        except Exception as e:
            logger.error(f"Error fetching price history: {e}")
            return []
    
    @staticmethod
    @cached(ttl=600, key_prefix='user_stats')
    @measure_performance('database')
    def get_user_statistics(db_session, user_id: int):
        """获取用户统计信息（缓存10分钟）"""
        try:
            from models import UserAccess, Customer
            
            # 使用JOIN优化查询
            result = db_session.query(
                func.count(Customer.id).label('customer_count'),
                func.sum(Customer.investment_amount).label('total_investment')
            ).filter(
                Customer.user_id == user_id
            ).first()
            
            return {
                'customer_count': result.customer_count or 0,
                'total_investment': float(result.total_investment or 0)
            }
            
        except Exception as e:
            logger.error(f"Error fetching user stats: {e}")
            return {'customer_count': 0, 'total_investment': 0}
    
    @staticmethod
    @measure_performance('database')
    def batch_update_user_plans(db_session, updates: list):
        """批量更新用户计划"""
        try:
            from models import UserAccess
            
            # 使用bulk_update_mappings进行批量更新
            db_session.bulk_update_mappings(UserAccess, updates)
            db_session.commit()
            
            # 清理相关缓存
            for update in updates:
                cache.delete(CacheKeys.user_plan(update.get('id')))
            
            return True
            
        except Exception as e:
            logger.error(f"Error in batch update: {e}")
            db_session.rollback()
            return False
    
    @staticmethod
    @cached(ttl=3600, key_prefix='technical_indicators')
    @measure_performance('database')
    def get_technical_indicators(db_session):
        """获取技术指标（缓存1小时）"""
        try:
            from models import TechnicalIndicator
            
            latest = db_session.query(TechnicalIndicator)\
                .order_by(TechnicalIndicator.recorded_at.desc())\
                .first()
            
            if latest:
                return {
                    'rsi': latest.rsi,
                    'macd': latest.macd,
                    'sma_20': latest.sma_20,
                    'sma_50': latest.sma_50,
                    'ema_12': latest.ema_12,
                    'ema_26': latest.ema_26,
                    'bollinger_upper': latest.bollinger_upper,
                    'bollinger_lower': latest.bollinger_lower,
                    'volatility': latest.volatility,
                    'recorded_at': latest.recorded_at.isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching technical indicators: {e}")
            return None
    
    @staticmethod
    def cleanup_old_data(db_session, days_to_keep: int = 30):
        """清理旧数据"""
        try:
            from models import NetworkSnapshot, TechnicalIndicator
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            # 删除旧的网络快照
            deleted_snapshots = db_session.query(NetworkSnapshot)\
                .filter(NetworkSnapshot.recorded_at < cutoff_date)\
                .delete()
            
            # 删除旧的技术指标
            deleted_indicators = db_session.query(TechnicalIndicator)\
                .filter(TechnicalIndicator.recorded_at < cutoff_date)\
                .delete()
            
            db_session.commit()
            
            logger.info(f"Cleaned up {deleted_snapshots} snapshots and {deleted_indicators} indicators")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning old data: {e}")
            db_session.rollback()
            return False