"""
共享数据库操作
所有模块都可以调用的数据库接口
"""
from models import NetworkSnapshot, CalculationLog, db
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_network_data():
    """
    获取最新的网络数据
    所有模块统一从这里获取网络状态
    """
    try:
        network = NetworkSnapshot.query.order_by(
            NetworkSnapshot.timestamp.desc()
        ).first()
        
        if network:
            return {
                'btc_price': network.btc_price,
                'network_hashrate': network.network_hashrate,
                'network_difficulty': network.network_difficulty,
                'block_reward': network.block_reward,
                'timestamp': network.timestamp
            }
        return None
        
    except Exception as e:
        logger.error(f"获取网络数据失败: {e}")
        return None

def save_calculation_log(user_id, module_name, params, results):
    """
    保存计算日志
    所有模块的计算都记录到统一的日志表
    
    Args:
        user_id: 用户ID
        module_name: 模块名称 (calculator, batch, crm等)
        params: 计算参数
        results: 计算结果
    """
    try:
        log = CalculationLog(
            user_id=user_id,
            module=module_name,
            parameters=params,
            results=results,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        return log.id
        
    except Exception as e:
        logger.error(f"保存计算日志失败: {e}")
        db.session.rollback()
        return None

def get_user_calculations(user_id, module_name=None, limit=10):
    """
    获取用户的计算历史
    
    Args:
        user_id: 用户ID
        module_name: 可选，筛选特定模块
        limit: 返回记录数量
    """
    try:
        query = CalculationLog.query.filter_by(user_id=user_id)
        
        if module_name:
            query = query.filter_by(module=module_name)
            
        logs = query.order_by(
            CalculationLog.timestamp.desc()
        ).limit(limit).all()
        
        return [log.to_dict() for log in logs]
        
    except Exception as e:
        logger.error(f"获取计算历史失败: {e}")
        return []

def get_cross_module_stats(user_id):
    """
    获取跨模块统计数据
    用于展示用户在所有模块的活动情况
    """
    try:
        stats = {}
        
        # 各模块使用次数
        modules = ['calculator', 'batch', 'crm', 'analytics']
        for module in modules:
            count = CalculationLog.query.filter_by(
                user_id=user_id,
                module=module
            ).count()
            stats[f'{module}_usage'] = count
        
        # 最近活动时间
        latest = CalculationLog.query.filter_by(
            user_id=user_id
        ).order_by(
            CalculationLog.timestamp.desc()
        ).first()
        
        if latest:
            stats['last_activity'] = latest.timestamp
            
        return stats
        
    except Exception as e:
        logger.error(f"获取跨模块统计失败: {e}")
        return {}