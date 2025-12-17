#!/usr/bin/env python3
"""
HashInsight CDC Platform - Intelligence Forecast Consumer
Intelligence预测消费者（占位实现）

功能：
- 订阅 events.miner 主题
- 监听 miner.* 事件触发预测刷新
- 更新 forecast_daily 表（BTC价格、难度预测）
- 占位实现但结构完整

Author: HashInsight Team
Version: 1.0.0
"""
import os
import sys
import logging
from typing import Dict
from datetime import datetime, timedelta

# 添加项目根目录到路径
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, PROJECT_ROOT)

# 添加CDC平台核心模块到路径（与common.py一致）
CDC_WORKERS_PATH = os.path.dirname(__file__)
sys.path.insert(0, CDC_WORKERS_PATH)

from common import KafkaConsumerBase, format_error_message

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/intel_consumer.log')
    ]
)
logger = logging.getLogger(__name__)


class IntelligenceConsumer(KafkaConsumerBase):
    """
    Intelligence预测消费者
    
    监听miner事件，触发预测模型刷新
    
    当用户矿机配置发生变化时：
    - 重新预测该用户的收益趋势
    - 更新 forecast_daily 表
    - 触发智能推荐引擎
    """
    
    def __init__(self):
        """初始化Intelligence消费者"""
        super().__init__(
            consumer_name='intel-consumer',
            topic=os.getenv('KAFKA_MINER_TOPIC', 'events.miner'),
            group_id=os.getenv('KAFKA_INTEL_GROUP', 'intelligence-forecast-group')
        )
        
        # 需要响应的事件类型
        self.event_types = ['miner.added', 'miner.updated', 'miner.removed']
        
        # 预测配置
        self.forecast_horizon = int(os.getenv('FORECAST_HORIZON_DAYS', 7))  # 默认预测7天
        
        logger.info(
            f"✅ IntelligenceConsumer initialized, "
            f"listening to: {self.event_types}, forecast_horizon={self.forecast_horizon} days"
        )
    
    def process_event(self, event_id: str, event_kind: str, user_id: str, payload: Dict):
        """
        处理miner事件，触发预测刷新
        
        参数:
            event_id: 事件ID
            event_kind: 事件类型（miner.added/updated/removed）
            user_id: 用户ID
            payload: 事件负载
        
        流程：
            1. 检查事件类型
            2. 获取用户矿机配置
            3. 调用预测引擎
            4. 写入 forecast_daily 表
        """
        # 1. 过滤事件类型
        if event_kind not in self.event_types:
            logger.debug(f"⏭️ Skipping event type: {event_kind}")
            return
        
        logger.info(f"🧠 Processing intelligence forecast: user_id={user_id}, event={event_kind}")
        
        try:
            # 2. 刷新预测数据
            forecast_result = self._refresh_forecast(user_id, event_kind, payload)
            
            logger.info(
                f"✅ Forecast refreshed: user_id={user_id}, "
                f"predicted_price=${forecast_result.get('predicted_btc_price', 0):.2f}, "
                f"horizon={self.forecast_horizon} days"
            )
        
        except Exception as e:
            error_msg = format_error_message(e)
            logger.error(f"❌ Intelligence forecast failed for user {user_id}: {error_msg}")
            raise
    
    def _refresh_forecast(self, user_id: str, event_kind: str, payload: Dict) -> Dict:
        """
        刷新用户收益预测
        
        参数:
            user_id: 用户ID
            event_kind: 事件类型
            payload: 事件负载
        
        返回:
            预测结果字典
        
        占位实现：
            - 生成模拟预测数据
            - 写入 forecast_daily 表
            - 实际生产环境应调用预测模型
        """
        try:
            with self.app.app_context():
                # 尝试导入预测模型
                try:
                    from intelligence.forecast import forecast_btc_price, forecast_network_difficulty
                    
                    # 调用预测函数
                    price_forecast = forecast_btc_price(days=self.forecast_horizon)
                    difficulty_forecast = forecast_network_difficulty(days=self.forecast_horizon)
                    
                    # 保存预测结果
                    result = self._save_forecast(
                        user_id, 
                        price_forecast, 
                        difficulty_forecast
                    )
                    
                    return result
                
                except ImportError:
                    # 如果无法导入预测模块，使用占位实现
                    logger.warning("⚠️ Cannot import forecast module, using placeholder")
                    return self._placeholder_forecast(user_id, event_kind)
        
        except Exception as e:
            logger.error(f"❌ Forecast refresh error: {e}")
            raise
    
    def _placeholder_forecast(self, user_id: str, event_kind: str) -> Dict:
        """
        占位预测函数
        
        参数:
            user_id: 用户ID
            event_kind: 事件类型
        
        返回:
            模拟的预测结果
        
        注意：
            - 这是占位实现，实际应调用ML模型
            - 生成简单的线性预测数据
        """
        logger.info(f"📋 Placeholder forecast for user_id={user_id}, event={event_kind}")
        
        # 生成占位预测数据
        base_price = 45000.0  # 基础BTC价格
        base_difficulty = 50e12  # 基础网络难度
        
        # 写入forecast_daily表（占位）
        try:
            from models import ForecastDaily
            from app import db
            
            forecast_date = datetime.utcnow().date() + timedelta(days=1)
            
            # 检查是否已存在预测
            existing = ForecastDaily.query.filter_by(
                user_id=user_id,
                forecast_date=forecast_date,
                forecast_horizon=self.forecast_horizon
            ).first()
            
            if existing:
                # 更新现有预测
                existing.predicted_btc_price = base_price
                existing.predicted_difficulty = base_difficulty
                existing.model_name = 'Placeholder'
                existing.updated_at = datetime.utcnow()
                logger.info(f"📝 Updated existing forecast for user {user_id}")
            else:
                # 创建新预测
                forecast = ForecastDaily(
                    forecast_date=forecast_date,
                    predicted_btc_price=base_price,
                    predicted_difficulty=base_difficulty,
                    user_id=user_id,
                    forecast_horizon=self.forecast_horizon,
                    model_name='Placeholder',
                    rmse=100.0,  # 占位误差
                    mae=50.0,
                    confidence_score=75.0
                )
                db.session.add(forecast)
                logger.info(f"📝 Created new forecast for user {user_id}")
            
            db.session.commit()
            
            return {
                'user_id': user_id,
                'forecast_date': forecast_date.isoformat(),
                'predicted_btc_price': base_price,
                'predicted_difficulty': base_difficulty,
                'forecast_horizon': self.forecast_horizon,
                'status': 'success'
            }
        
        except ImportError:
            # 如果无法导入模型，仅记录日志
            logger.warning("⚠️ Cannot import ForecastDaily model, skipping DB write")
            return {
                'user_id': user_id,
                'status': 'skipped',
                'reason': 'model_not_available'
            }
        
        except Exception as e:
            logger.error(f"❌ Error saving forecast: {e}")
            db.session.rollback()
            raise
    
    def _save_forecast(self, user_id: str, price_forecast: Dict, 
                       difficulty_forecast: Dict) -> Dict:
        """
        保存预测结果到数据库
        
        参数:
            user_id: 用户ID
            price_forecast: BTC价格预测结果
            difficulty_forecast: 网络难度预测结果
        
        返回:
            保存结果字典
        """
        try:
            from models import ForecastDaily
            from app import db
            
            # 获取预测数据
            predictions = price_forecast.get('predictions', [])
            if not predictions:
                raise ValueError("No predictions available")
            
            # 保存每天的预测
            for idx, pred in enumerate(predictions[:self.forecast_horizon]):
                forecast_date = pred['date']
                
                # 检查是否已存在
                existing = ForecastDaily.query.filter_by(
                    user_id=user_id,
                    forecast_date=forecast_date,
                    forecast_horizon=self.forecast_horizon
                ).first()
                
                difficulty_pred = difficulty_forecast.get('predictions', [{}])[idx]
                
                if existing:
                    # 更新
                    existing.predicted_btc_price = pred['price']
                    existing.price_lower_bound = pred.get('lower_bound')
                    existing.price_upper_bound = pred.get('upper_bound')
                    existing.predicted_difficulty = difficulty_pred.get('difficulty', 0)
                    existing.model_name = price_forecast.get('model_params', {}).get('order', 'ARIMA')
                    existing.rmse = price_forecast.get('rmse')
                    existing.mae = price_forecast.get('mae')
                    existing.updated_at = datetime.utcnow()
                else:
                    # 创建新记录
                    forecast = ForecastDaily(
                        forecast_date=forecast_date,
                        predicted_btc_price=pred['price'],
                        predicted_difficulty=difficulty_pred.get('difficulty', 0),
                        user_id=user_id,
                        forecast_horizon=self.forecast_horizon,
                        price_lower_bound=pred.get('lower_bound'),
                        price_upper_bound=pred.get('upper_bound'),
                        model_name=str(price_forecast.get('model_params', {}).get('order', 'ARIMA')),
                        rmse=price_forecast.get('rmse'),
                        mae=price_forecast.get('mae')
                    )
                    db.session.add(forecast)
            
            db.session.commit()
            
            return {
                'user_id': user_id,
                'predicted_btc_price': predictions[0]['price'],
                'forecast_horizon': self.forecast_horizon,
                'status': 'success'
            }
        
        except Exception as e:
            db.session.rollback()
            raise


def main():
    """主函数 - 运行Intelligence消费者"""
    logger.info("=" * 60)
    logger.info("🧠 HashInsight Intelligence Consumer Starting...")
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
    consumer = IntelligenceConsumer()
    
    try:
        consumer.run()
    except KeyboardInterrupt:
        logger.info("⏹️ Intelligence Consumer stopped by user")
    except Exception as e:
        logger.error(f"❌ Intelligence Consumer crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
